"""
Main Agent Orchestrator: State machine managing passive research, Provenance DAG audits,
epistemic entropy triage, active experimentation, and calibrated stopping.
"""

from typing import Dict, List, Optional
from core.active_prober import ActiveProbingEngine
from core.belief_state import AgentResponse, BeliefState, DigitalProbe, Hypothesis
from core.entropy import calculate_shannon_entropy
from core.passive_agent import PassiveResearchEngine


class EpistemicAgent:
    """
    Autonomous Epistemic Agent that transitions from passive retrieval
    to active digital experimentation when information is insufficient or contradictory.
    """

    def __init__(
        self,
        tau_stop: float = 0.20,
        max_active_steps: int = 3,
        lambda_info: float = 1.5
    ):
        self.tau_stop = tau_stop
        self.max_active_steps = max_active_steps
        self.passive_engine = PassiveResearchEngine()
        self.active_engine = ActiveProbingEngine(lambda_info=lambda_info)

    def run(
        self,
        query: str,
        initial_hypotheses: List[Dict[str, str]],
        raw_documents: List[Dict],
        custom_probes: Optional[List[DigitalProbe]] = None
    ) -> AgentResponse:
        """
        Executes the full agent loop.

        Args:
            query: The research question
            initial_hypotheses: List of hypothesis dicts [{"id": "H1", "statement": "..."}]
            raw_documents: Scraped documents for the passive phase
            custom_probes: Optional pre-synthesized domain probes to evaluate
        """
        # Step 1: Initialize Belief State
        hypotheses = [
            Hypothesis(
                id=h["id"],
                statement=h["statement"],
                prior_probability=1.0 / len(initial_hypotheses),
                posterior_probability=1.0 / len(initial_hypotheses)
            )
            for h in initial_hypotheses
        ]

        state = BeliefState(
            query=query,
            hypotheses=hypotheses,
            epistemic_entropy=calculate_shannon_entropy([h.prior_probability for h in hypotheses])
        )
        initial_entropy = state.epistemic_entropy

        # Step 2: Passive Research Phase & Provenance DAG Ingestion
        state = self.passive_engine.ingest_documents(state, raw_documents)
        scraped_count = len(raw_documents)
        root_nodes = state.provenance_dag.get_root_nodes()
        root_count = len(root_nodes)
        echo_pruned = (scraped_count - root_count) > 0

        executed_probes_log = []

        # Step 3: Epistemic Triage Check
        # If entropy is already low and we have good root independence, we are done
        if state.epistemic_entropy <= self.tau_stop and state.current_regime == "CONSERVATIVE_CONSENSUS":
            best_hypo = max(state.hypotheses, key=lambda h: h.posterior_probability)
            return AgentResponse(
                query=query,
                verified_answer=f"Conclusive consensus established from {root_count} independent root sources: {best_hypo.statement}",
                confidence=best_hypo.posterior_probability,
                epistemic_regime=state.current_regime,
                initial_entropy=initial_entropy,
                final_entropy=state.epistemic_entropy,
                independent_roots_count=root_count,
                total_sources_scraped=scraped_count,
                echo_chamber_pruned=echo_pruned,
                probes_executed=[]
            )

        # Step 4: Active Experimentation Loop
        step_count = 0
        while state.epistemic_entropy > self.tau_stop and step_count < self.max_active_steps:
            step_count += 1

            # Design & select candidate probes
            candidate_probes = self.active_engine.design_candidate_probes(state, custom_probes)
            best_probe, max_evoi, max_eig = self.active_engine.select_best_probe(state, candidate_probes)

            # Stopping check: Diminishing returns (EVOI <= 0)
            if not best_probe or max_evoi <= 0:
                break

            # Execute probe in sandbox and update beliefs
            sandbox_res, new_posterior = self.active_engine.execute_and_update(state, best_probe)

            executed_probes_log.append({
                "probe_id": best_probe.id,
                "environment": best_probe.target_environment,
                "rationale": best_probe.rationale,
                "exit_code": sandbox_res.exit_code,
                "stdout": sandbox_res.stdout,
                "stderr": sandbox_res.stderr,
                "duration_sec": sandbox_res.duration_sec,
                "evoi": max_evoi,
                "eig": max_eig,
                "posteriors": new_posterior
            })

            # If custom probes were provided, remove the executed one from next iteration
            if custom_probes and best_probe in custom_probes:
                custom_probes.remove(best_probe)

        # Step 5: Synthesize Final Output
        best_hypo = max(state.hypotheses, key=lambda h: h.posterior_probability)

        if best_hypo.posterior_probability >= 0.80:
            verified_answer = (
                f"Empirically verified conclusion: {best_hypo.statement}\n"
                f"(Posterior certainty: {best_hypo.posterior_probability * 100:.1f}%, "
                f"Entropy: {state.epistemic_entropy:.3f} bits)"
            )
            residual = None
        else:
            verified_answer = (
                f"Information remains inconclusive after passive audit and {len(executed_probes_log)} active experiments. "
                f"Leading hypothesis: {best_hypo.statement} ({best_hypo.posterior_probability * 100:.1f}% confidence)."
            )
            residual = "Further active interventions yielded diminishing expected value or hit budget ceilings."

        return AgentResponse(
            query=query,
            verified_answer=verified_answer,
            confidence=best_hypo.posterior_probability,
            epistemic_regime=state.current_regime,
            initial_entropy=initial_entropy,
            final_entropy=state.epistemic_entropy,
            independent_roots_count=root_count,
            total_sources_scraped=scraped_count,
            echo_chamber_pruned=echo_pruned,
            probes_executed=executed_probes_log,
            residual_uncertainty=residual
        )
