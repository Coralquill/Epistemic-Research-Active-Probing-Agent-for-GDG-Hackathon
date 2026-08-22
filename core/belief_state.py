"""
Data structures representing the agent's epistemic state,
hypotheses, provenance DAG, claims, and active experiments.
Compatible with standard library dataclasses with optional Pydantic support.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Literal, Optional


@dataclass
class ProvenanceNode:
    id: str
    url: str
    domain: str
    authoritativeness_score: float = 0.5
    published_timestamp: Optional[str] = None
    tls_verified: bool = True
    is_root_source: bool = True


@dataclass
class ProvenanceEdge:
    source_node_id: str
    target_node_id: str
    relation_type: str = "EXPLICIT_CITATION"  # EXPLICIT_CITATION | SYNDICATED_COPY | TEXTUAL_DERIVATIVE
    derivation_confidence: float = 1.0


@dataclass
class AtomicClaim:
    id: str
    source_node_id: str
    verbatim_quote: str
    normalized_assertion: str
    extraction_confidence: float = 0.9
    associated_hypotheses: Dict[str, float] = field(default_factory=dict)


@dataclass
class Hypothesis:
    id: str
    statement: str
    prior_probability: float = 0.5
    posterior_probability: float = 0.5
    status: str = "pending"  # pending | supported | refuted | inconclusive
    supporting_claim_ids: List[str] = field(default_factory=list)


@dataclass
class ContradictionCluster:
    id: str
    hypothesis_a_id: str
    hypothesis_b_id: str
    claims_a: List[str] = field(default_factory=list)
    claims_b: List[str] = field(default_factory=list)
    severity: str = "CRITICAL"  # LOW | MEDIUM | CRITICAL


@dataclass
class DigitalProbe:
    id: str
    target_environment: str = "PYTHON_SUBPROCESS"  # PYTHON_SUBPROCESS | HTTP_REST | DOCKER
    code_or_payload: str = ""
    expected_outcomes: Dict[str, str] = field(default_factory=dict)
    likelihood_table: Dict[str, Dict[str, float]] = field(default_factory=dict)
    cost_estimate: float = 0.001
    risk_score: float = 0.0
    rationale: str = ""


@dataclass
class ProvenanceDAG:
    nodes: Dict[str, ProvenanceNode] = field(default_factory=dict)
    edges: List[ProvenanceEdge] = field(default_factory=list)

    def add_node(self, node: ProvenanceNode) -> None:
        self.nodes[node.id] = node

    def add_edge(self, edge: ProvenanceEdge) -> None:
        self.edges.append(edge)
        if edge.target_node_id in self.nodes:
            self.nodes[edge.target_node_id].is_root_source = False

    def get_root_nodes(self) -> List[ProvenanceNode]:
        derived_targets = {edge.target_node_id for edge in self.edges}
        return [node for node_id, node in self.nodes.items() if node_id not in derived_targets]

    def compute_source_independence_ratio(self) -> float:
        if not self.nodes:
            return 1.0
        roots = self.get_root_nodes()
        return len(roots) / len(self.nodes)


@dataclass
class BeliefState:
    query: str
    hypotheses: List[Hypothesis] = field(default_factory=list)
    provenance_dag: ProvenanceDAG = field(default_factory=ProvenanceDAG)
    claims: List[AtomicClaim] = field(default_factory=list)
    contradictions: List[ContradictionCluster] = field(default_factory=list)
    active_probes: List[DigitalProbe] = field(default_factory=list)
    epistemic_entropy: float = 1.0
    source_independence_ratio: float = 1.0
    current_regime: str = "SCARCITY"

    def get_hypothesis(self, hypo_id: str) -> Optional[Hypothesis]:
        for h in self.hypotheses:
            if h.id == hypo_id:
                return h
        return None


@dataclass
class AgentResponse:
    query: str
    verified_answer: str
    confidence: float
    epistemic_regime: str
    initial_entropy: float
    final_entropy: float
    independent_roots_count: int
    total_sources_scraped: int
    echo_chamber_pruned: bool
    probes_executed: List[Dict] = field(default_factory=list)
    residual_uncertainty: Optional[str] = None
