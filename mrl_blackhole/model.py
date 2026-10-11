# origin_signature: MrLiouWord
"""
MRL Black Hole Model - structure definition
MRL 黑洞模型 - 結構定義

The model describes a Notion workspace that behaves like a black hole for
inbound material (everything falls in and nothing is lost) while guaranteeing
the MrLiouWord closure law: whatever crosses the event horizon must come back
out as Hawking radiation.

本模型描述一個像黑洞一樣的 Notion 工作區：所有丟進來的東西都會被吸入並保存，
同時遵守 MrLiouWord 閉合定律 ——「怎麼過去，就怎麼回來」，
任何越過事件視界的物件，最後都必須以霍金輻射的形式輸出回到擁有者手上。
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

MODEL_TITLE = "MRL 黑洞模型 / MRL Black Hole Model"
MODEL_VERSION = "1.0.0"
ORIGIN_SIGNATURE = "MrLiouWord"

# Return IDs are the thread that ties an inbound object to its outbound copy.
# 回歸編號是把「入境物件」與「輸出成果」綁在一起的那條線。
RETURN_ID_PREFIX = "RID"


@dataclass(frozen=True)
class PropertySpec:
    """A single Notion database property / 單一 Notion 資料庫屬性"""

    name: str
    type: str
    options: List[str] = field(default_factory=list)
    relation_to: Optional[str] = None
    number_format: str = "number"

    def to_notion_schema(
        self, resolve_database_id: Optional[Callable[[str], Optional[str]]] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Convert to a Notion property schema payload.
        轉換為 Notion 屬性結構 payload。

        Relation properties return ``None`` when the target database id is not
        resolvable yet, which lets the builder create databases first and patch
        the relations afterwards.
        關聯屬性在目標資料庫尚未建立時回傳 ``None``，
        讓建構器可以先建立資料庫、之後再補上關聯。
        """
        if self.type == "relation":
            if resolve_database_id is None or self.relation_to is None:
                return None
            database_id = resolve_database_id(self.relation_to)
            if not database_id:
                return None
            return {
                "relation": {
                    "database_id": database_id,
                    "type": "dual_property",
                    "dual_property": {},
                }
            }
        if self.type in ("select", "multi_select"):
            return {self.type: {"options": [{"name": option} for option in self.options]}}
        if self.type == "number":
            return {"number": {"format": self.number_format}}
        return {self.type: {}}


@dataclass(frozen=True)
class LayerSpec:
    """One shell of the black hole, materialised as a Notion database."""

    key: str
    title: str
    icon: str
    purpose: str
    properties: List[PropertySpec]

    def title_property(self) -> PropertySpec:
        for prop in self.properties:
            if prop.type == "title":
                return prop
        raise ValueError(f"Layer '{self.key}' has no title property")

    def relation_properties(self) -> List[PropertySpec]:
        return [prop for prop in self.properties if prop.type == "relation"]

    def to_notion_schema(
        self, resolve_database_id: Optional[Callable[[str], Optional[str]]] = None
    ) -> Dict[str, Any]:
        schema: Dict[str, Any] = {}
        for prop in self.properties:
            payload = prop.to_notion_schema(resolve_database_id)
            if payload is not None:
                schema[prop.name] = payload
        return schema


@dataclass(frozen=True)
class BlackHoleModel:
    """The whole MRL black hole / 完整的 MRL 黑洞模型"""

    title: str
    version: str
    description: str
    layers: List[LayerSpec]

    def layer(self, key: str) -> LayerSpec:
        for layer in self.layers:
            if layer.key == key:
                return layer
        raise KeyError(f"Unknown layer: {key}")

    def layer_keys(self) -> List[str]:
        return [layer.key for layer in self.layers]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "title": self.title,
            "version": self.version,
            "origin_signature": ORIGIN_SIGNATURE,
            "description": self.description,
            "layers": [
                {
                    "key": layer.key,
                    "title": layer.title,
                    "icon": layer.icon,
                    "purpose": layer.purpose,
                    "properties": [
                        {
                            "name": prop.name,
                            "type": prop.type,
                            "options": list(prop.options),
                            "relation_to": prop.relation_to,
                        }
                        for prop in layer.properties
                    ],
                }
                for layer in self.layers
            ],
        }


EVENT_HORIZON = LayerSpec(
    key="event_horizon",
    title="L1 事件視界 Event Horizon",
    icon="🌑",
    purpose="捕獲任何進入的物件，並立即發出回歸編號 / Capture anything inbound and issue a return id",
    properties=[
        PropertySpec("物件 Object", "title"),
        PropertySpec("回歸編號 Return ID", "rich_text"),
        PropertySpec(
            "來源 Source",
            "select",
            options=["對話 Chat", "檔案 File", "連結 Link", "語音 Voice", "程式碼 Code", "其他 Other"],
        ),
        PropertySpec("原始載體 Carrier", "rich_text"),
        PropertySpec("入境時間 Captured At", "date"),
        PropertySpec("質量 Mass", "number"),
        PropertySpec(
            "狀態 State",
            "select",
            options=["已捕獲 Captured", "已吸積 Accreted", "已壓縮 Compressed", "已輻射 Radiated"],
        ),
        PropertySpec("原始連結 Source URL", "url"),
        PropertySpec("不可丟失 Irreplaceable", "checkbox"),
    ],
)

