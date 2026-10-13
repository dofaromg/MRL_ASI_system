# origin_signature: MrLiouWord
"""
MRL 黑洞模型 / MRL Black Hole Model

A Notion structure that swallows everything and returns everything.
一個吞下所有東西、也歸還所有東西的 Notion 結構。
"""

from .builder import BlackHoleBuilder, NotionAPIClient
from .conservation import ConservationReport, Violation, audit_conservation, round_trip_hours
from .celestial_vectors import CelestialVectorGraph
from .genesis import (
    GenesisAudit,
    GenesisParticle,
    GenesisStructure,
    LogicRelation,
    MirrorConstraint,
    ParallelWorld,
    ParticleSpec,
    audit_genesis_structure,
)
from .model import (
    MODEL_TITLE,
    MODEL_VERSION,
    BlackHoleModel,
    LayerSpec,
    PropertySpec,
    default_model,
    make_return_id,
)
from .snapshot import fetch_snapshot, flatten_page, query_database
from .translation import (
    BlackHoleTranslationPipeline,
    StageTrace,
    TranslationAudit,
    TranslationResult,
    audit_translation,
    make_translation_return_id,
)

__all__ = [
    "BlackHoleBuilder",
    "BlackHoleModel",
    "BlackHoleTranslationPipeline",
    "CelestialVectorGraph",
    "ConservationReport",
    "GenesisAudit",
    "GenesisParticle",
    "GenesisStructure",
    "LayerSpec",
    "LogicRelation",
    "MirrorConstraint",
    "ConservationReport",
    "LayerSpec",
    "MODEL_TITLE",
    "MODEL_VERSION",
    "NotionAPIClient",
    "PropertySpec",
    "ParallelWorld",
    "ParticleSpec",
    "StageTrace",
    "TranslationAudit",
    "TranslationResult",
    "Violation",
    "audit_conservation",
    "audit_genesis_structure",
    "audit_translation",
    "Violation",
    "audit_conservation",
    "default_model",
    "fetch_snapshot",
    "flatten_page",
    "make_return_id",
    "make_translation_return_id",
    "query_database",
    "round_trip_hours",
]
