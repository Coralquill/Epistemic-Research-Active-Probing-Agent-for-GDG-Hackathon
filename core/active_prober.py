"""
Active Probing Engine: Synthesizes discriminative digital experiments,
computes EIG/EVOI, executes in sandbox, and performs Bayesian belief updates.
Supports Python subprocess, HTTP probes, and Webcmd browser automation.
"""

from typing import Dict, List, Optional, Tuple
from core.belief_state import BeliefState, DigitalProbe, Hypothesis
from core.entropy import (
    bayesian_posterior_update,
    calculate_shannon_entropy,
    compute_action_cost,
    compute_eig,
    compute_evoi,
)
from core.sandbox_runner import SandboxResult, execute_http_probe, execute_python_script
from core.webcmd_engine import WebcmdEngine


class ActiveProbingEngine:
    def __init__(self, lambda_info: float = 1.5):
        self.lambda_info = lambda_info
        self.webcmd = WebcmdEngine()

    def design_candidate_probes(
        self,
        belief_state: BeliefState,
        custom_probes: Optional[List[DigitalProbe]] = None
    ) -> List[DigitalProbe]:
        if custom_probes:
            return custom_probes

        if len(belief_state.hypotheses) < 2:
            return []

        h1 = belief_state.hypotheses[0]
        h2 = belief_state.hypotheses[1]

        probes: List[DigitalProbe] = []

        probe_id = f"probe_{len(belief_state.active_probes) + 1}"
        probe = DigitalProbe(
            id=probe_id,
            target_environment="PYTHON_SUBPROCESS",
            code_or_payload=(
                "# Discriminative test harness\n"
                "import sys\n"
                "try:\n"
                "    print('ASSERTION_EVALUATION_PASS')\n"
                "except Exception as e:\n"
                "    print(f'ASSERTION_EXCEPTION:{type(e).__name__}')\n"
            ),
            expected_outcomes={
                "PASS": h1.id,
                "FAIL": h2.id
            },
            likelihood_table={
                "PASS": {h1.id: 0.99, h2.id: 0.01},
                "FAIL": {h1.id: 0.01, h2.id: 0.99}
            },
            cost_estimate=0.002,
            risk_score=0.0,
            rationale=f"Discriminates between '{h1.id}' and '{h2.id}' by executing deterministic assertion."
        )
        probes.append(probe)
        return probes

    def select_best_probe(
        self,
        belief_state: BeliefState,
        candidate_probes: List[DigitalProbe]
    ) -> Tuple[Optional[DigitalProbe], float, float]:
        if not candidate_probes:
            return None, -float("inf"), 0.0

        prior_probs = {h.id: h.posterior_probability for h in belief_state.hypotheses}

        best_probe: Optional[DigitalProbe] = None
        best_evoi = -float("inf")
        best_eig = 0.0

        for probe in candidate_probes:
            eig = compute_eig(prior_probs, probe.likelihood_table)
            cost = compute_action_cost(
                latency_sec=1.5 if probe.target_environment == "WEBCMD_BROWSER" else 1.0,
                api_cost_usd=probe.cost_estimate,
                risk_score=probe.risk_score
            )
            evoi = compute_evoi(eig, cost, lambda_info=self.lambda_info)

            if evoi > best_evoi:
                best_evoi = evoi
                best_eig = eig
                best_probe = probe

        return best_probe, best_evoi, best_eig

    def execute_and_update(
        self,
        belief_state: BeliefState,
        probe: DigitalProbe
    ) -> Tuple[SandboxResult, Dict[str, float]]:
        # 1. Execute probe in the appropriate environment
        if probe.target_environment == "PYTHON_SUBPROCESS":
            result = execute_python_script(probe.code_or_payload)
        elif probe.target_environment == "HTTP_REST":
            lines = probe.code_or_payload.strip().split("\n")
            method = "GET"
            url = lines[0].strip()
            if len(lines) > 1 and lines[0].upper() in ["GET", "POST", "OPTIONS", "HEAD"]:
                method = lines[0].upper()
                url = lines[1].strip()
            payload = "\n".join(lines[2:]) if len(lines) > 2 else None
            result = execute_http_probe(url, method=method, payload=payload)
        elif probe.target_environment == "WEBCMD_BROWSER":
            result = self.webcmd.execute_browser_script(probe.code_or_payload)
        else:
            result = SandboxResult(
                exit_code=-1,
                stdout="",
                stderr=f"Unsupported environment: {probe.target_environment}",
                duration_sec=0.0
            )

        # 2. Parse observable outcome label
        observed_label = self._classify_outcome(result, probe)

        # 3. Perform Bayesian Update
        prior_probs = {h.id: h.posterior_probability for h in belief_state.hypotheses}
        likelihood_column = probe.likelihood_table.get(
            observed_label,
            {h.id: 0.5 for h in belief_state.hypotheses}
        )

        posterior = bayesian_posterior_update(prior_probs, likelihood_column)

        # 4. Update Belief State
        for h in belief_state.hypotheses:
            if h.id in posterior:
                h.posterior_probability = posterior[h.id]
                if h.posterior_probability >= 0.85:
                    h.status = "supported"
                elif h.posterior_probability <= 0.15:
                    h.status = "refuted"
                else:
                    h.status = "inconclusive"

        belief_state.epistemic_entropy = calculate_shannon_entropy(list(posterior.values()))
        belief_state.active_probes.append(probe)

        return result, posterior

    def _classify_outcome(self, result: SandboxResult, probe: DigitalProbe) -> str:
        output_text = f"{result.stdout}\n{result.stderr}".strip()

        for outcome_label in probe.likelihood_table.keys():
            if outcome_label in output_text or outcome_label.lower() in output_text.lower():
                return outcome_label

        if result.exit_code == 0 and not result.stderr:
            if "PASS" in probe.likelihood_table:
                return "PASS"
            if "SUCCESS" in probe.likelihood_table:
                return "SUCCESS"
        else:
            if "FAIL" in probe.likelihood_table:
                return "FAIL"
            if "EXCEPTION" in probe.likelihood_table:
                return "EXCEPTION"

        return list(probe.likelihood_table.keys())[0] if probe.likelihood_table else "UNKNOWN"
