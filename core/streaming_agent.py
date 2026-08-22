"""
Streaming Epistemic Agent: Emits asynchronous real-time events over WebSockets
as the agent progresses through hypothesis formulation, DAG construction,
entropy calculation, sandboxed probing, and Bayesian updating.
"""

import asyncio
from dataclasses import asdict
from typing import AsyncGenerator, Dict, List, Optional
from core.active_prober import ActiveProbingEngine
from core.belief_state import (
    AgentResponse,
    BeliefState,
    DigitalProbe,
    Hypothesis,
    ProvenanceDAG,
)
from core.entropy import calculate_shannon_entropy
from core.passive_agent import PassiveResearchEngine


class StreamingEpistemicAgent:
    def __init__(
        self,
        tau_stop: float = 0.20,
        max_active_steps: int = 3,
        lambda_info: float = 1.5,
        step_delay_sec: float = 0.6  # Smooth animation pacing for frontend UI
    ):
        self.tau_stop = tau_stop
        self.max_active_steps = max_active_steps
        self.lambda_info = lambda_info
        self.step_delay_sec = step_delay_sec
        self.passive_engine = PassiveResearchEngine()
        self.active_engine = ActiveProbingEngine(lambda_info=lambda_info)

    async def run_stream(
        self,
        query: str,
        initial_hypotheses: List[Dict[str, str]],
        raw_documents: List[Dict],
        custom_probes: Optional[List[Dict]] = None
    ) -> AsyncGenerator[Dict, None]:
        """
        Executes the agent loop while yielding real-time JSON events.
        """
        # 1. Initialize State
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

        yield {
            "event": "STAGE_INIT",
            "message": "Initialized research state & hypothesis space.",
            "data": {
                "query": query,
                "hypotheses": [asdict(h) for h in state.hypotheses],
                "entropy": state.epistemic_entropy
            }
        }
        await asyncio.sleep(self.step_delay_sec)

        # 2. Ingest Passive Documents & Build DAG
        state = self.passive_engine.ingest_documents(state, raw_documents)
        scraped_count = len(raw_documents)
        root_nodes = state.provenance_dag.get_root_nodes()
        root_count = len(root_nodes)
        echo_pruned = (scraped_count - root_count) > 0

        # Serialize DAG for D3 visualization
        dag_data = {
            "nodes": [
                {
                    "id": n.id,
                    "domain": n.domain,
                    "url": n.url,
                    "authoritativeness": n.authoritativeness_score,
                    "is_root": n.is_root_source
                }
                for n in state.provenance_dag.nodes.values()
            ],
            "edges": [
                {
                    "source": e.source_node_id,
                    "target": e.target_node_id,
                    "relation": e.relation_type,
                    "confidence": e.derivation_confidence
                }
                for e in state.provenance_dag.edges
            ]
        }

        yield {
            "event": "STAGE_PASSIVE_DAG",
            "message": f"Processed {scraped_count} documents. Identified {root_count} independent root sources.",
            "data": {
                "dag": dag_data,
                "claims_count": len(state.claims),
                "hypotheses": [asdict(h) for h in state.hypotheses],
                "entropy": state.epistemic_entropy,
                "sir": state.source_independence_ratio,
                "echo_pruned": echo_pruned,
                "regime": state.current_regime
            }
        }
        await asyncio.sleep(self.step_delay_sec)

        # 3. Epistemic Triage
        yield {
            "event": "STAGE_TRIAGE",
            "message": f"Epistemic Regime: {state.current_regime} (Entropy: {state.epistemic_entropy:.3f} bits).",
            "data": {
                "regime": state.current_regime,
                "entropy": state.epistemic_entropy,
                "needs_active_probing": state.epistemic_entropy > self.tau_stop
            }
        }
        await asyncio.sleep(self.step_delay_sec)

        # 4. Check if passive consensus was reached
        if state.epistemic_entropy <= self.tau_stop and state.current_regime == "CONSERVATIVE_CONSENSUS":
            best_hypo = max(state.hypotheses, key=lambda h: h.posterior_probability)
            final_res = AgentResponse(
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
            yield {
                "event": "STAGE_COMPLETED",
                "message": "Research successfully concluded via passive consensus.",
                "data": asdict(final_res)
            }
            return

        # 5. Active Experimentation Phase
        # Convert custom_probes dicts to DigitalProbe instances
        probes_list: List[DigitalProbe] = []
        if custom_probes:
            for p in custom_probes:
                probes_list.append(DigitalProbe(
                    id=p["id"],
                    target_environment=p.get("target_environment", "PYTHON_SUBPROCESS"),
                    code_or_payload=p["code_or_payload"],
                    expected_outcomes=p.get("expected_outcomes", {}),
                    likelihood_table=p.get("likelihood_table", {}),
                    cost_estimate=p.get("cost_estimate", 0.001),
                    risk_score=p.get("risk_score", 0.0),
                    rationale=p.get("rationale", "")
                ))

        executed_probes_log = []
        step_count = 0

        while state.epistemic_entropy > self.tau_stop and step_count < self.max_active_steps:
            step_count += 1
            best_probe, max_evoi, max_eig = self.active_engine.select_best_probe(state, probes_list)

            if not best_probe or max_evoi <= 0:
                yield {
                    "event": "STAGE_STOPPING_DIMINISHING_RETURNS",
                    "message": "Further active interventions yielded zero or negative expected value of information (EVOI <= 0).",
                    "data": {"max_evoi": max_evoi}
                }
                break

            yield {
                "event": "STAGE_PROBE_SELECTED",
                "message": f"Selected optimal probe: {best_probe.id} (EVOI: {max_evoi:.3f}, EIG: {max_eig:.3f} bits).",
                "data": {
                    "probe": asdict(best_probe),
                    "evoi": max_evoi,
                    "eig": max_eig
                }
            }
            await asyncio.sleep(self.step_delay_sec)

            # Execute Probe in isolated sandbox
            sandbox_res, new_posterior = self.active_engine.execute_and_update(state, best_probe)

            probe_log_entry = {
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
            }
            executed_probes_log.append(probe_log_entry)

            yield {
                "event": "STAGE_SANDBOX_TELEMETRY",
                "message": f"Sandbox execution completed in {sandbox_res.duration_sec * 1000:.1f}ms with exit code {sandbox_res.exit_code}.",
                "data": {
                    "telemetry": probe_log_entry,
                    "hypotheses": [asdict(h) for h in state.hypotheses],
                    "entropy": state.epistemic_entropy
                }
            }
            await asyncio.sleep(self.step_delay_sec)

            if best_probe in probes_list:
                probes_list.remove(best_probe)

        # 6. Final Synthesis
        best_hypo = max(state.hypotheses, key=lambda h: h.posterior_probability)
        if best_hypo.posterior_probability >= 0.80:
            verified_answer = (
                f"Empirically verified conclusion: {best_hypo.statement}\n"
                f"(Posterior certainty: {best_hypo.posterior_probability * 100:.1f}%, "
                f"Residual Entropy: {state.epistemic_entropy:.3f} bits)"
            )
            residual = None
        else:
            verified_answer = (
                f"Information remains inconclusive after passive audit and {len(executed_probes_log)} active experiments. "
                f"Leading hypothesis: {best_hypo.statement} ({best_hypo.posterior_probability * 100:.1f}% confidence)."
            )
            residual = "Further active interventions yielded diminishing expected value or hit budget ceilings."

        final_res = AgentResponse(
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

        yield {
            "event": "STAGE_COMPLETED",
            "message": "Research cycle finished with calibrated verification.",
            "data": asdict(final_res)
        }
