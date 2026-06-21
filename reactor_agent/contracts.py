from __future__ import annotations

from enum import Enum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class LiteratureFactType(str, Enum):
    STRUCTURE = "structure"
    REACTION = "reaction"
    MEMBRANE = "membrane"
    FEED = "feed"
    PERFORMANCE = "performance"
    FAILURE = "failure"


class LiteratureSource(BaseModel):
    doc_id: str
    doi: str | None = None
    title: str
    chunk_id: str | None = None


class Fact(BaseModel):
    model_config = ConfigDict(extra="forbid")

    value: str
    chunk_id: str | None
    section_title: str | None


class PaperFacts(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    doi: str
    structure: list[Fact]
    reaction: list[Fact]
    membrane: list[Fact]
    feed: list[Fact]
    performance: list[Fact]
    failure: list[Fact]


class LiteratureFact(BaseModel):
    doc_id: str
    chunk_id: str
    fact_type: LiteratureFactType
    text: str
    source: str = "parsed"
    confidence: float = Field(ge=0, le=1, default=0.5)


class LiteratureDBStats(BaseModel):
    n_docs: int
    n_chunks: int
    tags: list[str] = Field(default_factory=list)
    db_path: str


class CorePaperSummary(BaseModel):
    doc_id: str
    title: str
    doi: str | None = None
    score: float = Field(default=0)
    reason: str = ""
    anchor: bool = False


class LiteratureFactExtraction(BaseModel):
    doc_id: str
    facts: list[LiteratureFact] = Field(min_length=6, max_length=6)


class ChunkInputRecord(BaseModel):
    doc_id: str
    filename: str
    page_number: int
    paragraph_id: str
    chunk_id: str
    char_start: int
    char_end: int
    text: str
    clean_text: str
    section_title: str
    chunk_type: str
    source_block_type: str
    source_block_id: int


KGNodeType = Literal[
    "Paper",
    "Claim",
    "Reactor",
    "Cathode",
    "Anode",
    "Separator",
    "Electrolyte",
    "Gas Feed",
    "Operating Condition",
    "Performance",
    "Failure Mode",
    "Diagnosis",
    "Next Hypothesis",
]

KGRelation = Literal[
    "supports",
    "has_component",
    "improves",
    "causes_risk",
    "caused_by",
    "evidenced_by",
    "replaces",
]


class KGProperty(BaseModel):
    model_config = ConfigDict(extra="forbid")

    key: str
    value: str


class ExtractedKGNode(BaseModel):
    model_config = ConfigDict(extra="forbid")

    node_id: str
    type: KGNodeType
    label: str
    props: list[KGProperty]


class ExtractedKGEdge(BaseModel):
    model_config = ConfigDict(extra="forbid")

    src: str
    dst: str
    relation: KGRelation
    source_doc_id: str | None
    source_chunk_id: str | None
    experiment_ref: str | None


class KGPaperExtraction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    nodes: list[ExtractedKGNode]
    edges: list[ExtractedKGEdge]


class KGPaperEntities(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    nodes: list[ExtractedKGNode]


class KGPaperEdges(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    edges: list[ExtractedKGEdge]


class LiteratureRef(BaseModel):
    model_config = ConfigDict(extra="forbid")

    doc_id: str
    doi: str | None = None
    title: str


class ReactorRecommendation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_id: str
    prev_failure_mode: list[str]
    primary_bottleneck: str
    hypothesis: str
    new_architecture: str
    design_change: list[str]
    rationale: str
    expected_improvement: str
    key_risks: list[str]
    min_experiment: list[str]
    discriminating_test: list[str]
    diagnostic_trigger: list[str]
    go_no_go: str
    literature_refs: list[LiteratureRef] = Field(min_length=3)
    score: float | None = None


class BuildLayer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    order: int
    component: str
    material: str
    thickness: str
    active_area: str


class BuildSheet(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_id: str
    layers: list[BuildLayer]
    cathode_feed: list[str]
    anode_feed: list[str]
    use_koh_spray: bool
    prewetting: list[str]
    gas_params: dict[str, str]
    gasket_and_clamping: list[str]
    test_plan: list[str]
    teardown_photo_points: list[str]
    safety_checks: list[str]
    notes: str = ""


class Step3RunConfig(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_id: str
    kg_dir: str
    output_dir: str
    diagnosis: str
    evidence_counts: dict | None = None
    seed_counts: dict | None = None
    chain_counts: dict | None = None
    transport_dimension_counts: dict | None = None
    reaction_system_counts: dict | None = None
    selected_doc_ids: list[str]
    model_role: str = "reasoning"
    model_name: str = "gpt-5.4"
