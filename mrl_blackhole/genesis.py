# origin_signature: MrLiouWord
"""Extensible, source-conserving particle graph for the MRL genesis model."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from typing import Iterable, Tuple, Union

from .translation import make_translation_return_id

Source = Union[str, bytes]
POLARITIES = frozenset({"negative", "neutral", "positive"})
BASE_WORLD = "base"


def _source_bytes(source: Source) -> bytes:
    if isinstance(source, bytes):
        return source
    if isinstance(source, str):
        return source.encode("utf-8")
    raise TypeError("source must be str or bytes")


@dataclass(frozen=True)
class ParticleSpec:
    """Format-defined atomizer output, using half-open source byte offsets."""

    particle_id: str
    start: int
    end: int
    dimensions: Tuple[str, ...]
    unit_type: str
    polarity: str = "neutral"
    world_id: str = BASE_WORLD


@dataclass(frozen=True)
class GenesisParticle:
    """A source-addressable particle in a named logic dimension and world."""

    particle_id: str
    start: int
    end: int
    fragment_sha256: str
    dimensions: Tuple[str, ...]
    unit_type: str
    polarity: str
    world_id: str


@dataclass(frozen=True)
class LogicRelation:
    relation_id: str
    source_particle: str
    predicate: str
    target_particle: str


@dataclass(frozen=True)
class MirrorConstraint:
    """A symbolic mirror rule, not a claim that its notation is physical law."""

    mirror_id: str
    negative_particle: str
    positive_particle: str
    invariant: str = "-1 + 1 = 0"
    boundary: str = "∞"
    symmetry: str = "involution"


@dataclass(frozen=True)
class ParallelWorld:
    """Counterpart mapping from base particles into one modeled world."""

    world_id: str
    label: str
    correspondence: Tuple[Tuple[str, str], ...]


@dataclass(frozen=True)
class GenesisAudit:
    conserved: bool
    violations: Tuple[str, ...] = ()


@dataclass(frozen=True)
class GenesisStructure:
    """Source-complete particle graph with dimensions, relations, and projections."""

    source_return_id: str
    source_name: str
    captured_at: str
    source_sha256: str
    atomizer: str
    particles: Tuple[GenesisParticle, ...]
    relations: Tuple[LogicRelation, ...] = ()
    mirrors: Tuple[MirrorConstraint, ...] = ()
    parallel_worlds: Tuple[ParallelWorld, ...] = ()

    @classmethod
    def from_atomization(
        cls,
        source: Source,
        *,
        source_name: str,
        captured_at: str,
        atomizer: str,
        particles: Iterable[ParticleSpec],
        source_return_id: str = "",
        relations: Iterable[LogicRelation] = (),
        mirrors: Iterable[MirrorConstraint] = (),
        parallel_worlds: Iterable[ParallelWorld] = (),
    ) -> "GenesisStructure":
        if not source_name.strip() or not captured_at.strip() or not atomizer.strip():
            raise ValueError("source_name, captured_at, and atomizer must not be empty")
        source_data = _source_bytes(source)
        materialized = tuple(particles)
        atoms = tuple(
            GenesisParticle(
                particle_id=spec.particle_id,
                start=spec.start,
                end=spec.end,
                fragment_sha256=hashlib.sha256(source_data[spec.start:spec.end]).hexdigest(),
                dimensions=tuple(spec.dimensions),
                unit_type=spec.unit_type,
                polarity=spec.polarity,
                world_id=spec.world_id,
            )
            for spec in materialized
        )
        expected_return_id = make_translation_return_id(source_name, captured_at, source)
        if source_return_id and source_return_id != expected_return_id:
            raise ValueError("source_return_id does not match source lineage")
        structure = cls(
            source_return_id=source_return_id or expected_return_id,
            source_name=source_name,
            captured_at=captured_at,
            source_sha256=hashlib.sha256(source_data).hexdigest(),
            atomizer=atomizer,
            particles=atoms,
            relations=tuple(relations),
            mirrors=tuple(mirrors),
            parallel_worlds=tuple(parallel_worlds),
        )
        audit = audit_genesis_structure(structure, source)
        if not audit.conserved:
            raise ValueError(f"Invalid genesis structure: {audit.violations}")
        return structure


def audit_genesis_structure(structure: GenesisStructure, source: Source) -> GenesisAudit:
    """Check exact source coverage and that all graph references resolve."""
    source_data = _source_bytes(source)
    violations = []
    if not structure.source_return_id.strip():
        violations.append("missing_return_id")
    if not structure.source_name.strip() or not structure.captured_at.strip():
        violations.append("missing_source_lineage")
    if not structure.atomizer.strip():
        violations.append("missing_atomizer")
    if structure.source_sha256 != hashlib.sha256(source_data).hexdigest():
        violations.append("source_fingerprint_mismatch")
    if structure.source_return_id != make_translation_return_id(
        structure.source_name,
        structure.captured_at,
        source,
    ):
        violations.append("return_id_mismatch")

    particle_ids = [particle.particle_id for particle in structure.particles]
    if any(not particle_id.strip() for particle_id in particle_ids):
        violations.append("missing_particle_id")
    if len(set(particle_ids)) != len(particle_ids):
        violations.append("duplicate_particle_id")

    cursor = 0
    base_particles = [
        particle for particle in structure.particles if particle.world_id == BASE_WORLD
    ]
    for particle in sorted(base_particles, key=lambda atom: (atom.start, atom.end)):
        if particle.start != cursor or particle.end <= particle.start or particle.end > len(source_data):
            violations.append("source_coverage_gap_or_overlap")
        cursor = particle.end
    if cursor != len(source_data):
        violations.append("source_coverage_gap_or_overlap")

    for particle in structure.particles:
        if particle.start < 0 or particle.end < particle.start or particle.end > len(source_data):
            fragment = b""
        else:
            fragment = source_data[particle.start:particle.end]
        if particle.fragment_sha256 != hashlib.sha256(fragment).hexdigest():
            violations.append("particle_fingerprint_mismatch")
        if not particle.dimensions or any(not dimension.strip() for dimension in particle.dimensions):
            violations.append("missing_dimension")
        if len(set(particle.dimensions)) != len(particle.dimensions):
            violations.append("duplicate_dimension")
        if not particle.unit_type.strip():
            violations.append("missing_unit_type")
        if particle.polarity not in POLARITIES:
            violations.append("invalid_polarity")
        if not particle.world_id.strip():
            violations.append("missing_world_id")

    known_particles = set(particle_ids)
    relation_ids = [relation.relation_id for relation in structure.relations]
    if len(set(relation_ids)) != len(relation_ids):
        violations.append("duplicate_relation_id")
    for relation in structure.relations:
        if not relation.relation_id.strip() or not relation.predicate.strip():
            violations.append("incomplete_relation")
        if relation.source_particle not in known_particles or relation.target_particle not in known_particles:
            violations.append("unresolved_relation")

    mirror_ids = [mirror.mirror_id for mirror in structure.mirrors]
    if len(set(mirror_ids)) != len(mirror_ids):
        violations.append("duplicate_mirror_id")
    particles_by_id = {particle.particle_id: particle for particle in structure.particles}
    for mirror in structure.mirrors:
        negative = particles_by_id.get(mirror.negative_particle)
        positive = particles_by_id.get(mirror.positive_particle)
        if negative is None or positive is None:
            violations.append("unresolved_mirror")
            continue
        if negative.polarity != "negative" or positive.polarity != "positive":
            violations.append("mirror_polarity_mismatch")
        if not mirror.mirror_id.strip() or not mirror.invariant.strip() or not mirror.boundary.strip():
            violations.append("incomplete_mirror")

    world_ids = [world.world_id for world in structure.parallel_worlds]
    if len(set(world_ids)) != len(world_ids):
        violations.append("duplicate_world_id")
    registered_worlds = set(world_ids)
    for particle in structure.particles:
        if particle.world_id != BASE_WORLD and particle.world_id not in registered_worlds:
            violations.append("unresolved_world_particle")
    base_ids = {
        particle.particle_id
        for particle in structure.particles
        if particle.world_id == BASE_WORLD
    }
    for world in structure.parallel_worlds:
        if not world.world_id.strip() or world.world_id == BASE_WORLD or not world.label.strip():
            violations.append("invalid_world")
        sources = [source_id for source_id, _ in world.correspondence]
        targets = [target_id for _, target_id in world.correspondence]
        if len(set(sources)) != len(sources) or len(set(targets)) != len(targets):
            violations.append("ambiguous_world_correspondence")
        world_particle_ids = {
            particle.particle_id
            for particle in structure.particles
            if particle.world_id == world.world_id
        }
        if set(sources) != base_ids or set(targets) != world_particle_ids:
            violations.append("incomplete_world_correspondence")
        for source_id, target_id in world.correspondence:
            source_particle = particles_by_id.get(source_id)
            target_particle = particles_by_id.get(target_id)
            if (
                source_particle is None
                or target_particle is None
                or source_particle.world_id != BASE_WORLD
                or target_particle.world_id != world.world_id
            ):
                violations.append("unresolved_world_correspondence")
    return GenesisAudit(not violations, tuple(violations))
