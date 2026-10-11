# origin_signature: MrLiouWord
"""
Tests for the MRL black hole model
MRL 黑洞模型測試
"""

from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import pytest

from mrl_blackhole import (
    BlackHoleBuilder,
    audit_conservation,
    default_model,
    fetch_snapshot,
    make_return_id,
)
from mrl_blackhole.conservation import round_trip_hours
from mrl_blackhole.snapshot import flatten_page


class FakeNotionClient:
    """Record requests instead of calling Notion / 記錄請求而不是真的呼叫 Notion"""

    def __init__(self) -> None:
        self.calls: List[Dict[str, Any]] = []
        self._counter = 0

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self.calls.append({"method": method, "path": path, "payload": payload})
        self._counter += 1
        return {"id": f"id-{self._counter}"}

    def calls_for(self, method: str, path_prefix: str) -> List[Dict[str, Any]]:
        return [
            call
            for call in self.calls
            if call["method"] == method and call["path"].startswith(path_prefix)
        ]


@pytest.fixture
def model():
    return default_model()


@pytest.mark.unit
def test_model_has_the_five_shells(model):
    assert model.layer_keys() == [
        "event_horizon",
        "accretion_disk",
        "singularity",
        "hawking_radiation",
        "return_ledger",
    ]


@pytest.mark.unit
def test_every_layer_has_exactly_one_title_property(model):
    for layer in model.layers:
        titles = [prop for prop in layer.properties if prop.type == "title"]
        assert len(titles) == 1, f"{layer.key} must have exactly one title property"


@pytest.mark.unit
def test_relations_only_target_known_layers(model):
    keys = set(model.layer_keys())
    for layer in model.layers:
        for prop in layer.relation_properties():
            assert prop.relation_to in keys


@pytest.mark.unit
def test_return_ledger_closes_the_loop(model):
    targets = {prop.relation_to for prop in model.layer("return_ledger").relation_properties()}
    assert targets == {"event_horizon", "hawking_radiation"}


@pytest.mark.unit
def test_relation_schema_is_skipped_until_the_target_exists(model):
    relation = model.layer("accretion_disk").relation_properties()[0]
    assert relation.to_notion_schema(lambda key: None) is None
    schema = relation.to_notion_schema({"event_horizon": "db-1"}.get)
    assert schema["relation"]["database_id"] == "db-1"


@pytest.mark.unit
def test_plan_describes_the_whole_build_without_a_client(tmp_path):
    builder = BlackHoleBuilder(manifest_path=tmp_path / "manifest.json")
    plan = builder.plan("parent-page")

    steps = [op["step"] for op in plan["operations"]]
    assert steps.count("create_root_page") == 1
    assert steps.count("create_database") == 5
    assert steps.count("patch_relations") == 4
    assert plan["model"]["version"] == default_model().version


@pytest.mark.unit
def test_build_creates_root_page_then_databases_then_relations(tmp_path):
    client = FakeNotionClient()
    manifest_path = tmp_path / "manifest.json"
    manifest = BlackHoleBuilder(client=client, manifest_path=manifest_path).build("parent-page")

    assert len(client.calls_for("POST", "/pages")) == 1
    assert len(client.calls_for("POST", "/databases")) == 5
    assert len(manifest["databases"]) == 5
    assert manifest_path.exists()

    patches = client.calls_for("PATCH", "/databases/")
    assert len(patches) == 4
    for patch in patches:
        for schema in patch["payload"]["properties"].values():
            assert schema["relation"]["database_id"] in manifest["databases"].values()


@pytest.mark.unit
def test_build_is_idempotent(tmp_path):
    manifest_path = tmp_path / "manifest.json"
    first_client = FakeNotionClient()
    first = BlackHoleBuilder(client=first_client, manifest_path=manifest_path).build("parent-page")

    second_client = FakeNotionClient()
    second = BlackHoleBuilder(client=second_client, manifest_path=manifest_path).build("parent-page")

    assert second["databases"] == first["databases"]
    assert second["root_page_id"] == first["root_page_id"]
    assert second["created"] == []
    assert second_client.calls_for("POST", "/pages") == []
    assert second_client.calls_for("POST", "/databases") == []


