# origin_signature: MrLiouWord
"""
Conservation audit for the MRL black hole
MRL 黑洞模型的守恆稽核

A real black hole destroys information. The MRL model is only allowed to look
like one: every object that crossed the event horizon must leave again through
Hawking radiation, carrying the same return id it entered with. This module
proves (or disproves) that property over an exported snapshot.

真的黑洞會摧毀資訊，MRL 模型只准「長得像」黑洞：
每個越過事件視界的物件，都必須帶著同一個回歸編號，以霍金輻射的形式離開。
這個模組就是用匯出的快照來證明（或戳破）這件事。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_OVERDUE_HOURS = 72


@dataclass
class Violation:
    """One broken promise / 一筆違反承諾的紀錄"""

    kind: str
    return_id: Optional[str]
    title: str
    detail: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "return_id": self.return_id,
            "title": self.title,
            "detail": self.detail,
        }


@dataclass
class ConservationReport:
    """Result of the audit / 稽核結果"""

    captured: int = 0
    radiated: int = 0
    returned: int = 0
    pending: int = 0
    violations: List[Violation] = field(default_factory=list)
    warnings: List[Violation] = field(default_factory=list)

    @property
    def conserved(self) -> bool:
        return not self.violations

    def to_dict(self) -> Dict[str, Any]:
        return {
            "conserved": self.conserved,
            "captured": self.captured,
            "radiated": self.radiated,
            "returned": self.returned,
            "pending": self.pending,
            "violations": [violation.to_dict() for violation in self.violations],
            "warnings": [warning.to_dict() for warning in self.warnings],
        }

    def summary(self) -> str:
        verdict = "守恆 CONSERVED" if self.conserved else "破損 BROKEN"
        return (
            f"[{verdict}] 捕獲 {self.captured} / 輻射 {self.radiated} / 回歸 {self.returned} / "
            f"待回歸 {self.pending} / 違規 {len(self.violations)}"
        )


def _parse_time(value: Optional[str]) -> Optional[datetime]:
    if not value:
        return None
    text = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(text)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=timezone.utc)
    return parsed


def round_trip_hours(captured_at: Optional[str], delivered_at: Optional[str]) -> Optional[float]:
    """Hours between capture and delivery / 從捕獲到交付之間的小時數"""
    start = _parse_time(captured_at)
    end = _parse_time(delivered_at)
    if start is None or end is None:
        return None
    return round((end - start).total_seconds() / 3600.0, 2)


def audit_conservation(
    captured: Iterable[Dict[str, Any]],
    radiated: Iterable[Dict[str, Any]],
    now: Optional[datetime] = None,
    overdue_hours: int = DEFAULT_OVERDUE_HOURS,
) -> ConservationReport:
    """
    Check that every captured object came back out.
    檢查每個被捕獲的物件是否都回來了。
    """
    now = now or datetime.now(timezone.utc)
    report = ConservationReport()

    outputs_by_return_id: Dict[str, List[Dict[str, Any]]] = {}
    for item in radiated:
        report.radiated += 1
        return_id = (item.get("return_id") or "").strip()
        if not return_id:
            report.violations.append(
                Violation(
                    kind="untraceable_output",
                    return_id=None,
                    title=item.get("title", ""),
                    detail="輸出沒有回歸編號，無法證明它屬於哪個入境物件",
                )
            )
            continue
        outputs_by_return_id.setdefault(return_id, []).append(item)

    seen_return_ids: Dict[str, str] = {}
    for item in captured:
        report.captured += 1
        title = item.get("title", "")
        return_id = (item.get("return_id") or "").strip()

        if not return_id:
            report.violations.append(
                Violation(
                    kind="missing_return_id",
                    return_id=None,
                    title=title,
                    detail="物件已越過事件視界卻沒有回歸編號，等於被黑洞吞掉",
                )
            )
            continue

        if return_id in seen_return_ids:
            report.violations.append(
                Violation(
                    kind="duplicate_return_id",
                    return_id=return_id,
                    title=title,
                    detail=f"回歸編號與「{seen_return_ids[return_id]}」重複，回歸線會互相覆蓋",
                )
            )
            continue
        seen_return_ids[return_id] = title

        outputs = outputs_by_return_id.pop(return_id, [])
        if outputs:
            report.returned += 1
            for output in outputs:
                if not output.get("acknowledged", False):
                    report.warnings.append(
                        Violation(
                            kind="unacknowledged_output",
                            return_id=return_id,
                            title=output.get("title", title),
                            detail="已輻射但擁有者尚未確認收到",
                        )
                    )
            continue

        waited = round_trip_hours(item.get("captured_at"), now.isoformat())
        if waited is not None and waited > overdue_hours:
            report.violations.append(
                Violation(
                    kind="swallowed",
                    return_id=return_id,
                    title=title,
                    detail=f"已捕獲 {waited} 小時仍無輸出，超過 {overdue_hours} 小時的回歸上限",
                )
            )
        else:
            report.pending += 1

    for return_id, outputs in outputs_by_return_id.items():
        for output in outputs:
            report.violations.append(
                Violation(
                    kind="orphan_output",
                    return_id=return_id,
                    title=output.get("title", ""),
                    detail="輸出找不到對應的入境物件，來源無法追溯",
                )
            )

    return report
