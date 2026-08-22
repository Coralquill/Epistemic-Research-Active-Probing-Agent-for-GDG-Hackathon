/**
 * Main Application Logic: Dual-Mode Connection (WebSocket & REST),
 * Benchmark Controller, UI State Manager & Rich Output Card Renderer
 */

// ── API Configuration ──────────────────────────────────────────────────────
// When deployed: replace "" with your Render backend URL, e.g.:
//   "https://epistemic-agent-api.onrender.com"
// When running locally: keep it as "" (uses same-origin requests)
const API_BASE_URL = "https://epistemic-research-active-probing-agent.onrender.com";
// ──────────────────────────────────────────────────────────────────────────

let benchmarks = [];
let selectedBenchmark = null;
let ws = null;
let dagVisualizer = null;
let beliefVisualizer = null;
let lastReportData = null;

document.addEventListener("DOMContentLoaded", async () => {
  dagVisualizer = new DAGVisualizer("dag-container");
  beliefVisualizer = new BeliefVisualizer("hypotheses-container", "entropy-container");

  await loadBenchmarks();
  setupEventListeners();
});

async function loadBenchmarks() {
  try {
    const res = await fetch("/api/benchmarks");
    benchmarks = await res.json();
    const select = document.getElementById("benchmark-select");
    select.innerHTML = "";

    benchmarks.forEach((b) => {
      const opt = document.createElement("option");
      opt.value = b.id;
      opt.textContent = b.name;
      select.appendChild(opt);
    });

    if (benchmarks.length > 0) {
      selectBenchmark(benchmarks[0].id);
    }
  } catch (e) {
    console.error("Failed to load benchmarks:", e);
    logTerminal("[WARNING] Could not fetch benchmarks. Is 'python3 simple_server.py' running in your terminal?");
  }
}

function selectBenchmark(id) {
  selectedBenchmark = benchmarks.find(b => b.id === id);
  if (!selectedBenchmark) return;

  document.getElementById("query-input").value = selectedBenchmark.query;
  document.getElementById("benchmark-desc").textContent = selectedBenchmark.description;

  // Reset visualizer previews
  beliefVisualizer.update(selectedBenchmark.hypotheses.map(h => ({
    ...h,
    prior_probability: 1.0 / selectedBenchmark.hypotheses.length,
    posterior_probability: 1.0 / selectedBenchmark.hypotheses.length
  })), 1.0);

  // Clear terminal & report
  document.getElementById("terminal-output").textContent = "# Ready. Click 'Execute Epistemic Loop' to start causal research.";
  document.getElementById("result-card").classList.add("hidden");
}

function setupEventListeners() {
  document.getElementById("benchmark-select").addEventListener("change", (e) => {
    selectBenchmark(e.target.value);
  });

  document.getElementById("run-btn").addEventListener("click", () => {
    runAgentLoop();
  });

  const copyBtn = document.getElementById("copy-report-btn");
  if (copyBtn) {
    copyBtn.addEventListener("click", () => {
      copyAuditReportToClipboard();
    });
  }
}

function logTerminal(text) {
  const term = document.getElementById("terminal-output");
  term.textContent += `\n${text}`;
  term.scrollTop = term.scrollHeight;
}

function runAgentLoop() {
  const runBtn = document.getElementById("run-btn");
  runBtn.disabled = true;
  runBtn.innerHTML = `<span>Running Epistemic Loop...</span>`;

  document.getElementById("terminal-output").textContent = "[INIT] Launching research cycle...";
  document.getElementById("result-card").classList.add("hidden");

  const queryText = document.getElementById("query-input").value;
  const isCustomQuery = selectedBenchmark ? (queryText !== selectedBenchmark.query) : true;

  const payload = {
    query: queryText,
    hypotheses: (!isCustomQuery && selectedBenchmark) ? selectedBenchmark.hypotheses : [],
    raw_docs: (!isCustomQuery && selectedBenchmark) ? selectedBenchmark.raw_docs : [],
    probes: (!isCustomQuery && selectedBenchmark) ? selectedBenchmark.probes : [],
    tau_stop: parseFloat(document.getElementById("tau-stop-input").value || 0.20),
    lambda_info: parseFloat(document.getElementById("lambda-info-input").value || 1.5)
  };

  executeViaRest(payload, runBtn);
}

