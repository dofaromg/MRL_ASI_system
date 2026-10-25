# origin_signature: MrLiouWord
"""Append-only canonical integration; legacy model and builder remain historical."""
from __future__ import annotations

import argparse
import copy
import hashlib
import json
import os
from dataclasses import replace
from datetime import datetime, timezone
from pathlib import Path

from .builder import BlackHoleBuilder, NotionAPIClient, _text
from .model import PropertySpec, default_model
from .snapshot import flatten_page
from .conservation import audit_conservation, Violation

SCOPE = "MRL_BLACKHOLE_CANONICAL_V1"
CANONICAL = "3ede7f4e6c558064a840e3a531cb2aef"
MOTHER = "3e9e7f4e6c5580e49f3dc8292dda835a"
ORIGIN = "MrLiouWord"
BINDINGS_PATH = Path(__file__).with_name("canonical_bindings.json")
LINEAGE = ("source_id", "original_name", "original_author", "source_times",
           "version_revision", "parent_source", "derived_from",
           "canonical_target", "origin_signature", "content_sha256")


def norm(value):
    return value.replace("-", "").lower()


def paginate(client, method, path, payload=None):
    cursor = None
    seen = set()
    result = []
    while True:
        body = dict(payload or {})
        if cursor:
            body["start_cursor"] = cursor
        response = client.request(method, path, body)
        result.extend(response.get("results", []))
        if not response.get("has_more"):
            return result
        cursor = response.get("next_cursor")
        if not cursor or cursor in seen:
            raise RuntimeError("Incomplete or cyclic Notion pagination")
        seen.add(cursor)


def bound_model(bindings):
    layers = []
    for layer in default_model().layers:
        mapping = bindings["layers"][layer.key].get("property_map", {})
        props = [replace(p, name=mapping.get(p.name, p.name),
                         type="rich_text" if layer.key == "return_ledger"
                         and p.type == "title" else p.type)
                 for p in layer.properties]
        # The existing ledger title remains its original relation-name property.
        if layer.key == "return_ledger":
            props.insert(0, PropertySpec(bindings["layers"][layer.key]["title_property"], "title"))
        present = {p.name for p in props}
        for name in ("mrl_model_scope",) + LINEAGE:
            if name not in present:
                props.append(PropertySpec(name, "url" if name == "canonical_target" else "rich_text"))
        if layer.key != "event_horizon":
            props.append(PropertySpec("來源登錄 Source Registry", "relation", relation_to="event_horizon"))
        if not any(p.name == "回歸編號 Return ID" for p in props):
            props.append(PropertySpec("回歸編號 Return ID", "rich_text"))
        layers.append(replace(layer, properties=props))
    original = default_model()
    return replace(original, version=original.version + "+canonical.1", layers=layers)


class CanonicalAPIClient(NotionAPIClient):
    def _headers(self):
        headers = super()._headers()
        headers["Notion-Version"] = "2025-09-03"
        return headers

    def request(self, method, path, payload=None):
        # Avoid logging private response bodies or blindly retrying mutations.
        import requests
        response = requests.request(method, "https://api.notion.com/v1" + path,
                                    headers=self._headers(), json=payload,
                                    timeout=self.timeout)
        if response.status_code >= 400:
            raise RuntimeError(f"Notion {method} {path}: HTTP {response.status_code}")
        return response.json()