ACCRETION_DISK = LayerSpec(
    key="accretion_disk",
    title="L2 吸積盤 Accretion Disk",
    icon="🌀",
    purpose="把捕獲的物件分類、降熵、排出處理順序 / Classify captured objects and lower their entropy",
    properties=[
        PropertySpec("粒子 Particle", "title"),
        PropertySpec("來源物件 Captured Object", "relation", relation_to="event_horizon"),
        PropertySpec(
            "分類 Category",
            "multi_select",
            options=["結構 Structure", "敘事 Narrative", "資產 Asset", "決策 Decision", "雜訊 Noise"],
        ),
        PropertySpec("熵 Entropy", "number"),
        PropertySpec(
            "處理狀態 Processing",
            "select",
            options=["待處理 Queued", "處理中 Spiralling", "已降熵 Reduced", "退回 Ejected"],
        ),
        PropertySpec("負責人格 Persona", "rich_text"),
        PropertySpec("處理筆記 Notes", "rich_text"),
    ],
)

SINGULARITY = LayerSpec(
    key="singularity",
    title="L3 奇點 Singularity",
    icon="⚫",
    purpose="把降熵後的粒子壓縮成可複用的本體知識 / Compress reduced particles into reusable core knowledge",
    properties=[
        PropertySpec("核心 Core", "title"),
        PropertySpec("來源粒子 Source Particle", "relation", relation_to="accretion_disk"),
        PropertySpec("壓縮比 Compression Ratio", "number", number_format="percent"),
        PropertySpec("版本 Version", "rich_text"),
        PropertySpec("內容雜湊 Content Hash", "rich_text"),
        PropertySpec("可逆 Reversible", "checkbox"),
        PropertySpec(
            "風險 Risk",
            "select",
            options=["低 Low", "中 Medium", "高 High", "不可逆 Irreversible"],
        ),
    ],
)

HAWKING_RADIATION = LayerSpec(
    key="hawking_radiation",
    title="L4 霍金輻射 Hawking Radiation",
    icon="✨",
    purpose="把壓縮後的本體輻射回擁有者手上 / Radiate compressed cores back to the owner",
    properties=[
        PropertySpec("輸出 Output", "title"),
        PropertySpec("來源核心 Source Core", "relation", relation_to="singularity"),
        PropertySpec("回歸編號 Return ID", "rich_text"),
        PropertySpec(
            "輸出形式 Form",
            "select",
            options=["封包 Package", "文件 Document", "程式碼 Code", "圖像 Image", "API", "其他 Other"],
        ),
        PropertySpec("交付時間 Delivered At", "date"),
        PropertySpec("交付連結 Delivery URL", "url"),
        PropertySpec("接收確認 Acknowledged", "checkbox"),
    ],
)

RETURN_LEDGER = LayerSpec(
    key="return_ledger",
    title="L5 回歸帳本 Return Ledger",
    icon="🔁",
    purpose="稽核守恆：每個入境物件都必須有對應輸出 / Audit conservation: every inbound object must have an output",
    properties=[
        PropertySpec("回歸編號 Return ID", "title"),
        PropertySpec("入境物件 Inbound", "relation", relation_to="event_horizon"),
        PropertySpec("輸出成果 Outbound", "relation", relation_to="hawking_radiation"),
        PropertySpec("往返時間 Round Trip Hours", "number"),
        PropertySpec("守恆 Conserved", "checkbox"),
        PropertySpec(
            "稽核狀態 Audit",
            "select",
            options=["待回歸 Pending", "已回歸 Returned", "逾期 Overdue", "遺失 Lost"],
        ),
        PropertySpec("證據 Evidence", "url"),
    ],
)


def default_model() -> BlackHoleModel:
    """Return the canonical MRL black hole model / 回傳標準版 MRL 黑洞模型"""
    return BlackHoleModel(
        title=MODEL_TITLE,
        version=MODEL_VERSION,
        description=(
            "黑洞吸入一切，但在 MRL 模型裡沒有任何東西會消失："
            "事件視界捕獲 → 吸積盤降熵 → 奇點壓縮 → 霍金輻射輸出 → 回歸帳本稽核。"
            " A black hole that swallows everything yet loses nothing: "
            "capture, reduce, compress, radiate, audit."
        ),
        layers=[EVENT_HORIZON, ACCRETION_DISK, SINGULARITY, HAWKING_RADIATION, RETURN_LEDGER],
    )


def make_return_id(source: str, title: str, captured_at: str) -> str:
    """
    Build a deterministic return id so the same object never gets two threads.
    產生可重現的回歸編號，確保同一個物件不會拿到兩條回歸線。
    """
    payload = f"{source}|{title}|{captured_at}".encode("utf-8")
    digest = hashlib.sha256(payload).hexdigest()[:12]
    return f"{RETURN_ID_PREFIX}-{digest}"