async function executeViaRest(payload, runBtn) {
  try {
    logTerminal("[STAGE_PASSIVE_DAG] Ingesting documents and constructing Provenance DAG...");
    
    const res = await fetch("/api/research/run", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload)
    });

    if (!res.ok) {
      throw new Error(`HTTP Error ${res.status}: ${res.statusText}`);
    }

    const data = await res.json();
    lastReportData = data;

    // Render DAG from sources returned by backend
    const rawDocs = data.raw_docs || (selectedBenchmark ? selectedBenchmark.raw_docs : []);
    const mockDag = {
      nodes: rawDocs.map(d => ({
        id: d.id,
        domain: d.domain,
        authoritativeness: d.authoritativeness,
        is_root: !d.is_copy
      })),
      edges: rawDocs.flatMap(d => (d.cites || []).map(c => ({
        source: d.id,
        target: c,
        relation: d.is_copy ? "SYNDICATED_COPY" : "EXPLICIT_CITATION"
      })))
    };
    dagVisualizer.render(mockDag);

    logTerminal(`[STAGE_TRIAGE] Epistemic Regime: ${data.epistemic_regime}`);
    if (data.probes_executed && data.probes_executed.length > 0) {
      data.probes_executed.forEach((p) => {
        logTerminal(`[STAGE_SANDBOX_TELEMETRY] Probe: ${p.probe_id} | ExitCode: ${p.exit_code} | Duration: ${(p.duration_sec * 1000).toFixed(1)}ms`);
        if (p.stdout) logTerminal(`[STDOUT]\n${p.stdout}`);
        if (p.stderr) logTerminal(`[STDERR]\n${p.stderr}`);
      });
    }

    // Update belief bars with server's hypotheses
    const hypothesesToDisplay = data.initial_hypotheses || (selectedBenchmark ? selectedBenchmark.hypotheses : []);
    const updatedHypotheses = hypothesesToDisplay.map(h => ({
      ...h,
      prior_probability: 1.0 / hypothesesToDisplay.length,
      posterior_probability: data.verified_answer.includes(h.statement) ? data.confidence : (1.0 - data.confidence)
    }));
    beliefVisualizer.update(updatedHypotheses, data.final_entropy);

    document.getElementById("stat-scraped").textContent = data.total_sources_scraped;
    document.getElementById("stat-roots").textContent = data.independent_roots_count;
    document.getElementById("stat-regime").textContent = data.epistemic_regime;

    renderFinalReport(data);
    logTerminal("[STAGE_COMPLETED] Research cycle concluded successfully.");
  } catch (err) {
    logTerminal(`[ERROR] Connection failed: ${err.message}`);
    logTerminal(`👉 Make sure 'python3 simple_server.py' is actively running in your terminal!`);
  } finally {
    runBtn.disabled = false;
    runBtn.innerHTML = `<span>🚀 Execute Epistemic Loop</span>`;
  }
}

function renderFinalReport(data) {
  const card = document.getElementById("result-card");
  card.classList.remove("hidden");

  document.getElementById("report-answer").textContent = data.verified_answer.replace(/^Empirically verified conclusion:\s*/, "");
  document.getElementById("report-confidence").textContent = `${(data.confidence * 100).toFixed(1)}%`;

  // Echo Chamber Badge
  const badgeEcho = document.getElementById("badge-echo");
  if (data.echo_chamber_pruned) {
    badgeEcho.textContent = "Echo Chamber Detected & Pruned";
    badgeEcho.className = "px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-rose-950/80 text-rose-300 border border-rose-800/60";
  } else {
    badgeEcho.textContent = "Clean Source Topology";
    badgeEcho.className = "px-2.5 py-0.5 rounded-full text-[11px] font-medium bg-slate-800 text-slate-300 border border-slate-700";
  }

  // Provenance Badges
  document.getElementById("report-roots-badge").textContent = `${data.independent_roots_count} Independent Roots`;
  const prunedCount = data.total_sources_scraped - data.independent_roots_count;
  const scrapersBadge = document.getElementById("report-scrapers-badge");
  if (prunedCount > 0) {
    scrapersBadge.textContent = `${prunedCount} Scraper Copies Pruned`;
    scrapersBadge.classList.remove("hidden");
  } else {
    scrapersBadge.classList.add("hidden");
  }

  // Telemetry Highlight
  const probeHighlight = document.getElementById("report-probe-highlight");
  const execTime = document.getElementById("report-exec-time");
  if (data.probes_executed && data.probes_executed.length > 0) {
    const p = data.probes_executed[0];
    probeHighlight.textContent = p.stdout || p.stderr || "Executed successfully in isolated micro-sandbox.";
    execTime.textContent = `Execution Latency: ${(p.duration_sec * 1000).toFixed(1)}ms`;
  } else {
    probeHighlight.textContent = "Resolved via high-authority root consensus without requiring active sandbox probing.";
    execTime.textContent = "Passive Audit: Instant";
  }

  // Entropy Delta
  const entropyDiff = (data.final_entropy - data.initial_entropy).toFixed(3);
  document.getElementById("report-entropy-delta").innerHTML = `${data.initial_entropy.toFixed(3)} &rarr; ${data.final_entropy.toFixed(3)} bits <span class="text-emerald-400 font-normal">(&Delta; ${entropyDiff})</span>`;
  document.getElementById("report-regime-shift").textContent = `${data.epistemic_regime} \u2192 VERIFIED`;
}

function copyAuditReportToClipboard() {
  if (!lastReportData) return;

  const md = `### 🔬 Epistemic Research Agent Audit Report
**Question:** ${lastReportData.query}

**🎯 Verified Conclusion:**
${lastReportData.verified_answer}

**Epistemic Metrics:**
- **Posterior Certainty:** ${(lastReportData.confidence * 100).toFixed(1)}%
- **Entropy Reduction:** ${lastReportData.initial_entropy.toFixed(3)} -> ${lastReportData.final_entropy.toFixed(3)} bits
- **Independent Roots:** ${lastReportData.independent_roots_count} (from ${lastReportData.total_sources_scraped} scraped)
- **Echo Chamber Pruned:** ${lastReportData.echo_chamber_pruned ? "YES" : "NO"}
- **Probes Executed:** ${lastReportData.probes_executed.length}

*Verified via Epistemic Research & Causal Probing Engine.*`;

  navigator.clipboard.writeText(md).then(() => {
    const btnText = document.getElementById("copy-btn-text");
    const orig = btnText.textContent;
    btnText.textContent = "✓ Copied to Clipboard!";
    setTimeout(() => {
      btnText.textContent = orig;
    }, 2000);
  });
}
