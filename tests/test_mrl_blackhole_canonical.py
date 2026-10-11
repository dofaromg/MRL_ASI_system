# origin_signature: MrLiouWord
import copy
import json
from datetime import datetime, timezone
from pathlib import Path

import pytest

from mrl_blackhole.canonical import (
    BINDINGS_PATH, CANONICAL, MOTHER, ORIGIN, SCOPE, LINEAGE,
    CanonicalBlackHoleBuilder, audit_snapshot, bound_model, make_lineage_return_id,
    paginate, snapshot,
)


def bindings():
    return json.loads(BINDINGS_PATH.read_text(encoding="utf-8"))


class Client:
    def __init__(self, missing_delivery=False):
        self.calls = []
        self.dbs = {}
        self.sources = {}
        self.fail_create = False
        self.fail_patch = False
        self.rows = {}
        b = bindings()
        self.model = bound_model(b)
        for layer in self.model.layers:
            item = b["layers"][layer.key]
            db = item.get("database_id")
            source = item.get("data_source_id")
            if layer.key == "hawking_radiation":
                if missing_delivery:
                    continue
                db = db or "delivery-db"
                source = source or "delivery-source"
            self.dbs[db] = {"id": db, "parent": {"page_id": item["parent_page_id"]},
                            "data_sources": [{"id": source}]}
            title = layer.title_property().name
            self.sources[source] = {"id": source, "properties": {title: {"type": "title", "title": {}}}}

    def request(self, method, path, payload=None):
        self.calls.append((method, path, copy.deepcopy(payload)))
        if path.startswith("/pages/"):
            return {"id": path.split("/")[-1]}
        if path.startswith("/blocks/"):
            return {"results": [{"id": db, "type": "child_database",
                                  "child_database": {"title": "L4 霍金輻射 Hawking Radiation"}}
                                 for db in self.dbs if db == "delivery-db"],
                    "has_more": False}
        if method == "GET" and path.startswith("/databases/"):
            return copy.deepcopy(self.dbs[path.split("/")[-1]])
        if method == "POST" and path == "/databases":
            if self.fail_create:
                raise TimeoutError("creation response unknown")
            db = {"id": "delivery-db", "parent": payload["parent"],
                  "data_sources": [{"id": "delivery-source"}]}
            self.dbs["delivery-db"] = db
            self.sources["delivery-source"] = {"properties": {}}
            for name, spec in payload["initial_data_source"]["properties"].items():
                self.sources["delivery-source"]["properties"][name] = dict(spec, type=next(iter(spec)))
            return copy.deepcopy(db)
        source = path.split("/")[2]
        if path.endswith("/query"):
            return {"results": self.rows.get(source, []), "has_more": False}
        if method == "GET":
            return copy.deepcopy(self.sources[source])
        if method == "PATCH":
            if self.fail_patch:
                self.fail_patch = False
                raise RuntimeError("patch failed")
            for name, spec in payload["properties"].items():
                self.sources[source]["properties"][name] = dict(spec, type=next(iter(spec)))
            return copy.deepcopy(self.sources[source])
        raise AssertionError((method, path))


def builder(tmp_path, client=None):
    return CanonicalBlackHoleBuilder(client=client or Client(),
                                     manifest_path=tmp_path / "manifest.json")


def test_reuse_four_existing_ids_and_preserve_titles(tmp_path):
    client = Client(missing_delivery=True)
    b = builder(tmp_path, client)
    result = b.build()
    assert result["status"] == "STRUCTURE_READBACK_PASS"
    assert result["root_page_id"] == MOTHER
    creates = [c for c in client.calls if c[0] == "POST"]
    assert len(creates) == 1 and creates[0][1] == "/databases"
    for c in client.calls:
        if c[0] == "PATCH":
            assert all(next(iter(spec)) != "title" for spec in c[2]["properties"].values())
    assert list((tmp_path / "manifest.json.history").glob("*.json"))