class CanonicalBlackHoleBuilder(BlackHoleBuilder):
    def __init__(self, client=None, manifest_path=None, bindings=None):
        self.bindings = copy.deepcopy(bindings or json.loads(BINDINGS_PATH.read_text(encoding="utf-8")))
        if self.bindings.get("canonical_authority") != "Mr.liou":
            raise ValueError("canonical_authority mismatch")
        if self.bindings.get("origin_signature") != ORIGIN:
            raise ValueError("origin_signature mismatch")
        if norm(self.bindings["canonical_navigation_id"]) != CANONICAL:
            raise ValueError("canonical navigation mismatch")
        if norm(self.bindings["mother_page_id"]) != MOTHER:
            raise ValueError("canonical mother mismatch")
        super().__init__(model=bound_model(self.bindings), client=client, manifest_path=manifest_path)

    def _validate_manifest(self, manifest):
        if not manifest:
            return
        for key, expected in (("canonical_navigation_id", CANONICAL),
                              ("root_page_id", MOTHER)):
            if norm(manifest.get(key, "")) != expected:
                raise ValueError(f"Manifest {key} mismatch; legacy manifests require explicit review")
        if manifest.get("canonical_authority") != "Mr.liou":
            raise ValueError("Manifest canonical_authority mismatch")
        if manifest.get("origin_signature") != ORIGIN:
            raise ValueError("Manifest origin_signature mismatch")
        if manifest.get("model_scope") != SCOPE:
            raise ValueError("Manifest model scope mismatch")
        for key, item in self.bindings["layers"].items():
            known = manifest.get("databases", {}).get(key)
            if known and item.get("database_id") and norm(known) != norm(item["database_id"]):
                raise ValueError(f"Manifest binding conflict: {key}")
            source = manifest.get("data_sources", {}).get(key)
            if source and item.get("data_source_id") and norm(source) != norm(item["data_source_id"]):
                raise ValueError(f"Manifest data source conflict: {key}")

    def save_manifest(self, manifest):
        if not self.manifest_path:
            raise ValueError("A durable manifest path is required for build")
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        # Every checkpoint is retained, including failures; current pointer is atomic.
        stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
        text = json.dumps(manifest, ensure_ascii=False, indent=2) + "\n"
        history = self.manifest_path.parent / (self.manifest_path.name + ".history")
        history.mkdir(exist_ok=True)
        checkpoint = history / (stamp + ".json")
        with checkpoint.open("x", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        temporary = self.manifest_path.with_name(self.manifest_path.name + ".tmp")
        with temporary.open("w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.manifest_path)
        return self.manifest_path

    def _schema(self, layer, sources):
        properties = {}
        for prop in layer.properties:
            if prop.type == "relation":
                target = sources.get(prop.relation_to)
                if target:
                    properties[prop.name] = {"relation": {"data_source_id": target,
                                                          "single_property": {}}}
            else:
                properties[prop.name] = prop.to_notion_schema()
        return properties

    def _missing_properties(self, layer, live, sources):
        existing = live.get("properties")
        if not isinstance(existing, dict):
            raise RuntimeError("Notion schema unavailable")
        missing = {}
        for name, wanted in self._schema(layer, sources).items():
            current = existing.get(name)
            kind = next(iter(wanted))
            if current is None:
                if kind == "title" and any(p.get("type") == "title" for p in existing.values()):
                    raise ValueError("Cannot add or rename an existing title")
                missing[name] = wanted
                continue
            if current.get("type") != kind:
                raise ValueError(f"Schema type conflict: {layer.key}/{name}")
            if kind == "relation":
                if norm(current.get("relation", {}).get("data_source_id", "")) != norm(wanted["relation"]["data_source_id"]):
                    raise ValueError(f"Relation target conflict: {layer.key}/{name}")
            if kind in ("select", "multi_select"):
                expected = {o["name"] for o in wanted[kind]["options"]}
                actual = {o["name"] for o in current[kind].get("options", [])}
                if not expected <= actual:
                    # Do not replace option IDs or remove historical options.
                    raise ValueError(f"Missing enum options require explicit additive review: {name}")
        return missing

    def _resolve(self, manifest):
        ids = dict(manifest.get("databases", {}))
        sources = dict(manifest.get("data_sources", {}))
        missing = []
        for layer in self.model.layers:
            binding = self.bindings["layers"][layer.key]
            db_id = ids.get(layer.key) or binding.get("database_id")
            if not db_id:
                # Existing Node Lookup under the existing mother; never create another root.
                blocks = paginate(self.client, "GET", f"/blocks/{MOTHER}/children", {"page_size": 100})
                matches = [b["id"] for b in blocks if b.get("type") == "child_database"
                           and b.get("child_database", {}).get("title") == layer.title]
                if len(matches) > 1:
                    raise ValueError(f"Ambiguous existing node: {layer.key}")
                db_id = matches[0] if matches else None
            if not db_id:
                missing.append(layer)
                continue
            db = self.client.request("GET", f"/databases/{db_id}")
            if db.get("archived") or db.get("in_trash"):
                raise ValueError(f"Archived binding: {layer.key}")
            expected_parent = binding.get("parent_page_id", MOTHER)
            if norm(db.get("parent", {}).get("page_id", "")) != norm(expected_parent):
                raise ValueError(f"Database parent conflict: {layer.key}")
            source_id = sources.get(layer.key) or binding.get("data_source_id")
            choices = db.get("data_sources", [])
            if source_id:
                if not any(norm(d["id"]) == norm(source_id) for d in choices):
                    raise ValueError(f"Data source not in database: {layer.key}")
            elif len(choices) == 1:
                source_id = choices[0]["id"]
            else:
                raise ValueError(f"Ambiguous data source: {layer.key}")
            ids[layer.key], sources[layer.key] = db_id, source_id
        if len({norm(v) for v in sources.values()}) != len(sources):
            raise ValueError("Layers must not share a data source without a discriminator")
        return ids, sources, missing

    def plan(self, parent_page_id=MOTHER):
        if norm(parent_page_id) != MOTHER:
            raise ValueError("Only the existing canonical mother is an allowed parent")
        manifest = self.load_manifest()
        self._validate_manifest(manifest)
        if not self.client:
            return {"status": "OFFLINE_BINDING_PLAN_NOT_LIVE_ACCEPTANCE",
                    "canonical_navigation_id": CANONICAL, "root_page_id": MOTHER,
                    "model": self.model.to_dict(), "bindings": self.bindings}
        for page_id in (CANONICAL, MOTHER):
            page = self.client.request("GET", f"/pages/{page_id}")
            if page.get("archived") or page.get("in_trash"):
                raise ValueError("Canonical page is archived")
        ids, sources, absent = self._resolve(manifest)
        live = {key: self.client.request("GET", f"/data_sources/{source}")
                for key, source in sources.items()}
        operations = []
        for layer in self.model.layers:
            if layer in absent:
                operations.append({"step": "create_missing_database", "layer": layer.key})
            else:
                props = self._missing_properties(layer, live[layer.key], sources)
                if props:
                    operations.append({"step": "add_properties", "layer": layer.key, "properties": props})
        return {"status": "LIVE_PREFLIGHT", "databases": ids, "data_sources": sources,
                "operations": operations, "schemas": live}

    def build(self, parent_page_id=MOTHER):
        if not self.client or not self.manifest_path:
            raise ValueError("Client and durable manifest path required")
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        lock = self.manifest_path.with_name(self.manifest_path.name + ".lock")
        # A stale lock must be investigated, never silently removed.
        with lock.open("x", encoding="utf-8") as handle:
            handle.write(str(os.getpid()))
        try:
            plan = self.plan(parent_page_id)  # all known schema conflicts precede mutations
            manifest = self.load_manifest()
            manifest.update({"canonical_navigation_id": CANONICAL, "root_page_id": MOTHER,
                             "canonical_authority": "Mr.liou", "origin_signature": ORIGIN,
                             "model_scope": SCOPE, "model_version": self.model.version,
                             "databases": plan["databases"], "data_sources": plan["data_sources"]})
            manifest.setdefault("created_at", datetime.now(timezone.utc).isoformat())
            manifest["status"] = "BUILD_IN_PROGRESS"
            self.save_manifest(manifest)
            for operation in plan["operations"]:
                if operation["step"] != "create_missing_database":
                    continue
                layer = self.model.layer(operation["layer"])
                payload = {"parent": {"type": "page_id", "page_id": MOTHER},
                           "title": _text(layer.title),
                           "description": _text(layer.purpose + " · " + SCOPE + " · " + ORIGIN),
                           "initial_data_source": {"properties": self._schema(layer, {})}}
                db = self.client.request("POST", "/databases", payload)
                # Save acknowledged database ID before resolving its data source.
                manifest["databases"][layer.key] = db["id"]
                self.save_manifest(manifest)
                sources = db.get("data_sources", [])
                if len(sources) != 1:
                    db = self.client.request("GET", f"/databases/{db['id']}")
                    sources = db.get("data_sources", [])
                if len(sources) != 1:
                    raise ValueError("New database data source unresolved")
                manifest["data_sources"][layer.key] = sources[0]["id"]
                self.save_manifest(manifest)
            for layer in self.model.layers:
                source = manifest["data_sources"][layer.key]
                live = self.client.request("GET", f"/data_sources/{source}")
                missing = self._missing_properties(layer, live, manifest["data_sources"])
                if missing:
                    self.client.request("PATCH", f"/data_sources/{source}", {"properties": missing})
                    self.save_manifest(manifest)
                reread = self.client.request("GET", f"/data_sources/{source}")
                if self._missing_properties(layer, reread, manifest["data_sources"]):
                    raise RuntimeError(f"Schema readback incomplete: {layer.key}")
            manifest["status"] = "STRUCTURE_READBACK_PASS"
            manifest["updated_at"] = datetime.now(timezone.utc).isoformat()
            self.save_manifest(manifest)
            return manifest
        finally:
            lock.unlink()


def make_lineage_return_id(source_id, original_time, version):
    """New lineage ID; the original v1 function and its historical IDs are unchanged."""
    values = (source_id, original_time, version)
    if any(not isinstance(v, str) or not v.strip() for v in values):
        raise ValueError("Source ID, original timestamp and version are required")
    payload = json.dumps(values, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    return "RID-L1-" + hashlib.sha256(payload).hexdigest()


def snapshot(client, manifest, bindings=None):
    builder = CanonicalBlackHoleBuilder(client=client, bindings=bindings)
    builder._validate_manifest(manifest)
    sources = manifest.get("data_sources", {})
    if set(sources) != set(builder.model.layer_keys()):
        raise ValueError("Snapshot requires all five resolved data sources")
    result = {"model_scope": SCOPE, "origin_signature": ORIGIN,
              "fetched_at": datetime.now(timezone.utc).isoformat(), "complete": True, "layers": {}}
    for layer in builder.model.layers:
        fields = {p.name: p.name for p in layer.properties}
        rows = paginate(client, "POST", f"/data_sources/{sources[layer.key]}/query",
                        {"page_size": 100, "filter": {"property": "mrl_model_scope",
                                                     "rich_text": {"equals": SCOPE}}})
        values = []
        for row in rows:
            # Fail closed on truncated relation values rather than certifying partial lineage.
            if any(p.get("has_more") for p in row.get("properties", {}).values()):
                raise RuntimeError("Truncated page properties require full property retrieval")
            value = flatten_page(row, fields)
            value["return_id"] = value["回歸編號 Return ID"]
            values.append(value)
        result["layers"][layer.key] = values
    return result


def audit_snapshot(data, now=None, overdue_hours=72):
    if data.get("complete") is not True or data.get("model_scope") != SCOPE:
        raise ValueError("Incomplete or wrong-scope snapshot")
    layers = data["layers"]
    if set(layers) != set(default_model().layer_keys()):
        raise ValueError("All five layers required")
    captured = [dict(r, captured_at=r.get("入境時間 Captured At")) for r in layers["event_horizon"]]
    outputs = [dict(r, delivered_at=r.get("交付時間 Delivered At"),
                    acknowledged=r.get("接收確認 Acknowledged")) for r in layers["hawking_radiation"]]
    report = audit_conservation(captured, outputs, now=now, overdue_hours=overdue_hours)
    def fail(kind, row, detail):
        report.violations.append(Violation(kind, row.get("return_id"), row.get("original_name") or "", detail))
    refs = {key: {norm(r["page_id"]): r for r in rows} for key, rows in layers.items()}
    edges = {"accretion_disk": ("來源物件 Captured Object", "event_horizon"),
             "singularity": ("來源粒子 Source Particle", "accretion_disk"),
             "hawking_radiation": ("來源核心 Source Core", "singularity")}
    for key, rows in layers.items():
        seen = set()
        for row in rows:
            rid = row.get("return_id")
            if rid in seen or not rid:
                fail("duplicate_or_missing_layer_return_id", row, key)
            seen.add(rid)
            if row.get("mrl_model_scope") != SCOPE:
                fail("scope_mismatch", row, key)
            if row.get("origin_signature") != ORIGIN or row.get("canonical_target") != "https://app.notion.com/p/" + CANONICAL:
                fail("authority_mismatch", row, key)
            if any(not row.get(name) for name in LINEAGE if name not in ("parent_source", "derived_from", "content_sha256")):
                fail("missing_source_lineage", row, key)
            if key in edges:
                prop, target = edges[key]
                links = row.get(prop) or []
                if not links or any(norm(link) not in refs[target] or refs[target][norm(link)].get("return_id") != rid
                                    for link in links):
                    fail("broken_layer_relation", row, prop)
            if key != "event_horizon":
                links = row.get("來源登錄 Source Registry") or []
                if not links or any(norm(link) not in refs["event_horizon"] or
                                    refs["event_horizon"][norm(link)].get("source_id") != row.get("source_id")
                                    for link in links):
                    fail("broken_source_registry", row, key)
                else:
                    for link in links:
                        source_row = refs["event_horizon"][norm(link)]
                        if any(row.get(name) != source_row.get(name) for name in
                               ("original_name", "original_author", "source_times", "version_revision")):
                            fail("source_lineage_mismatch", row, key)
    ledger_by_rid = {}
    for row in layers["return_ledger"]:
        ledger_by_rid.setdefault(row.get("return_id"), []).append(row)
        for prop, target in (("入境物件 Inbound", "event_horizon"), ("輸出成果 Outbound", "hawking_radiation")):
            links = row.get(prop) or []
            # Empty outbound is allowed for pending entries only; base audit checks overdue.
            if not links and target == "event_horizon":
                fail("broken_ledger_relation", row, prop)
            if any(norm(link) not in refs[target] or refs[target][norm(link)].get("return_id") != row.get("return_id")
                   for link in links):
                fail("broken_ledger_relation", row, prop)
    for row in captured:
        entries = ledger_by_rid.get(row.get("return_id"), [])
        if len(entries) != 1:
            fail("missing_or_duplicate_ledger", row, "Exactly one ledger entry required")
        if any(o.get("return_id") == row.get("return_id") for o in outputs):
            if not entries or not entries[0].get("輸出成果 Outbound"):
                fail("missing_ledger_output", row, "Delivered output must be linked")
    for row in outputs:
        start = next((r.get("captured_at") for r in captured if r.get("return_id") == row.get("return_id")), None)
        try:
            begin = datetime.fromisoformat((start or "").replace("Z", "+00:00"))
            end = datetime.fromisoformat((row.get("delivered_at") or "").replace("Z", "+00:00"))
            if begin.tzinfo is None or end.tzinfo is None or end < begin:
                raise ValueError()
        except (ValueError, TypeError):
            fail("invalid_delivery_time", row, "Delivery requires ordered timezone-aware timestamps")
    # Pending is reported distinctly; no-output empty snapshots never establish live runtime acceptance.
    result = report.to_dict()
    result["runtime_acceptance"] = "PASS" if report.conserved and report.captured > 0 and report.pending == 0 and not report.warnings else "HOLD"
    return result


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("command", choices=("plan", "build", "snapshot", "audit"))
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--snapshot", type=Path)
    args = parser.parse_args()
    if args.command == "audit":
        result = audit_snapshot(json.loads(args.snapshot.read_text(encoding="utf-8")))
    else:
        builder = CanonicalBlackHoleBuilder(client=CanonicalAPIClient(), manifest_path=args.manifest)
        if args.command == "plan":
            result = builder.plan()
        elif args.command == "build":
            result = builder.build()
        else:
            result = snapshot(builder.client, builder.load_manifest())
    if args.command == "snapshot":
        if not args.snapshot:
            parser.error("--snapshot is required")
        args.snapshot.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
        print("Snapshot saved locally; contents not printed")
    else:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    if args.command == "audit" and not result["conserved"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
