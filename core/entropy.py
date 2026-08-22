"""
Mathematical engine for Shannon Entropy, Expected Information Gain (EIG),
Expected Value of Information (EVOI), and Bayesian Belief Updates.
"""

import math
from typing import Dict, List, Literal


def calculate_shannon_entropy(probabilities: List[float]) -> float:
    """Calculates Shannon entropy in bits for a discrete probability distribution."""
    # Filter non-positive probabilities and normalize if needed
    valid_probs = [p for p in probabilities if p > 1e-9]
    total = sum(valid_probs)
    if total <= 0:
        return 0.0
    normalized = [p / total for p in valid_probs]
    return -sum(p * math.log2(p) for p in normalized)


def compute_eig(
    prior_probs: Dict[str, float],
    likelihood_matrix: Dict[str, Dict[str, float]]
) -> float:
    """
    Computes Expected Information Gain (EIG = Mutual Information I(H; Y | a)).

    Args:
        prior_probs: Dict mapping hypothesis_id -> prior probability P(h)
        likelihood_matrix: Dict mapping outcome_label -> {hypothesis_id: P(y|h)}

    Returns:
        EIG in bits (reduction in Shannon entropy).
    """
    # Current entropy H(H)
    current_entropy = calculate_shannon_entropy(list(prior_probs.values()))

    # Compute marginal probability of each outcome P(y) = sum_h P(y|h) * P(h)
    marginal_p_y: Dict[str, float] = {}
    for outcome, h_map in likelihood_matrix.items():
        marginal_p_y[outcome] = sum(
            h_map.get(h_id, 0.0) * prior_probs.get(h_id, 0.0)
            for h_id in prior_probs
        )

    # Compute expected posterior entropy sum_y P(y) * H(H | Y=y)
    expected_post_entropy = 0.0
    for outcome, p_y in marginal_p_y.items():
        if p_y <= 1e-9:
            continue

        # Compute posterior P(h | Y=y) = (P(y|h) * P(h)) / P(y)
        posterior: Dict[str, float] = {}
        for h_id in prior_probs:
            p_y_given_h = likelihood_matrix[outcome].get(h_id, 0.0)
            posterior[h_id] = (p_y_given_h * prior_probs[h_id]) / p_y

        post_entropy = calculate_shannon_entropy(list(posterior.values()))
        expected_post_entropy += p_y * post_entropy

    eig = max(0.0, current_entropy - expected_post_entropy)
    return eig


def compute_action_cost(
    latency_sec: float,
    api_cost_usd: float = 0.001,
    risk_score: float = 0.0,
    w_time: float = 0.01,
    w_money: float = 1.0,
    w_risk: float = 10.0,
    risk_threshold: float = 0.8
) -> float:
    """
    Computes unified composite cost for an action.
    If risk_score exceeds risk_threshold, returns infinity (safety veto).
    """
    if risk_score > risk_threshold:
        return float("inf")

    cost = (w_time * latency_sec) + (w_money * api_cost_usd) + (w_risk * risk_score)
    return cost


def compute_evoi(
    eig_bits: float,
    action_cost: float,
    lambda_info: float = 1.0
) -> float:
    """
    Expected Value of Information (EVOI) = lambda * EIG - Cost.
    Positive value indicates the experiment is economically and epistemically worthwhile.
    """
    if math.isinf(action_cost):
        return -float("inf")
    return (lambda_info * eig_bits) - action_cost


def bayesian_posterior_update(
    prior_probs: Dict[str, float],
    likelihood_column: Dict[str, float]
) -> Dict[str, float]:
    """
    Updates prior probabilities to posterior given observed outcome y.

    Args:
        prior_probs: Dict mapping hypothesis_id -> P(h)
        likelihood_column: Dict mapping hypothesis_id -> P(y_obs | h)

    Returns:
        Dict mapping hypothesis_id -> normalized posterior P(h | y_obs)
    """
    unnormalized = {}
    for h_id, prior in prior_probs.items():
        lik = likelihood_column.get(h_id, 0.01)  # epsilon smoothing for unexpected observations
        unnormalized[h_id] = prior * lik

    total = sum(unnormalized.values())
    if total <= 1e-9:
        # If all likelihoods are zero, retain prior with uniform smoothing
        return {h_id: 1.0 / len(prior_probs) for h_id in prior_probs}

    return {h_id: val / total for h_id, val in unnormalized.items()}


def classify_epistemic_regime(
    entropy: float,
    sir: float,
    total_claims: int,
    tau_h: float = 0.35,
    tau_sir: float = 0.5
) -> Literal["CONSERVATIVE_CONSENSUS", "CONTRADICTION", "SCARCITY", "ECHO_CHAMBER", "ALEATORIC_VOID"]:
    """
    Classifies the current state of knowledge into an actionable regime.
    """
    if total_claims == 0:
        return "SCARCITY"

    if entropy < tau_h:
        if sir >= tau_sir:
            return "CONSERVATIVE_CONSENSUS"
        else:
            return "ECHO_CHAMBER"
    else:
        if sir >= tau_sir:
            return "CONTRADICTION"
        else:
            return "ECHO_CHAMBER"
