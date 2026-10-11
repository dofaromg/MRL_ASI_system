# origin_signature: MrLiouWord
"""Tests for persistent celestial trajectory vector graphs."""

import pytest

from mrl_blackhole import CelestialVectorGraph


def _add_body_and_observations(graph):
    graph.add_body("earth", name="Earth", metadata={"catalog": "demo"})
    for observed_at, x in (
        ("2026-01-01T00:00:00Z", 0),
        ("2026-01-01T00:00:10Z", 10),
        ("2026-01-01T00:00:20Z", 40),
    ):
        graph.add_observation(
            "earth",
            observed_at=observed_at,
            position=(x, 0, 0),
            position_unit="km",
            reference_frame="ICRF",
            source_return_id=f"RID-{x}",
        )


@pytest.mark.unit
def test_trajectory_derives_velocity_acceleration_and_graph_edges(tmp_path):
    with CelestialVectorGraph(tmp_path / "celestial.sqlite") as graph:
        _add_body_and_observations(graph)
        patterns = graph.derive_trajectory_patterns("earth")

        assert len(patterns) == 3
        first_velocity = graph.graph(patterns[0])
        assert first_velocity["vector"]["values"] == [1.0, 0.0, 0.0]
        assert first_velocity["vector"]["dimensions"] == ["vx", "vy", "vz"]
        assert first_velocity["vector"]["units"] == ["km/s"] * 3
        assert first_velocity["vector"]["source_return_id"] == "RID-10"
        acceleration = graph.graph(patterns[-1])
        assert acceleration["vector"]["values"] == [0.2, 0.0, 0.0]
        assert acceleration["vector"]["units"] == ["km/s^2"] * 3
        assert len(
            [edge for edge in acceleration["edges"] if edge["relation"] == "derived_from"]
        ) == 3


@pytest.mark.unit
def test_trajectory_derivation_is_idempotent_and_persistent(tmp_path):
    database = tmp_path / "vectors.sqlite"
    graph = CelestialVectorGraph(database)
    _add_body_and_observations(graph)
    first = graph.derive_trajectory_patterns("earth")
    second = graph.derive_trajectory_patterns("earth")
    assert second == first
    graph.close()

    with CelestialVectorGraph(database) as reopened:
        assert reopened.graph(first[0])["vector"]["values"] == [1.0, 0.0, 0.0]


@pytest.mark.unit
def test_similarity_search_filters_by_dimensions_units_and_frame(tmp_path):
    with CelestialVectorGraph(tmp_path / "vectors.sqlite") as graph:
        graph.add_pattern(
            "east",
            label="Eastward motion",
            values=(1, 0, 0),
            dimensions=("vx", "vy", "vz"),
            units=("km/s",) * 3,
            reference_frame="ICRF",
            source_return_id="RID-east",
        )
        graph.add_pattern(
            "north",
            label="Northward motion",
            values=(0, 1, 0),
            dimensions=("vx", "vy", "vz"),
            units=("km/s",) * 3,
            reference_frame="ICRF",
            source_return_id="RID-north",
        )
        graph.add_pattern(
            "east-meters",
            label="Eastward motion in meters",
            values=(1000, 0, 0),
            dimensions=("vx", "vy", "vz"),
            units=("m/s",) * 3,
            reference_frame="ICRF",
            source_return_id="RID-east-m",
        )

        matches = graph.similar_patterns(
            (1, 0, 0),
            dimensions=("vx", "vy", "vz"),
            units=("km/s",) * 3,
            reference_frame="ICRF",
        )
        assert [match["label"] for match in matches] == ["Eastward motion", "Northward motion"]
        assert matches[0]["score"] == pytest.approx(1.0)
        assert matches[1]["score"] == pytest.approx(0.0)


@pytest.mark.unit
def test_euclidean_similarity_orders_by_distance(tmp_path):
    with CelestialVectorGraph(tmp_path / "vectors.sqlite") as graph:
        for pattern_id, value in (("near", 1.5), ("far", 10.0)):
            graph.add_pattern(
                pattern_id,
                label=pattern_id,
                values=(value, 0, 0),
                dimensions=("vx", "vy", "vz"),
                units=("km/s",) * 3,
                reference_frame="ICRF",
                source_return_id=f"RID-{pattern_id}",
            )
        matches = graph.similar_patterns(
            (1, 0, 0),
            dimensions=("vx", "vy", "vz"),
            units=("km/s",) * 3,
            reference_frame="ICRF",
            metric="euclidean",
        )
        assert [match["label"] for match in matches] == ["near", "far"]
        assert matches[0]["score"] == pytest.approx(0.5)


@pytest.mark.unit
def test_observations_require_explicit_units_frames_and_finite_vectors(tmp_path):
    with CelestialVectorGraph(tmp_path / "vectors.sqlite") as graph:
        graph.add_body("mars", name="Mars")
        with pytest.raises(ValueError, match="three coordinates"):
            graph.add_observation(
                "mars",
                observed_at="2026-01-01T00:00:00Z",
                position=(1, 2),
                position_unit="km",
                reference_frame="ICRF",
                source_return_id="RID-mars",
            )
        with pytest.raises(ValueError, match="finite"):
            graph.add_observation(
                "mars",
                observed_at="2026-01-01T00:00:00Z",
                position=(1, float("nan"), 3),
                position_unit="km",
                reference_frame="ICRF",
                source_return_id="RID-mars",
            )


@pytest.mark.unit
def test_observation_state_vector_retains_measured_position_and_velocity(tmp_path):
    with CelestialVectorGraph(tmp_path / "vectors.sqlite") as graph:
        graph.add_body("jupiter", name="Jupiter")
        observation_id = graph.add_observation(
            "jupiter",
            observed_at="2026-01-01T00:00:00Z",
            position=(1, 2, 3),
            position_unit="km",
            velocity=(4, 5, 6),
            velocity_unit="km/s",
            reference_frame="ICRF",
            source_return_id="RID-jupiter",
        )

        state = graph.graph(observation_id)["vector"]
        assert state["values"] == [1.0, 2.0, 3.0, 4.0, 5.0, 6.0]
        assert state["dimensions"] == ["x", "y", "z", "vx", "vy", "vz"]
        assert state["units"] == ["km"] * 3 + ["km/s"] * 3


@pytest.mark.unit
def test_trajectory_refuses_mixed_reference_frames(tmp_path):
    with CelestialVectorGraph(tmp_path / "vectors.sqlite") as graph:
        graph.add_body("venus", name="Venus")
        for observed_at, frame in (
            ("2026-01-01T00:00:00Z", "ICRF"),
            ("2026-01-01T00:00:01Z", "ECLIPJ2000"),
        ):
            graph.add_observation(
                "venus",
                observed_at=observed_at,
                position=(1, 2, 3),
                position_unit="km",
                reference_frame=frame,
                source_return_id="RID-venus",
            )
        with pytest.raises(ValueError, match="same reference frame"):
            graph.derive_trajectory_patterns("venus")