@pytest.mark.unit
def test_manifest_is_readable_json(tmp_path):
    manifest_path = tmp_path / "nested" / "manifest.json"
    BlackHoleBuilder(client=FakeNotionClient(), manifest_path=manifest_path).build("parent-page")
    stored = json.loads(manifest_path.read_text(encoding="utf-8"))
    assert stored["model_title"] == default_model().title


@pytest.mark.unit
def test_build_without_client_refuses_to_guess():
    with pytest.raises(RuntimeError, match="plan"):
        BlackHoleBuilder().build("parent-page")


@pytest.mark.unit
def test_return_id_is_deterministic_and_distinct():
    first = make_return_id("對話 Chat", "豆花配方", "2026-01-01T00:00:00+00:00")
    again = make_return_id("對話 Chat", "豆花配方", "2026-01-01T00:00:00+00:00")
    other = make_return_id("檔案 File", "豆花配方", "2026-01-01T00:00:00+00:00")

    assert first == again
    assert first != other
    assert first.startswith("RID-")


@pytest.mark.unit
def test_round_trip_hours_handles_zulu_and_missing_values():
    assert round_trip_hours("2026-01-01T00:00:00Z", "2026-01-01T06:00:00Z") == 6.0
    assert round_trip_hours(None, "2026-01-01T06:00:00Z") is None
    assert round_trip_hours("not-a-date", "2026-01-01T06:00:00Z") is None


def _now() -> datetime:
    return datetime(2026, 1, 10, tzinfo=timezone.utc)


def _captured(title: str, return_id: str, hours_ago: int) -> Dict[str, Any]:
    return {
        "title": title,
        "return_id": return_id,
        "captured_at": (_now() - timedelta(hours=hours_ago)).isoformat(),
    }


@pytest.mark.unit
def test_a_closed_loop_is_conserved():
    report = audit_conservation(
        captured=[_captured("語場封包", "RID-aaa", 4)],
        radiated=[{"title": "語場封包 v1", "return_id": "RID-aaa", "acknowledged": True}],
        now=_now(),
    )

    assert report.conserved
    assert report.returned == 1
    assert report.warnings == []


@pytest.mark.unit
def test_delivered_but_unacknowledged_is_only_a_warning():
    report = audit_conservation(
        captured=[_captured("語場封包", "RID-aaa", 4)],
        radiated=[{"title": "語場封包 v1", "return_id": "RID-aaa"}],
        now=_now(),
    )

    assert report.conserved
    assert [warning.kind for warning in report.warnings] == ["unacknowledged_output"]


@pytest.mark.unit
def test_an_object_that_never_comes_back_is_a_violation():
    report = audit_conservation(
        captured=[_captured("重要檔案", "RID-bbb", 200)],
        radiated=[],
        now=_now(),
    )

    assert not report.conserved
    assert [violation.kind for violation in report.violations] == ["swallowed"]


@pytest.mark.unit
def test_recent_objects_are_pending_not_swallowed():
    report = audit_conservation(
        captured=[_captured("剛丟進來的東西", "RID-ccc", 2)],
        radiated=[],
        now=_now(),
    )

    assert report.conserved
    assert report.pending == 1


@pytest.mark.unit
def test_missing_duplicate_and_orphan_return_ids_are_violations():
    report = audit_conservation(
        captured=[
            {"title": "無編號物件", "return_id": "", "captured_at": _now().isoformat()},
            _captured("第一份", "RID-ddd", 1),
            _captured("重複編號", "RID-ddd", 1),
        ],
        radiated=[
            {"title": "第一份輸出", "return_id": "RID-ddd", "acknowledged": True},
            {"title": "來路不明的輸出", "return_id": "RID-zzz", "acknowledged": True},
            {"title": "沒有編號的輸出", "acknowledged": True},
        ],
        now=_now(),
    )

    kinds = sorted(violation.kind for violation in report.violations)
    assert kinds == ["duplicate_return_id", "missing_return_id", "orphan_output", "untraceable_output"]
    assert not report.conserved


@pytest.mark.unit
def test_report_summary_is_human_readable():
    report = audit_conservation(captured=[], radiated=[], now=_now())
    assert "守恆 CONSERVED" in report.summary()


