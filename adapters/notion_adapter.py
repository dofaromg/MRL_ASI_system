from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, List


class NotionAdapter:
    def __init__(self, data_dir: Path, token: str | None = None) -> None:
        self.data_dir = data_dir
        self.token = token or os.environ.get("NOTION_TOKEN")

    def sync_entries(self, entries: List[Dict[str, Any]], config: Dict[str, Any]) -> Path:
        """
        Closed-loop sync: stores the payload locally only.
        閉環同步：僅將資料封存至本地，不向外部 Notion API 發出請求。
        """
        export_path = self.data_dir / "notion_export.json"
        payload = {"config": config, "entries": entries}
        export_path.write_text(json.dumps(payload, indent=2, ensure_ascii=False))
        return export_path
