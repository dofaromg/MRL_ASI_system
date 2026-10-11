# origin_signature: MrLiouWord
"""
Pull a conservation snapshot back out of Notion
從 Notion 取回守恆稽核所需的快照

The audit is only trustworthy if its input comes from the live structure, so
this module queries the event horizon and the Hawking radiation databases and
flattens their pages into the plain dictionaries ``audit_conservation`` reads.

稽核要可信，輸入就得來自真實結構。這個模組查詢事件視界與霍金輻射兩個資料庫，
把 Notion 頁面攤平成 ``audit_conservation`` 看得懂的字典。
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from .model import BlackHoleModel, default_model

PAGE_SIZE = 100


def _plain_text(rich_text: List[Dict[str, Any]]) -> str:
    return "".join(part.get("plain_text", "") for part in rich_text).strip()


def _read_property(prop: Dict[str, Any]) -> Any:
    """Flatten one Notion property value / 把單一 Notion 屬性值攤平"""
    prop_type = prop.get("type")
    value = prop.get(prop_type)
    if prop_type in ("title", "rich_text"):
        return _plain_text(value or [])
    if prop_type == "date":
        return (value or {}).get("start")
    if prop_type == "checkbox":
        return bool(value)
    if prop_type == "select":
        return (value or {}).get("name")
    if prop_type == "multi_select":
        return [option.get("name") for option in value or []]
    if prop_type == "relation":
        return [item.get("id") for item in value or []]
    return value


def flatten_page(page: Dict[str, Any], layer_properties: Dict[str, str]) -> Dict[str, Any]:
    """
    Map a Notion page onto the audit field names.
    把 Notion 頁面對應到稽核用的欄位名稱。

    ``layer_properties`` maps an audit field (``title``, ``return_id`` ...) to
    the Notion property name defined by the model.
    """
    properties = page.get("properties", {})
    flattened: Dict[str, Any] = {"page_id": page.get("id")}
    for field, property_name in layer_properties.items():
        prop = properties.get(property_name)
        flattened[field] = _read_property(prop) if prop else None
    return flattened


def query_database(client: Any, database_id: str) -> List[Dict[str, Any]]:
    """Read every page of a database / 讀取資料庫中的所有頁面"""
    pages: List[Dict[str, Any]] = []
    cursor: Optional[str] = None
    while True:
        payload: Dict[str, Any] = {"page_size": PAGE_SIZE}
        if cursor:
            payload["start_cursor"] = cursor
        response = client.request("POST", f"/databases/{database_id}/query", payload)
        pages.extend(response.get("results", []))
        if not response.get("has_more"):
            break
        cursor = response.get("next_cursor")
        if not cursor:
            break
    return pages


def _property_name(model: BlackHoleModel, layer_key: str, prefix: str) -> str:
    for prop in model.layer(layer_key).properties:
        if prop.name.startswith(prefix):
            return prop.name
    raise KeyError(f"Layer '{layer_key}' has no property starting with '{prefix}'")


def fetch_snapshot(
    client: Any, manifest: Dict[str, Any], model: Optional[BlackHoleModel] = None
) -> Dict[str, Any]:
    """
    Build the snapshot the conservation audit consumes.
    組出守恆稽核所需的快照。
    """
    model = model or default_model()
    databases = manifest.get("databases", {})
    missing = [key for key in ("event_horizon", "hawking_radiation") if key not in databases]
    if missing:
        raise RuntimeError(f"Manifest is missing database ids for: {', '.join(missing)}")

    captured_fields = {
        "title": _property_name(model, "event_horizon", "物件"),
        "return_id": _property_name(model, "event_horizon", "回歸編號"),
        "captured_at": _property_name(model, "event_horizon", "入境時間"),
        "state": _property_name(model, "event_horizon", "狀態"),
    }
    radiated_fields = {
        "title": _property_name(model, "hawking_radiation", "輸出"),
        "return_id": _property_name(model, "hawking_radiation", "回歸編號"),
        "delivered_at": _property_name(model, "hawking_radiation", "交付時間"),
        "acknowledged": _property_name(model, "hawking_radiation", "接收確認"),
    }

    captured = [
        flatten_page(page, captured_fields)
        for page in query_database(client, databases["event_horizon"])
    ]
    radiated = [
        flatten_page(page, radiated_fields)
        for page in query_database(client, databases["hawking_radiation"])
    ]

    return {
        "model_title": model.title,
        "model_version": model.version,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "captured": captured,
        "radiated": radiated,
    }
