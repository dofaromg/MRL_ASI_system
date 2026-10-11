# origin_signature: MrLiouWord
"""Tests for the source-conserving MRL genesis graph."""

from dataclasses import replace

import pytest

from mrl_blackhole import (
    GenesisStructure,
    LogicRelation,
    MirrorConstraint,
    ParallelWorld,
    ParticleSpec,
    audit_genesis_structure,
)

SOURCE = b"-+"
SOURCE_NAME = "duality.pcode"
CAPTURED_AT = "2026-10-11T18:00:00Z"


def _specs(include_world=False):
    atoms = [
        ParticleSpec("negative", 0, 1, ("symbolic", "polarity"), "sign", "negative"),
        ParticleSpec("positive", 1, 2, ("symbolic", "polarity"), "sign", "positive"),
    ]
    if include_world:
        atoms.extend(
            [
                ParticleSpec(
                    "negative-twin", 0, 1, ("symbolic", "polarity"), "sign", "negative", "mirror"
                ),
                ParticleSpec(
                    "positive-twin", 1, 2, ("symbolic", "polarity"), "sign", "positive", "mirror"
                ),
            ]
        )
    return atoms


def _structure(**overrides):
    options = {
        "source_name": SOURCE_NAME,
        "captured_at": CAPTURED_AT,
        "atomizer": "test-byte-atomizer-v1",
        "particles": _specs(),
        "mirrors": [MirrorConstraint("balance", "negative", "positive")],
    }
    options.update(overrides)
    return GenesisStructure.from_atomization(SOURCE, **options)


@pytest.mark.unit
def test_genesis_structure_conserves_source_and_symbolic_mirror():
    structure = _structure()

    assert structure.source_sha256
    assert structure.mirrors[0].invariant == "-1 + 1 = 0"
    assert structure.mirrors[0].boundary == "∞"
    assert audit_genesis_structure(structure, SOURCE).conserved


@pytest.mark.unit
def test_atomizer_must_cover_source_without_gaps_or_overlaps():
    with pytest.raises(ValueError, match="source_coverage_gap_or_overlap"):
        _structure(
            particles=[
                ParticleSpec("negative", 0, 1, ("polarity",), "sign", "negative"),
                ParticleSpec("positive", 2, 2, ("polarity",), "sign", "positive"),
            ],
            mirrors=(),
        )


@pytest.mark.unit
def test_particle_content_and_source_fingerprints_are_audited():
    structure = _structure()
    altered_particle = replace(structure.particles[0], fragment_sha256="0" * 64)
    altered = replace(
        structure,
        source_sha256="1" * 64,
        particles=(altered_particle,) + structure.particles[1:],
    )

    report = audit_genesis_structure(altered, SOURCE)
    assert not report.conserved
    assert "source_fingerprint_mismatch" in report.violations
    assert "particle_fingerprint_mismatch" in report.violations


@pytest.mark.unit
def test_logic_relations_must_resolve_particle_ids():
    with pytest.raises(ValueError, match="unresolved_relation"):
        _structure(
            relations=[LogicRelation("edge-1", "negative", "balances", "missing")],
        )


@pytest.mark.unit
def test_mirror_requires_negative_and_positive_symbolic_polarities():
    with pytest.raises(ValueError, match="mirror_polarity_mismatch"):
        _structure(
            particles=[
                ParticleSpec("negative", 0, 1, ("polarity",), "sign", "neutral"),
                ParticleSpec("positive", 1, 2, ("polarity",), "sign", "positive"),
            ],
        )


@pytest.mark.unit
def test_parallel_world_projection_maps_base_atoms_to_world_counterparts():
    world = ParallelWorld(
        "mirror",
        "Mirror world",
        (("negative", "negative-twin"), ("positive", "positive-twin")),
    )
    structure = _structure(particles=_specs(include_world=True), parallel_worlds=[world])

    assert audit_genesis_structure(structure, SOURCE).conserved


@pytest.mark.unit
def test_parallel_world_projection_must_map_every_particle():
    world = ParallelWorld(
        "mirror",
        "Mirror world",
        (("negative", "negative-twin"),),
    )
    with pytest.raises(ValueError, match="incomplete_world_correspondence"):
        _structure(particles=_specs(include_world=True), parallel_worlds=[world])


@pytest.mark.unit
def test_translation_return_id_is_bound_to_the_genesis_source():
    structure = _structure()
    altered = replace(structure, source_return_id="RID-forged")

    assert "return_id_mismatch" in audit_genesis_structure(altered, SOURCE).violations