def test_rerun_is_read_only_and_manifest_loss_uses_lookup(tmp_path):
    client = Client(missing_delivery=True)
    b = builder(tmp_path, client)
    b.build()
    client.calls.clear()
    b.build()
    assert not [c for c in client.calls if c[0] in ("POST", "PATCH")]
    b.manifest_path.unlink()
    client.calls.clear()
    b.build()
    assert not [c for c in client.calls if c[0] in ("POST", "PATCH")]


def test_partial_failure_checkpoint_prevents_duplicate_database(tmp_path):
    client = Client(missing_delivery=True)
    client.fail_patch = True
    b = builder(tmp_path, client)
    with pytest.raises(RuntimeError, match="patch failed"):
        b.build()
    assert b.load_manifest()["databases"]["hawking_radiation"] == "delivery-db"
    assert not (tmp_path / "manifest.json.lock").exists()
    b.build()
    assert len([c for c in client.calls if c[:2] == ("POST", "/databases")]) == 1


@pytest.mark.parametrize("case", ["parent", "origin", "binding", "source", "scope"])
def test_manifest_conflicts_reject_before_mutation(tmp_path, case):
    b = builder(tmp_path)
    m = {"canonical_navigation_id": CANONICAL, "root_page_id": MOTHER,
         "origin_signature": ORIGIN, "model_scope": SCOPE}
    if case == "parent":
        m["root_page_id"] = "wrong"
    elif case == "origin":
        m["origin_signature"] = "wrong"
    elif case == "scope":
        m["model_scope"] = "wrong"
    elif case == "source":
        m["data_sources"] = {"event_horizon": "wrong"}
    else:
        m["databases"] = {"event_horizon": "wrong"}
    b.manifest_path.write_text(json.dumps(m))
    with pytest.raises(ValueError):
        b.build()
    assert not [c for c in b.client.calls if c[0] in ("POST", "PATCH")]


def test_schema_type_conflict_fails_before_writes(tmp_path):
    client = Client()
    source = bindings()["layers"]["event_horizon"]["data_source_id"]
    client.sources[source]["properties"]["回歸編號 Return ID"] = {"type": "number"}
    with pytest.raises(ValueError, match="type conflict"):
        builder(tmp_path, client).build()
    assert not [c for c in client.calls if c[0] in ("POST", "PATCH")]


def test_wrong_relation_target_fails_before_writes(tmp_path):
    client = Client()
    source = bindings()["layers"]["accretion_disk"]["data_source_id"]
    client.sources[source]["properties"]["來源物件 Captured Object"] = {
        "type": "relation", "relation": {"data_source_id": "wrong"}}
    with pytest.raises(ValueError, match="target conflict"):
        builder(tmp_path, client).build()
    assert not [c for c in client.calls if c[0] in ("POST", "PATCH")]


def test_concurrent_build_is_rejected(tmp_path):
    b = builder(tmp_path)
    (tmp_path / "manifest.json.lock").write_text("another operation")
    with pytest.raises(FileExistsError):
        b.build()
    assert not b.client.calls


def test_invalid_parent_rejects_before_network(tmp_path):
    b = builder(tmp_path)
    with pytest.raises(ValueError):
        b.build("parallel-root")
    assert not b.client.calls


def test_lookup_rejects_ambiguity(tmp_path):
    client = Client(missing_delivery=True)
    original = client.request
    def request(method, path, payload=None):
        if path.startswith("/blocks/"):
            return {"results": [{"id": str(i), "type": "child_database",
                     "child_database": {"title": "L4 霍金輻射 Hawking Radiation"}} for i in (1, 2)]}
        return original(method, path, payload)
    client.request = request
    with pytest.raises(ValueError, match="Ambiguous"):
        builder(tmp_path, client).build()


def test_pagination_fail_closed():
    class Bad:
        def request(self, *args):
            return {"results": [], "has_more": True, "next_cursor": None}
    with pytest.raises(RuntimeError):
        paginate(Bad(), "POST", "/query")