def _title(text: str) -> Dict[str, Any]:
    return {"type": "title", "title": [{"plain_text": text}]}


def _rich_text(text: str) -> Dict[str, Any]:
    return {"type": "rich_text", "rich_text": [{"plain_text": text}]}


class FakeQueryClient:
    """Serve canned database query responses / 提供預錄的資料庫查詢回應"""

    def __init__(self, pages_by_database: Dict[str, List[List[Dict[str, Any]]]]) -> None:
        self.pages_by_database = pages_by_database
        self.queried: List[str] = []

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        database_id = path.split("/")[2]
        self.queried.append(path)
        batches = self.pages_by_database[database_id]
        index = 0 if not payload or "start_cursor" not in payload else int(payload["start_cursor"])
        has_more = index + 1 < len(batches)
        return {
            "results": batches[index],
            "has_more": has_more,
            "next_cursor": str(index + 1) if has_more else None,
        }


@pytest.mark.unit
def test_flatten_page_reads_every_property_type():
    page = {
        "id": "page-1",
        "properties": {
            "物件 Object": _title("豆花配方"),
            "入境時間 Captured At": {"type": "date", "date": {"start": "2026-01-01T00:00:00Z"}},
            "接收確認 Acknowledged": {"type": "checkbox", "checkbox": True},
            "狀態 State": {"type": "select", "select": {"name": "已捕獲 Captured"}},
        },
    }
    flattened = flatten_page(
        page,
        {
            "title": "物件 Object",
            "captured_at": "入境時間 Captured At",
            "acknowledged": "接收確認 Acknowledged",
            "state": "狀態 State",
            "return_id": "回歸編號 Return ID",
        },
    )

    assert flattened["title"] == "豆花配方"
    assert flattened["captured_at"] == "2026-01-01T00:00:00Z"
    assert flattened["acknowledged"] is True
    assert flattened["state"] == "已捕獲 Captured"
    assert flattened["return_id"] is None


@pytest.mark.unit
def test_fetch_snapshot_paginates_and_feeds_the_audit():
    captured_pages = [
        [
            {
                "id": "page-1",
                "properties": {
                    "物件 Object": _title("豆花配方"),
                    "回歸編號 Return ID": _rich_text("RID-abc"),
                    "入境時間 Captured At": {"type": "date", "date": {"start": "2026-01-09T00:00:00Z"}},
                },
            }
        ],
        [
            {
                "id": "page-2",
                "properties": {
                    "物件 Object": _title("語場封包"),
                    "回歸編號 Return ID": _rich_text("RID-def"),
                    "入境時間 Captured At": {"type": "date", "date": {"start": "2026-01-09T00:00:00Z"}},
                },
            }
        ],
    ]
    radiated_pages = [
        [
            {
                "id": "page-3",
                "properties": {
                    "輸出 Output": _title("豆花配方 v1"),
                    "回歸編號 Return ID": _rich_text("RID-abc"),
                    "接收確認 Acknowledged": {"type": "checkbox", "checkbox": True},
                },
            },
            {
                "id": "page-4",
                "properties": {
                    "輸出 Output": _title("語場封包 v1"),
                    "回歸編號 Return ID": _rich_text("RID-def"),
                    "接收確認 Acknowledged": {"type": "checkbox", "checkbox": True},
                },
            },
        ]
    ]
    client = FakeQueryClient({"db-horizon": captured_pages, "db-radiation": radiated_pages})
    manifest = {"databases": {"event_horizon": "db-horizon", "hawking_radiation": "db-radiation"}}

    snapshot = fetch_snapshot(client, manifest)

    assert len(snapshot["captured"]) == 2
    assert len(snapshot["radiated"]) == 2
    assert len(client.queried) == 3  # two pages for the horizon, one for the radiation

    report = audit_conservation(snapshot["captured"], snapshot["radiated"], now=_now())
    assert report.conserved
    assert report.returned == 2


@pytest.mark.unit
def test_fetch_snapshot_refuses_an_incomplete_manifest():
    with pytest.raises(RuntimeError, match="hawking_radiation"):
        fetch_snapshot(FakeQueryClient({}), {"databases": {"event_horizon": "db-horizon"}})
