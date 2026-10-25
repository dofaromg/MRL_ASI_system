# origin_signature: MrLiouWord
"""Persistent, unit-aware vector graph for celestial trajectories."""

from __future__ import annotations

import hashlib
import json
import math
import sqlite3
import threading
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, List, Optional, Sequence, Tuple


def _stable_json(value: Any) -> str:
    return json.dumps(
        value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False
    )


def _finite_vector(values: Sequence[float], name: str = "vector") -> Tuple[float, ...]:
    try:
        vector = tuple(float(value) for value in values)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{name} must contain finite numbers") from exc
    if not vector or any(not math.isfinite(value) for value in vector):
        raise ValueError(f"{name} must contain finite numbers")
    return vector


def _timestamp(value: str) -> Tuple[str, float]:
    if not isinstance(value, str) or not value.strip():
        raise ValueError("observed_at must be a non-empty ISO-8601 timestamp")
    try:
        parsed = datetime.fromisoformat(value.strip().replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError("observed_at must be a valid ISO-8601 timestamp") from exc
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    parsed = parsed.astimezone(timezone.utc)
    return parsed.isoformat(timespec="microseconds"), parsed.timestamp()


def _node_id(kind: str, *parts: str) -> str:
    key = _stable_json([kind, *parts]).encode("utf-8")
    return f"{kind}:{hashlib.sha256(key).hexdigest()}"


class CelestialVectorGraph:
    """SQLite-backed graph for measured states and derived motion signatures.

    Position vectors use three coordinates and an explicit distance unit.
    Motion signatures are derived only from supplied observations; this class
    does not synthesize celestial data or assume an orbital force model.
    """

    def __init__(self, database_path: str | Path) -> None:
        self.database_path = str(database_path)
        if self.database_path != ":memory:":
            Path(self.database_path).parent.mkdir(parents=True, exist_ok=True)
        self._lock = threading.RLock()
        self._connection = sqlite3.connect(self.database_path, check_same_thread=False)
        self._connection.row_factory = sqlite3.Row
        self._connection.execute("PRAGMA foreign_keys = ON")
        self._initialize()

    def _initialize(self) -> None:
        self._connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS nodes (
                node_id TEXT PRIMARY KEY,
                kind TEXT NOT NULL,
                label TEXT NOT NULL,
                payload_json TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS vectors (
                node_id TEXT PRIMARY KEY REFERENCES nodes(node_id) ON DELETE CASCADE,
                values_json TEXT NOT NULL,
                dimensions_json TEXT NOT NULL,
                units_json TEXT NOT NULL,
                reference_frame TEXT NOT NULL,
                source_return_id TEXT
            );
            CREATE TABLE IF NOT EXISTS edges (
                source_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
                target_id TEXT NOT NULL REFERENCES nodes(node_id) ON DELETE CASCADE,
                relation TEXT NOT NULL,
                PRIMARY KEY (source_id, target_id, relation)
            );
            CREATE INDEX IF NOT EXISTS idx_nodes_kind ON nodes(kind);
            CREATE INDEX IF NOT EXISTS idx_edges_target_relation
                ON edges(target_id, relation);
            CREATE INDEX IF NOT EXISTS idx_vectors_search
                ON vectors(reference_frame, node_id);
            """
        )
        self._connection.commit()

    @contextmanager
    def _transaction(self) -> Iterator[sqlite3.Connection]:
        with self._lock:
            if self._connection is None:
                raise RuntimeError("Vector graph is closed")
            self._connection.execute("BEGIN IMMEDIATE")
            try:
                yield self._connection
            except Exception:
                self._connection.rollback()
                raise
            else:
                self._connection.commit()

    def close(self) -> None:
        with self._lock:
            if self._connection is not None:
                self._connection.close()
                self._connection = None

    def __enter__(self) -> "CelestialVectorGraph":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.close()

    def add_body(
        self,
        body_id: str,
        *,
        name: str,
        body_type: str = "celestial_body",
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        if not body_id.strip() or not name.strip() or not body_type.strip():
            raise ValueError("body_id, name, and body_type must not be empty")
        node_id = f"body:{body_id}"
        payload = {"body_id": body_id, "body_type": body_type, "metadata": metadata or {}}
        payload_json = _stable_json(payload)
        with self._transaction() as connection:
            existing = connection.execute(
                "SELECT kind FROM nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
            if existing and existing["kind"] != "celestial_body":
                raise ValueError(f"Node ID already belongs to another kind: {body_id}")
            connection.execute(
                """INSERT INTO nodes(node_id, kind, label, payload_json)
                   VALUES (?, 'celestial_body', ?, ?)
                   ON CONFLICT(node_id) DO UPDATE SET label=excluded.label,
                   payload_json=excluded.payload_json""",
                (node_id, name, payload_json),
            )
        return node_id

    def add_observation(
        self,
        body_id: str,
        *,
        observed_at: str,
        position: Sequence[float],
        position_unit: str,
        reference_frame: str,
        source_return_id: str,
        velocity: Optional[Sequence[float]] = None,
        velocity_unit: Optional[str] = None,
    ) -> str:
        position_vector = _finite_vector(position, "position")
        if len(position_vector) != 3:
            raise ValueError("position must have exactly three coordinates")
        if not position_unit.strip() or not reference_frame.strip() or not source_return_id.strip():
            raise ValueError("position_unit, reference_frame, and source_return_id are required")
        canonical_time, epoch = _timestamp(observed_at)
        velocity_vector = None if velocity is None else _finite_vector(velocity, "velocity")
        if velocity_vector is not None:
            if len(velocity_vector) != 3:
                raise ValueError("velocity must have exactly three coordinates")
            if not velocity_unit or not velocity_unit.strip():
                raise ValueError("velocity_unit is required when velocity is provided")
        elif velocity_unit:
            raise ValueError("velocity_unit requires a velocity vector")

        state_values = position_vector + (() if velocity_vector is None else velocity_vector)
        state_dimensions = ("x", "y", "z") + (
            () if velocity_vector is None else ("vx", "vy", "vz")
        )
        state_units = (position_unit,) * 3 + (
            () if velocity_vector is None else (velocity_unit,) * 3
        )
        body_node = f"body:{body_id}"
        observation_id = _node_id("observation", body_id, canonical_time)
        payload = {
            "body_id": body_id,
            "observed_at": canonical_time,
            "epoch_seconds": epoch,
            "position": position_vector,
            "position_unit": position_unit,
            "velocity": velocity_vector,
            "velocity_unit": velocity_unit,
        }
        with self._transaction() as connection:
            body = connection.execute(
                "SELECT kind FROM nodes WHERE node_id = ?", (body_node,)
            ).fetchone()
            if body is None or body["kind"] != "celestial_body":
                raise KeyError(f"Unknown celestial body: {body_id}")
            connection.execute(
                """INSERT INTO nodes(node_id, kind, label, payload_json)
                   VALUES (?, 'observation', ?, ?)
                   ON CONFLICT(node_id) DO UPDATE SET label=excluded.label,
                   payload_json=excluded.payload_json""",
                (observation_id, canonical_time, _stable_json(payload)),
            )
            connection.execute(
                """INSERT INTO vectors(node_id, values_json, dimensions_json, units_json,
                   reference_frame, source_return_id) VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(node_id) DO UPDATE SET values_json=excluded.values_json,
                   dimensions_json=excluded.dimensions_json, units_json=excluded.units_json,
                   reference_frame=excluded.reference_frame,
                   source_return_id=excluded.source_return_id""",
                (
                    observation_id,
                    _stable_json(state_values),
                    _stable_json(state_dimensions),
                    _stable_json(state_units),
                    reference_frame,
                    source_return_id,
                ),
            )
            connection.execute(
                """INSERT OR IGNORE INTO edges(source_id, target_id, relation)
                   VALUES (?, ?, 'has_observation')""",
                (body_node, observation_id),
            )
        return observation_id

    def add_pattern(
        self,
        pattern_id: str,
        *,
        label: str,
        values: Sequence[float],
        dimensions: Sequence[str],
        units: Sequence[str],
        reference_frame: str,
        source_return_id: str,
        body_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        vector = _finite_vector(values)
        dimensions = tuple(dimensions)
        units = tuple(units)
        if len(vector) != len(dimensions) or len(vector) != len(units):
            raise ValueError("values, dimensions, and units must have equal lengths")
        if (
            not pattern_id.strip()
            or not label.strip()
            or not reference_frame.strip()
            or not source_return_id.strip()
            or any(not value.strip() for value in dimensions + units)
        ):
            raise ValueError("Pattern metadata, dimensions, and units must not be empty")
        node_id = f"pattern:{pattern_id}"
        payload = {"pattern_id": pattern_id, "metadata": metadata or {}}
        with self._transaction() as connection:
            if body_id is not None:
                body = connection.execute(
                    "SELECT kind FROM nodes WHERE node_id = ?", (f"body:{body_id}",)
                ).fetchone()
                if body is None or body["kind"] != "celestial_body":
                    raise KeyError(f"Unknown celestial body: {body_id}")
            connection.execute(
                """INSERT INTO nodes(node_id, kind, label, payload_json)
                   VALUES (?, 'pattern', ?, ?)
                   ON CONFLICT(node_id) DO UPDATE SET label=excluded.label,
                   payload_json=excluded.payload_json""",
                (node_id, label, _stable_json(payload)),
            )
            connection.execute(
                """INSERT INTO vectors(node_id, values_json, dimensions_json, units_json,
                   reference_frame, source_return_id) VALUES (?, ?, ?, ?, ?, ?)
                   ON CONFLICT(node_id) DO UPDATE SET values_json=excluded.values_json,
                   dimensions_json=excluded.dimensions_json, units_json=excluded.units_json,
                   reference_frame=excluded.reference_frame,
                   source_return_id=excluded.source_return_id""",
                (
                    node_id,
                    _stable_json(vector),
                    _stable_json(dimensions),
                    _stable_json(units),
                    reference_frame,
                    source_return_id,
                ),
            )
            if body_id is not None:
                connection.execute(
                    """INSERT OR IGNORE INTO edges(source_id, target_id, relation)
                       VALUES (?, ?, 'has_pattern')""",
                    (f"body:{body_id}", node_id),
                )
        return node_id

    def add_relation(self, source_node: str, target_node: str, relation: str) -> None:
        if not relation.strip():
            raise ValueError("relation must not be empty")
        with self._transaction() as connection:
            try:
                connection.execute(
                    "INSERT OR IGNORE INTO edges(source_id, target_id, relation) VALUES (?, ?, ?)",
                    (source_node, target_node, relation),
                )
            except sqlite3.IntegrityError as exc:
                raise KeyError("Both graph nodes must exist before adding an edge") from exc

    def derive_trajectory_patterns(self, body_id: str) -> List[str]:
        """Create idempotent interval-velocity and adjacent-acceleration vectors."""
        with self._transaction() as connection:
            body_node = f"body:{body_id}"
            body = connection.execute(
                "SELECT kind FROM nodes WHERE node_id = ?", (body_node,)
            ).fetchone()
            if body is None or body["kind"] != "celestial_body":
                raise KeyError(f"Unknown celestial body: {body_id}")
            rows = connection.execute(
                """SELECT n.node_id, n.payload_json, v.reference_frame, v.source_return_id
                   FROM edges e JOIN nodes n ON n.node_id=e.target_id
                   JOIN vectors v ON v.node_id=n.node_id
                   WHERE e.source_id=? AND e.relation='has_observation'
                   ORDER BY json_extract(n.payload_json, '$.epoch_seconds'), n.node_id""",
                (body_node,),
            ).fetchall()
            observations = [(row, json.loads(row["payload_json"])) for row in rows]
            if len(observations) < 2:
                return []

            connection.execute(
                """DELETE FROM nodes WHERE kind='pattern'
                   AND json_extract(payload_json, '$.metadata.generated_by')='trajectory-v1'
                   AND json_extract(payload_json, '$.metadata.body_id')=?""",
                (body_id,),
            )
            velocities = []
            created = []
            for (left_row, left), (right_row, right) in zip(observations, observations[1:]):
                if left_row["reference_frame"] != right_row["reference_frame"]:
                    raise ValueError("Trajectory observations must use the same reference frame")
                if left["position_unit"] != right["position_unit"]:
                    raise ValueError("Trajectory observations must use the same position unit")
                elapsed = right["epoch_seconds"] - left["epoch_seconds"]
                if elapsed <= 0:
                    raise ValueError("Trajectory observation times must be strictly increasing")
                delta = tuple(b - a for a, b in zip(left["position"], right["position"]))
                velocity = tuple(component / elapsed for component in delta)
                pattern_key = _node_id("trajectory-velocity", left_row["node_id"], right_row["node_id"])
                interval = [left["observed_at"], right["observed_at"]]
                metadata = {
                    "generated_by": "trajectory-v1",
                    "body_id": body_id,
                    "observation_ids": [left_row["node_id"], right_row["node_id"]],
                    "interval": interval,
                    "elapsed_seconds": elapsed,
                    "pattern_type": "mean_velocity",
                }
                node_id = f"pattern:{pattern_key}"
                payload = {"pattern_id": pattern_key, "metadata": metadata}
                connection.execute(
                    "INSERT INTO nodes(node_id, kind, label, payload_json) VALUES (?, 'pattern', ?, ?)",
                    (node_id, "Mean trajectory velocity", _stable_json(payload)),
                )
                connection.execute(
                    """INSERT INTO vectors(node_id, values_json, dimensions_json, units_json,
                       reference_frame, source_return_id) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        node_id,
                        _stable_json(velocity),
                        _stable_json(["vx", "vy", "vz"]),
                        _stable_json([f"{left['position_unit']}/s"] * 3),
                        left_row["reference_frame"],
                        right_row["source_return_id"],
                    ),
                )
                connection.execute(
                    "INSERT INTO edges(source_id, target_id, relation) VALUES (?, ?, 'has_pattern')",
                    (body_node, node_id),
                )
                connection.execute(
                    "INSERT INTO edges(source_id, target_id, relation) VALUES (?, ?, 'derived_from')",
                    (node_id, left_row["node_id"],),
                )
                connection.execute(
                    "INSERT INTO edges(source_id, target_id, relation) VALUES (?, ?, 'derived_from')",
                    (node_id, right_row["node_id"]),
                )
                created.append(node_id)
                velocities.append((velocity, elapsed, left_row, right_row))

            for index in range(1, len(velocities)):
                previous, previous_dt, previous_left, previous_right = velocities[index - 1]
                current, current_dt, current_left, current_right = velocities[index]
                elapsed = (previous_dt + current_dt) / 2.0
                acceleration = tuple(
                    (current_component - previous_component) / elapsed
                    for previous_component, current_component in zip(previous, current)
                )
                pattern_key = _node_id(
                    "trajectory-acceleration", previous_left["node_id"], current_right["node_id"]
                )
                metadata = {
                    "generated_by": "trajectory-v1",
                    "body_id": body_id,
                    "observation_ids": [
                        previous_left["node_id"],
                        previous_right["node_id"],
                        current_right["node_id"],
                    ],
                    "pattern_type": "mean_acceleration",
                }
                position_unit = json.loads(previous_left["payload_json"])["position_unit"]
                node_id = f"pattern:{pattern_key}"
                payload = {"pattern_id": pattern_key, "metadata": metadata}
                connection.execute(
                    "INSERT INTO nodes(node_id, kind, label, payload_json) VALUES (?, 'pattern', ?, ?)",
                    (node_id, "Mean trajectory acceleration", _stable_json(payload)),
                )
                connection.execute(
                    """INSERT INTO vectors(node_id, values_json, dimensions_json, units_json,
                       reference_frame, source_return_id) VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        node_id,
                        _stable_json(acceleration),
                        _stable_json(["ax", "ay", "az"]),
                        _stable_json([f"{position_unit}/s^2"] * 3),
                        previous_left["reference_frame"],
                        current_right["source_return_id"],
                    ),
                )
                connection.execute(
                    "INSERT INTO edges(source_id, target_id, relation) VALUES (?, ?, 'has_pattern')",
                    (body_node, node_id),
                )
                for observation_id in metadata["observation_ids"]:
                    connection.execute(
                        "INSERT OR IGNORE INTO edges(source_id, target_id, relation) "
                        "VALUES (?, ?, 'derived_from')",
                        (node_id, observation_id),
                    )
                created.append(node_id)
            return created

    def similar_patterns(
        self,
        values: Sequence[float],
        *,
        dimensions: Sequence[str],
        units: Sequence[str],
        reference_frame: str,
        metric: str = "cosine",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search compatible vectors only; return score (cosine) or distance."""
        query = _finite_vector(values)
        dimensions = tuple(dimensions)
        units = tuple(units)
        if len(query) != len(dimensions) or len(query) != len(units):
            raise ValueError("values, dimensions, and units must have equal lengths")
        if not reference_frame.strip() or any(not value.strip() for value in dimensions + units):
            raise ValueError("dimensions, units, and reference_frame must not be empty")
        if metric not in {"cosine", "euclidean"}:
            raise ValueError("metric must be 'cosine' or 'euclidean'")
        if limit < 1:
            raise ValueError("limit must be positive")

        with self._lock:
            if self._connection is None:
                raise RuntimeError("Vector graph is closed")
            rows = self._connection.execute(
                """SELECT n.node_id, n.label, n.payload_json, v.values_json,
                          v.dimensions_json, v.units_json, v.reference_frame,
                          v.source_return_id
                   FROM vectors v JOIN nodes n ON n.node_id=v.node_id
                   WHERE n.kind='pattern' AND v.reference_frame=?""",
                (reference_frame,),
            ).fetchall()
        matches = []
        for row in rows:
            if (
                tuple(json.loads(row["dimensions_json"])) != dimensions
                or tuple(json.loads(row["units_json"])) != units
            ):
                continue
            candidate = json.loads(row["values_json"])
            if metric == "cosine":
                query_norm = math.hypot(*query)
                candidate_norm = math.hypot(*candidate)
                if query_norm == 0 or candidate_norm == 0:
                    score = 1.0 if query_norm == candidate_norm else 0.0
                else:
                    score = sum(
                        (a / query_norm) * (b / candidate_norm)
                        for a, b in zip(query, candidate)
                    )
                ordering = -score
            else:
                score = math.dist(query, candidate)
                ordering = score
            matches.append(
                {
                    "node_id": row["node_id"],
                    "label": row["label"],
                    "values": candidate,
                    "source_return_id": row["source_return_id"],
                    "metadata": json.loads(row["payload_json"])["metadata"],
                    "score": score,
                    "_ordering": ordering,
                }
            )
        matches.sort(key=lambda item: (item["_ordering"], item["node_id"]))
        for match in matches:
            del match["_ordering"]
        return matches[:limit]

    def graph(self, node_id: str) -> Dict[str, Any]:
        """Return one graph node and all directly incident typed edges."""
        with self._lock:
            if self._connection is None:
                raise RuntimeError("Vector graph is closed")
            row = self._connection.execute(
                "SELECT * FROM nodes WHERE node_id = ?", (node_id,)
            ).fetchone()
            if row is None:
                raise KeyError(f"Unknown graph node: {node_id}")
            vector = self._connection.execute(
                "SELECT * FROM vectors WHERE node_id = ?", (node_id,)
            ).fetchone()
            edges = self._connection.execute(
                """SELECT source_id, target_id, relation FROM edges
                   WHERE source_id=? OR target_id=? ORDER BY relation, source_id, target_id""",
                (node_id, node_id),
            ).fetchall()
        result = {
            "node_id": row["node_id"],
            "kind": row["kind"],
            "label": row["label"],
            "payload": json.loads(row["payload_json"]),
            "edges": [dict(edge) for edge in edges],
        }
        if vector:
            result["vector"] = {
                "values": json.loads(vector["values_json"]),
                "dimensions": json.loads(vector["dimensions_json"]),
                "units": json.loads(vector["units_json"]),
                "reference_frame": vector["reference_frame"],
                "source_return_id": vector["source_return_id"],
            }
        return result
