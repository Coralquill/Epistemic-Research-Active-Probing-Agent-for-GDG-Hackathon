/**
 * Canvas/HTML-based Real-Time Bayesian Belief Dynamics & Entropy Gauge
 */

class BeliefVisualizer {
  constructor(chartContainerId, entropyContainerId) {
    this.chartContainer = document.getElementById(chartContainerId);
    this.entropyContainer = document.getElementById(entropyContainerId);
  }

  update(hypotheses, currentEntropy) {
    this.renderHypothesisBars(hypotheses);
    this.renderEntropyGauge(currentEntropy);
  }

  renderHypothesisBars(hypotheses) {
    if (!this.chartContainer) return;
    this.chartContainer.innerHTML = "";

    hypotheses.forEach(h => {
      const probPct = (h.posterior_probability * 100).toFixed(1);
      const priorPct = (h.prior_probability * 100).toFixed(1);
      
      const isWinner = h.posterior_probability >= 0.8;
      const isRefuted = h.posterior_probability <= 0.2;

      let barColor = "bg-blue-500";
      let statusBadge = `<span class="px-2 py-0.5 text-xs rounded bg-slate-800 text-slate-300">Pending</span>`;
      
      if (isWinner) {
        barColor = "bg-emerald-500";
        statusBadge = `<span class="px-2 py-0.5 text-xs rounded bg-emerald-900/60 text-emerald-300 border border-emerald-500/40">Verified</span>`;
      } else if (isRefuted) {
        barColor = "bg-rose-500";
        statusBadge = `<span class="px-2 py-0.5 text-xs rounded bg-rose-900/60 text-rose-300 border border-rose-500/40">Refuted</span>`;
      }

      const itemHtml = `
        <div class="mb-4 p-3 rounded-lg bg-slate-900/80 border border-slate-800">
          <div class="flex justify-between items-start mb-2">
            <div class="flex items-center space-x-2">
              <span class="font-bold text-xs px-2 py-0.5 rounded bg-slate-800 text-cyan-400 font-mono">${h.id}</span>
              <span class="text-xs text-slate-300 font-medium">${h.statement}</span>
            </div>
            ${statusBadge}
          </div>
          
          <div class="w-full bg-slate-800 rounded-full h-3.5 mb-1 overflow-hidden relative">
            <div class="${barColor} h-3.5 rounded-full transition-all duration-500 ease-out" style="width: ${probPct}%"></div>
          </div>
          
          <div class="flex justify-between text-[11px] text-slate-400 font-mono">
            <span>Prior: ${priorPct}%</span>
            <span class="font-bold text-slate-200">Posterior: ${probPct}%</span>
          </div>
        </div>
      `;
      this.chartContainer.insertAdjacentHTML("beforeend", itemHtml);
    });
  }

  renderEntropyGauge(entropy) {
    if (!this.entropyContainer) return;
    const entropyVal = Number(entropy).toFixed(3);
    const maxEntropy = 1.0;
    const pct = Math.min(100, Math.max(0, (entropy / maxEntropy) * 100));

    let statusText = "High Uncertainty (Hypothesis Contradiction)";
    let colorClass = "text-amber-400";
    if (entropy < 0.20) {
      statusText = "Low Uncertainty (Conclusive Grounding)";
      colorClass = "text-emerald-400";
    }

    this.entropyContainer.innerHTML = `
      <div class="flex justify-between items-center mb-1">
        <span class="text-xs text-slate-400">Shannon Epistemic Entropy H(P(H))</span>
        <span class="font-mono font-bold text-sm ${colorClass}">${entropyVal} bits</span>
      </div>
      <div class="w-full bg-slate-800 rounded-full h-2 mb-2 overflow-hidden">
        <div class="h-2 rounded-full transition-all duration-500 ${entropy < 0.2 ? 'bg-emerald-500' : 'bg-amber-500'}" style="width: ${pct}%"></div>
      </div>
      <div class="text-[11px] text-slate-400 flex justify-between">
        <span>Target Threshold: 0.150 bits</span>
        <span class="${colorClass}">${statusText}</span>
      </div>
    `;
  }
}
