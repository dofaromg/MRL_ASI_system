# origin_signature: MrLiouWord
"""
Build the MRL black hole inside a Notion workspace
在 Notion 工作區中建構 MRL 黑洞模型

The builder is deliberately two-phase: databases are created first without
their relation properties, then the relations are patched in once every
database id is known. Every run writes a manifest so a second run reuses the
structure instead of creating a duplicate black hole.

建構器刻意分成兩階段：先建立不含關聯屬性的資料庫，等所有資料庫 id 都拿到之後
再補上關聯。每次執行都會寫出 manifest，讓第二次執行沿用既有結構，
而不是再長出一顆新的黑洞。
"""

from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from .model import BlackHoleModel, LayerSpec, default_model

NOTION_API_BASE = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"
DEFAULT_MANIFEST_NAME = "blackhole_manifest.json"


class NotionAPIClient:
    """Minimal Notion REST client / 最小化的 Notion REST 客戶端"""

    def __init__(self, token: Optional[str] = None, timeout: int = 15) -> None:
        self.token = token or os.environ.get("NOTION_TOKEN")
        self.timeout = timeout

    def _headers(self) -> Dict[str, str]:
        if not self.token:
            raise RuntimeError("NOTION_TOKEN is required to build the black hole in Notion")
        return {
            "Authorization": f"Bearer {self.token}",
            "Notion-Version": NOTION_VERSION,
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        import requests  # imported lazily so planning works without the dependency

        response = requests.request(
            method,
            f"{NOTION_API_BASE}{path}",
            headers=self._headers(),
            json=payload,
            timeout=self.timeout,
        )
        if response.status_code >= 400:
            raise RuntimeError(f"Notion API {method} {path} failed ({response.status_code}): {response.text}")
        return response.json()


def _text(content: str) -> List[Dict[str, Any]]:
    return [{"type": "text", "text": {"content": content}}]


class BlackHoleBuilder:
    """Create or repair the black hole structure / 建立或修復黑洞結構"""

    def __init__(
        self,
        model: Optional[BlackHoleModel] = None,
        client: Optional[NotionAPIClient] = None,
        manifest_path: Optional[Path] = None,
    ) -> None:
        self.model = model or default_model()
        self.client = client
        self.manifest_path = Path(manifest_path) if manifest_path else None

    # ------------------------------------------------------------------
    # Manifest / 結構清單
    # ------------------------------------------------------------------
    def load_manifest(self) -> Dict[str, Any]:
        if self.manifest_path and self.manifest_path.exists():
            return json.loads(self.manifest_path.read_text(encoding="utf-8"))
        return {}

    def save_manifest(self, manifest: Dict[str, Any]) -> Optional[Path]:
        if not self.manifest_path:
            return None
        self.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        self.manifest_path.write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )
        return self.manifest_path

    # ------------------------------------------------------------------
    # Payload builders / Payload 組裝
    # ------------------------------------------------------------------
    def root_page_payload(self, parent_page_id: str) -> Dict[str, Any]:
        return {
            "parent": {"type": "page_id", "page_id": parent_page_id},
            "icon": {"type": "emoji", "emoji": "🕳️"},
            "properties": {"title": {"title": _text(self.model.title)}},
            "children": [
                {
                    "object": "block",
                    "type": "heading_2",
                    "heading_2": {"rich_text": _text("閉合定律 / Closure Law")},
                },
                {
                    "object": "block",
                    "type": "callout",
                    "callout": {
                        "icon": {"type": "emoji", "emoji": "🔁"},
                        "rich_text": _text("怎麼過去，就怎麼回來 — How you go is how you come back"),
                    },
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {"rich_text": _text(self.model.description)},
                },
                {
                    "object": "block",
                    "type": "paragraph",
                    "paragraph": {
                        "rich_text": _text(
                            f"model version {self.model.version} · 任何越過事件視界的物件都必須帶著回歸編號離開。"
                        )
                    },
                },
            ],
        }

    def database_payload(
        self, layer: LayerSpec, root_page_id: str, database_ids: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        resolver = (database_ids or {}).get
        return {
            "parent": {"type": "page_id", "page_id": root_page_id},
            "icon": {"type": "emoji", "emoji": layer.icon},
            "title": _text(layer.title),
            "description": _text(layer.purpose),
            "properties": layer.to_notion_schema(resolver),
        }

    def relation_patch_payload(self, layer: LayerSpec, database_ids: Dict[str, str]) -> Dict[str, Any]:
        properties: Dict[str, Any] = {}
        for prop in layer.relation_properties():
            schema = prop.to_notion_schema(database_ids.get)
            if schema is not None:
                properties[prop.name] = schema
        return {"properties": properties}

    # ------------------------------------------------------------------
    # Planning / 計畫
    # ------------------------------------------------------------------
    def plan(self, parent_page_id: str) -> Dict[str, Any]:
        """
        Describe every API call without touching the network.
        在不呼叫網路的情況下，描述所有即將送出的 API 請求。
        """
        manifest = self.load_manifest()
        known_ids: Dict[str, str] = dict(manifest.get("databases", {}))
        root_page_id = manifest.get("root_page_id")

        operations: List[Dict[str, Any]] = []
        if root_page_id:
            operations.append({"step": "reuse_root_page", "page_id": root_page_id})
        else:
            operations.append(
                {
                    "step": "create_root_page",
                    "method": "POST",
                    "path": "/pages",
                    "payload": self.root_page_payload(parent_page_id),
                }
            )

        placeholder_ids = dict(known_ids)
        for layer in self.model.layers:
            if layer.key in known_ids:
                operations.append(
                    {"step": "reuse_database", "layer": layer.key, "database_id": known_ids[layer.key]}
                )
                continue
            placeholder_ids.setdefault(layer.key, f"<{layer.key}_database_id>")
            operations.append(
                {
                    "step": "create_database",
                    "layer": layer.key,
                    "method": "POST",
                    "path": "/databases",
                    "payload": self.database_payload(layer, root_page_id or "<root_page_id>"),
                }
            )

        for layer in self.model.layers:
            if not layer.relation_properties():
                continue
            operations.append(
                {
                    "step": "patch_relations",
                    "layer": layer.key,
                    "method": "PATCH",
                    "path": f"/databases/{placeholder_ids.get(layer.key, '<' + layer.key + '_database_id>')}",
                    "payload": self.relation_patch_payload(layer, placeholder_ids),
                }
            )

        return {
            "model": self.model.to_dict(),
            "parent_page_id": parent_page_id,
            "operations": operations,
        }

    # ------------------------------------------------------------------
    # Execution / 執行
    # ------------------------------------------------------------------
    def build(self, parent_page_id: str) -> Dict[str, Any]:
        """
        Create anything that is missing and return the manifest.
        建立所有缺少的部分，並回傳結構清單。
        """
        if self.client is None:
            raise RuntimeError("A Notion client is required to build; use plan() for a dry run")

        manifest = self.load_manifest()
        database_ids: Dict[str, str] = dict(manifest.get("databases", {}))
        created: List[str] = []

        root_page_id = manifest.get("root_page_id")
        if not root_page_id:
            page = self.client.request("POST", "/pages", self.root_page_payload(parent_page_id))
            root_page_id = page["id"]
            created.append("root_page")

        for layer in self.model.layers:
            if layer.key in database_ids:
                continue
            database = self.client.request(
                "POST", "/databases", self.database_payload(layer, root_page_id, database_ids)
            )
            database_ids[layer.key] = database["id"]
            created.append(layer.key)

        for layer in self.model.layers:
            payload = self.relation_patch_payload(layer, database_ids)
            if not payload["properties"]:
                continue
            self.client.request("PATCH", f"/databases/{database_ids[layer.key]}", payload)

        manifest = {
            "model_title": self.model.title,
            "model_version": self.model.version,
            "parent_page_id": parent_page_id,
            "root_page_id": root_page_id,
            "databases": database_ids,
            "created": created,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        saved_path = self.save_manifest(manifest)
        if saved_path:
            manifest["manifest_path"] = str(saved_path)
        return manifest
