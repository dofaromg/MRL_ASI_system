# origin_signature: MrLiouWord
"""Particle translation lifecycle on the MRL black-hole model."""

from __future__ import annotations

import base64
import hashlib
import json
import math
from collections.abc import Mapping
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
from typing import Any, Callable, Tuple, Union

from .model import make_return_id

Source = Union[str, bytes]
LayerKey = str

TRANSLATION_LAYERS: Tuple[LayerKey, ...] = (
    "event_horizon",
    "accretion_disk",
    "singularity",
    "hawking_radiation",
    "return_ledger",
)


def _json_value(value: Any) -> Any:
    """Convert supported intermediate values into stable JSON-compatible data."""
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Enum):
        return _json_value(value.value)
    if isinstance(value, bytes):
        return {"$bytes_base64": base64.b64encode(value).decode("ascii")}
    if isinstance(value, Mapping):
        if not all(isinstance(key, str) for key in value):
            raise TypeError("Intermediate mapping keys must be strings")
        return {key: _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    if value is None or isinstance(value, (str, int, bool)):
        return value
    if isinstance(value, float) and math.isfinite(value):
        return value
    raise TypeError(f"Unsupported intermediate value: {type(value).__name__}")


def _fingerprint(value: Any) -> str:
    if isinstance(value, bytes):
        content = value
    elif isinstance(value, str):
        content = value.encode("utf-8")
    else:
        content = json.dumps(
            _json_value(value),
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("utf-8")
    return hashlib.sha256(content).hexdigest()


def make_translation_return_id(source_name: str, captured_at: str, source: Source) -> str:
    """Create a stable return ID tied to the exact source content."""
    source_hash = _fingerprint(source)
    return make_return_id(
        "粒子程式 Particle Program",
        f"{source_name}|{source_hash}",
        captured_at,
    )


@dataclass(frozen=True)
class StageTrace:
    """Checksummed hand-off between two black-hole layers."""

    layer: LayerKey
    return_id: str
    input_sha256: str
    output_sha256: str


@dataclass(frozen=True)
class TranslationResult:
    """A loss-aware translation result retaining its original source."""

    return_id: str
    source_name: str
    captured_at: str
    source: Source
    normalized: Any
    syntax_tree: Any
    output: Source
    target: str
    trace: Tuple[StageTrace, ...]


@dataclass(frozen=True)
class TranslationAudit:
    """Conservation check for one translation / 單次轉譯的守恆檢查."""

    conserved: bool
    violations: Tuple[str, ...] = ()


Normalizer = Callable[[Source], Any]
Parser = Callable[[Any], Any]
Generator = Callable[[Any, str], Source]


class BlackHoleTranslationPipeline:
    """Run injected particle-language stages through the five black-hole layers.

    The model owns capture, provenance, stage ordering, and conservation checks.
    A language-specific normalizer, parser, and generator remain pluggable.
    """

    def __init__(
        self,
        normalizer: Normalizer,
        parser: Parser,
        generator: Generator,
    ) -> None:
        self.normalizer = normalizer
        self.parser = parser
        self.generator = generator

    def translate(
        self,
        source: Source,
        *,
        source_name: str,
        captured_at: str,
        target: str,
    ) -> TranslationResult:
        if not isinstance(source, (str, bytes)):
            raise TypeError("source must be str or bytes")
        if not source_name.strip():
            raise ValueError("source_name must not be empty")
        if not captured_at.strip():
            raise ValueError("captured_at must not be empty")
        if not target.strip():
            raise ValueError("target must not be empty")

        source_hash = _fingerprint(source)
        return_id = make_translation_return_id(source_name, captured_at, source)
        normalized = self.normalizer(source)
        normalized_hash = _fingerprint(normalized)
        syntax_tree = self.parser(normalized)
        syntax_tree_hash = _fingerprint(syntax_tree)
        output = self.generator(syntax_tree, target)
        if not isinstance(output, (str, bytes)):
            raise TypeError("generator must return str or bytes")
        output_hash = _fingerprint(output)

        result = TranslationResult(
            return_id=return_id,
            source_name=source_name,
            captured_at=captured_at,
            source=source,
            normalized=normalized,
            syntax_tree=syntax_tree,
            output=output,
            target=target,
            trace=(
                StageTrace("event_horizon", return_id, source_hash, source_hash),
                StageTrace("accretion_disk", return_id, source_hash, normalized_hash),
                StageTrace("singularity", return_id, normalized_hash, syntax_tree_hash),
                StageTrace("hawking_radiation", return_id, syntax_tree_hash, output_hash),
                StageTrace("return_ledger", return_id, output_hash, output_hash),
            ),
        )
        audit = audit_translation(result)
        if not audit.conserved:
            raise RuntimeError(f"Translation conservation check failed: {audit.violations}")
        return result


def audit_translation(result: TranslationResult) -> TranslationAudit:
    """Verify layer order, return-ID continuity, and payload fingerprints."""
    violations = []
    if len(result.trace) != len(TRANSLATION_LAYERS):
        violations.append("incomplete_trace")
    if result.return_id != make_translation_return_id(
        result.source_name,
        result.captured_at,
        result.source,
    ):
        violations.append("return_id_mismatch")

    source_hash = _fingerprint(result.source)
    normalized_hash = _fingerprint(result.normalized)
    syntax_tree_hash = _fingerprint(result.syntax_tree)
    output_hash = _fingerprint(result.output)
    expected_pairs = (
        (source_hash, source_hash),
        (source_hash, normalized_hash),
        (normalized_hash, syntax_tree_hash),
        (syntax_tree_hash, output_hash),
        (output_hash, output_hash),
    )
    for index, trace in enumerate(result.trace):
        if index >= len(TRANSLATION_LAYERS):
            violations.append("unexpected_stage")
            continue
        if trace.layer != TRANSLATION_LAYERS[index]:
            violations.append("stage_order_mismatch")
        if trace.return_id != result.return_id:
            violations.append("return_id_mismatch")
        expected_input, expected_output = expected_pairs[index]
        if trace.input_sha256 != expected_input:
            violations.append("stage_input_mismatch")
        if trace.output_sha256 != expected_output:
            violations.append("stage_output_mismatch")
    return TranslationAudit(not violations, tuple(violations))
