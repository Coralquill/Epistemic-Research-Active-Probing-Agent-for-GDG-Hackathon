"""
Passive research module: Web search retrieval, claim extraction,
Provenance DAG construction, echo-chamber de-duplication, and contradiction detection.
"""

from typing import Dict, List, Tuple
from core.belief_state import (
    AtomicClaim,
    BeliefState,
    ContradictionCluster,
    Hypothesis,
    ProvenanceDAG,
    ProvenanceEdge,
    ProvenanceNode,
)
from core.entropy import calculate_shannon_entropy, classify_epistemic_regime


class PassiveResearchEngine:
    """
    Handles the observational/retrieval phase of research.
    Constructs a Provenance DAG and extracts atomic claims with independent root tracing.
    """

    def __init__(self):
        pass

    def ingest_documents(
        self,
        belief_state: BeliefState,
        raw_documents: List[Dict]
    ) -> BeliefState:
        """
        Ingests scraped web documents into the Provenance DAG and extracts atomic claims.

        raw_documents structure:
        [
            {
                "id": "doc_1",
                "url": "https://example.com/doc",
                "domain": "example.com",
                "authoritativeness": 0.9,
                "text": "...",
                "cites": ["doc_2"] or [],
                "claims": [
                    {"quote": "...", "assertion": "...", "supports_hypo": "H1", "weight": 0.8}
                ]
            }
        ]
        """
        for doc in raw_documents:
            # 1. Add Provenance Node
            node = ProvenanceNode(
                id=doc["id"],
                url=doc.get("url", f"https://{doc['domain']}"),
                domain=doc["domain"],
                authoritativeness_score=doc.get("authoritativeness", 0.5),
                is_root_source=True
            )
            belief_state.provenance_dag.add_node(node)

            # 2. Add Citation/Syndication Edges
            for cited_id in doc.get("cites", []):
                edge = ProvenanceEdge(
                    source_node_id=doc["id"],
                    target_node_id=cited_id,
                    relation_type="SYNDICATED_COPY" if doc.get("is_copy") else "EXPLICIT_CITATION",
                    derivation_confidence=0.95
                )
                belief_state.provenance_dag.add_edge(edge)

            # 3. Extract Atomic Claims
            for claim_data in doc.get("claims", []):
                claim_id = f"c_{len(belief_state.claims) + 1}"
                claim = AtomicClaim(
                    id=claim_id,
                    source_node_id=doc["id"],
                    verbatim_quote=claim_data.get("quote", ""),
                    normalized_assertion=claim_data.get("assertion", ""),
                    associated_hypotheses={claim_data.get("supports_hypo", "H1"): claim_data.get("weight", 0.8)}
                )
                belief_state.claims.append(claim)

        # 4. Re-calculate independent root weights and update hypothesis priors
        self._update_hypothesis_priors_from_dag(belief_state)

        # 5. Detect Contradictions
        self._detect_contradictions(belief_state)

        # 6. Compute Epistemic Metrics
        probs = [h.prior_probability for h in belief_state.hypotheses]
        belief_state.epistemic_entropy = calculate_shannon_entropy(probs)
        belief_state.source_independence_ratio = belief_state.provenance_dag.compute_source_independence_ratio()
        belief_state.current_regime = classify_epistemic_regime(
            entropy=belief_state.epistemic_entropy,
            sir=belief_state.source_independence_ratio,
            total_claims=len(belief_state.claims)
        )

        return belief_state

    def _update_hypothesis_priors_from_dag(self, belief_state: BeliefState) -> None:
        """
        Updates hypothesis priors by summing claim evidence only from independent root nodes.
        Syndicated copies and scrapers are pruned to avoid echo-chamber bias.
        """
        if not belief_state.hypotheses:
            return

        # Initialize hypothesis scores with Laplace smoothing
        scores: Dict[str, float] = {h.id: 1.0 for h in belief_state.hypotheses}

        for claim in belief_state.claims:
            source_node = belief_state.provenance_dag.nodes.get(claim.source_node_id)
            if not source_node:
                continue

            # Weight calculation: Only give full weight if it's a root source
            effective_weight = source_node.authoritativeness_score
            if not source_node.is_root_source:
                # Heavily discount non-independent or circular copies
                effective_weight *= 0.05

            for hypo_id, alignment in claim.associated_hypotheses.items():
                if hypo_id in scores:
                    scores[hypo_id] += effective_weight * alignment

        # Normalize to probability distribution
        total_score = sum(scores.values())
        for h in belief_state.hypotheses:
            prob = scores[h.id] / total_score
            h.prior_probability = prob
            h.posterior_probability = prob

    def _detect_contradictions(self, belief_state: BeliefState) -> None:
        """
        Identifies opposing claims that support mutually exclusive hypotheses.
        """
        belief_state.contradictions.clear()
        if len(belief_state.hypotheses) < 2:
            return

        h1 = belief_state.hypotheses[0]
        h2 = belief_state.hypotheses[1]

        # If both hypotheses have significant non-trivial prior (> 0.25), flag contradiction
        if h1.prior_probability > 0.25 and h2.prior_probability > 0.25:
            claims_h1 = [
                c.id for c in belief_state.claims
                if c.associated_hypotheses.get(h1.id, 0) > 0.3
            ]
            claims_h2 = [
                c.id for c in belief_state.claims
                if c.associated_hypotheses.get(h2.id, 0) > 0.3
            ]

            cluster = ContradictionCluster(
                id="contra_1",
                hypothesis_a_id=h1.id,
                hypothesis_b_id=h2.id,
                claims_a=claims_h1,
                claims_b=claims_h2,
                severity="CRITICAL" if abs(h1.prior_probability - h2.prior_probability) < 0.3 else "MEDIUM"
            )
            belief_state.contradictions.append(cluster)
