# origin_signature: MrLiouWord
"""Tests for the particle translation lifecycle."""

from dataclasses import replace

import pytest

from mrl_blackhole import (
    BlackHoleTranslationPipeline,
    audit_translation,
    make_translation_return_id,
)


def _pipeline():
    return BlackHoleTranslationPipeline(
        normalizer=lambda source: source.strip().split(),
        parser=lambda tokens: {"nodes": [{"particle": token} for token in tokens]},
        generator=lambda tree, target: f"{target}:{len(tree['nodes'])}",
    )


@pytest.mark.unit
def test_translation_uses_all_five_layers_and_preserves_source():
    source = "  ⋄fx.unit.point → result  "
    result = _pipeline().translate(
        source,
        source_name="example.pcode",
        captured_at="2026-10-11T18:00:00Z",
        target="python",
    )

    assert result.source == source
    assert result.output == "python:3"
    assert [stage.layer for stage in result.trace] == [
        "event_horizon",
        "accretion_disk",
        "singularity",
        "hawking_radiation",
        "return_ledger",
    ]
    assert {stage.return_id for stage in result.trace} == {result.return_id}
    assert audit_translation(result).conserved


@pytest.mark.unit
def test_return_id_is_deterministic_and_content_sensitive():
    captured_at = "2026-10-11T18:00:00Z"
    first = make_translation_return_id("example.pcode", captured_at, "particle A")

    assert first == make_translation_return_id("example.pcode", captured_at, "particle A")
    assert first != make_translation_return_id("example.pcode", captured_at, "particle B")


@pytest.mark.unit
def test_audit_detects_missing_stages_and_broken_lineage():
    result = _pipeline().translate(
        "particle",
        source_name="example.pcode",
        captured_at="2026-10-11T18:00:00Z",
        target="python",
    )
    incomplete = replace(result, trace=result.trace[:-1])
    broken = replace(
        result,
        trace=(replace(result.trace[2], return_id="RID-other"),) + result.trace[1:],
    )

    assert "incomplete_trace" in audit_translation(incomplete).violations
    broken_audit = audit_translation(broken)
    assert "return_id_mismatch" in broken_audit.violations
    assert "stage_order_mismatch" in broken_audit.violations


@pytest.mark.unit
def test_audit_rejects_a_return_id_not_derived_from_the_source():
    result = _pipeline().translate(
        "particle",
        source_name="example.pcode",
        captured_at="2026-10-11T18:00:00Z",
        target="python",
    )
    altered = replace(
        result,
        return_id="RID-forged",
        trace=tuple(replace(stage, return_id="RID-forged") for stage in result.trace),
    )

    assert audit_translation(altered).violations == ("return_id_mismatch",)


@pytest.mark.unit
def test_pipeline_rejects_non_serializable_intermediate_values():
    pipeline = BlackHoleTranslationPipeline(
        normalizer=lambda source: object(),
        parser=lambda normalized: normalized,
        generator=lambda tree, target: target,
    )

    with pytest.raises(TypeError, match="Unsupported intermediate value"):
        pipeline.translate(
            "particle",
            source_name="example.pcode",
            captured_at="2026-10-11T18:00:00Z",
            target="python",
        )


@pytest.mark.unit
def test_pipeline_requires_a_text_or_binary_generated_output():
    pipeline = BlackHoleTranslationPipeline(
        normalizer=lambda source: source,
        parser=lambda normalized: normalized,
        generator=lambda tree, target: {"generated": target},
    )

    with pytest.raises(TypeError, match="generator must return str or bytes"):
        pipeline.translate(
            "particle",
            source_name="example.pcode",
            captured_at="2026-10-11T18:00:00Z",
            target="python",
        )