def test_lineage_id_preserves_delimiters_and_version():
    assert make_lineage_return_id("a|b", "c", "d") != make_lineage_return_id("a", "b|c", "d")
    assert make_lineage_return_id("id", "time", "v1") == make_lineage_return_id("id", "time", "v1")
    assert make_lineage_return_id("id", "time", "v1") != make_lineage_return_id("id", "time", "v2")
    with pytest.raises(ValueError):
        make_lineage_return_id("", "time", "v1")


def closed_snapshot():
    keys = bound_model(bindings()).layer_keys()
    rows = {}
    for index, key in enumerate(keys):
        row = {name: "original" for name in LINEAGE}
        row.update(page_id=str(index), return_id="RID-fixed", mrl_model_scope=SCOPE,
                   source_id="source-1", canonical_target="https://app.notion.com/p/" + CANONICAL,
                   origin_signature=ORIGIN)
        if index:
            row["來源登錄 Source Registry"] = ["0"]
        rows[key] = [row]
    rows["event_horizon"][0]["入境時間 Captured At"] = "2026-10-11T00:00:00Z"
    rows["accretion_disk"][0]["來源物件 Captured Object"] = ["0"]
    rows["singularity"][0]["來源粒子 Source Particle"] = ["1"]
    rows["hawking_radiation"][0].update({"來源核心 Source Core": ["2"],
                                      "交付時間 Delivered At": "2026-10-11T01:00:00Z",
                                      "接收確認 Acknowledged": True})
    rows["return_ledger"][0].update({"入境物件 Inbound": ["0"], "輸出成果 Outbound": ["3"]})
    return {"complete": True, "model_scope": SCOPE, "layers": rows}


def test_all_five_layers_closed():
    report = audit_snapshot(closed_snapshot())
    assert report["conserved"] and report["runtime_acceptance"] == "PASS"


@pytest.mark.parametrize("case", ["wrong_source", "missing_lineage", "wrong_origin",
                                "broken_edge", "missing_ledger", "missing_outbound",
                                "duplicate_output", "bad_delivery"])
def test_full_chain_regressions(case):
    data = closed_snapshot()
    layers = data["layers"]
    if case == "wrong_source":
        layers["singularity"][0]["source_id"] = "wrong"
    elif case == "missing_lineage":
        del layers["accretion_disk"][0]["version_revision"]
    elif case == "wrong_origin":
        layers["hawking_radiation"][0]["origin_signature"] = "wrong"
    elif case == "broken_edge":
        layers["hawking_radiation"][0]["來源核心 Source Core"] = ["absent"]
    elif case == "missing_ledger":
        layers["return_ledger"] = []
    elif case == "missing_outbound":
        layers["return_ledger"][0]["輸出成果 Outbound"] = []
    elif case == "duplicate_output":
        layers["hawking_radiation"].append(copy.deepcopy(layers["hawking_radiation"][0]))
    else:
        layers["hawking_radiation"][0]["交付時間 Delivered At"] = "2026-10-10T00:00:00Z"
    assert not audit_snapshot(data)["conserved"]


def test_empty_snapshot_is_not_runtime_acceptance():
    data = closed_snapshot()
    data["layers"] = {key: [] for key in data["layers"]}
    assert audit_snapshot(data)["runtime_acceptance"] == "HOLD"


def test_incomplete_snapshot_cannot_be_audited():
    data = closed_snapshot()
    data["complete"] = False
    with pytest.raises(ValueError):
        audit_snapshot(data)


def test_snapshot_scopes_queries_and_uses_data_sources(tmp_path):
    client = Client()
    b = builder(tmp_path, client)
    m = b.build()
    client.calls.clear()
    result = snapshot(client, m)
    assert result["complete"] and len(result["layers"]) == 5
    calls = [c for c in client.calls if c[0] == "POST"]
    assert len(calls) == 5
    assert all("/data_sources/" in c[1] and c[2]["filter"]["rich_text"]["equals"] == SCOPE for c in calls)
