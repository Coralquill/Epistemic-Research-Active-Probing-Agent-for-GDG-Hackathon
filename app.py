"""
Streamlit Web Dashboard: Live visualization of the Epistemic Agent's Provenance DAG,
Hypothesis Probability Dynamics, Sandboxed Telemetry Logs, and Calibrated Reports.
"""

import streamlit as st
import pandas as pd
from core.belief_state import DigitalProbe
from core.orchestrator import EpistemicAgent

st.set_page_config(
    page_title="Epistemic Research & Active Probing Agent",
    page_icon="🔬",
    layout="wide"
)

st.title("🔬 Epistemic Research & Active Probing Agent")
st.caption("A hypothesis-testing research agent that autonomously transitions from passive reading to causal digital interventions.")

# Sidebar Configuration
st.sidebar.header("Agent Parameters")
tau_stop = st.sidebar.slider("Stopping Entropy Threshold (tau_stop)", min_value=0.05, max_value=0.50, value=0.15, step=0.05)
lambda_info = st.sidebar.slider("Information Value Multiplier (lambda)", min_value=0.5, max_value=3.0, value=1.5, step=0.1)

# Benchmark Selection
benchmark_option = st.sidebar.selectbox(
    "Select Demonstration Benchmark",
    [
        "1. Software Invariant: Pydantic v2 Field(regex=...)",
        "2. Echo Chamber: SQLite UPSERT RETURNING Syndication",
        "3. Live API: Stale Spec vs Runtime Auth Header"
    ]
)

st.sidebar.markdown("---")
st.sidebar.markdown("### Architecture Highlights")
st.sidebar.info(
    "• **Provenance DAG:** De-duplicates syndicated SEO scrapers.\n"
    "• **Shannon Entropy:** Detects epistemic contradictions.\n"
    "• **EVOI Optimization:** Probes only when information gain outweighs cost.\n"
    "• **Micro-Sandbox:** Executes isolated code assertions."
)

# Benchmark Data Setup
if "1." in benchmark_option:
    query = "Does Pydantic v2 support Field(regex='^[a-z]+$') via backward compatibility, or does it throw an error in favor of pattern=?"
    hypotheses = [
        {"id": "H1", "statement": "Field(regex=...) is supported via backward compatibility alias."},
        {"id": "H2", "statement": "Field(regex=...) is completely removed; raises error at model definition."}
    ]
    raw_docs = [
        {
            "id": "doc_old_tutorial",
            "domain": "legacy-py-guide.dev",
            "authoritativeness": 0.4,
            "claims": [{"quote": "Pydantic v2 still accepts regex kwarg.", "assertion": "Field(regex) works", "supports_hypo": "H1", "weight": 0.8}]
        },
        {
            "id": "doc_migration_guide",
            "domain": "docs.pydantic.dev",
            "authoritativeness": 0.95,
            "claims": [{"quote": "regex argument is removed in v2 in favor of pattern.", "assertion": "Field(regex) raises error", "supports_hypo": "H2", "weight": 0.95}]
        },
        {
            "id": "doc_scraper_blog",
            "domain": "ai-python-scraps.io",
            "authoritativeness": 0.2,
            "cites": ["doc_old_tutorial"],
            "is_copy": True,
            "claims": [{"quote": "Pydantic v2 still accepts regex kwarg.", "assertion": "Field(regex) works", "supports_hypo": "H1", "weight": 0.8}]
        }
    ]
    custom_probe = DigitalProbe(
        id="probe_pydantic_regex",
        target_environment="PYTHON_SUBPROCESS",
        code_or_payload="""
from pydantic import BaseModel, Field
try:
    class TestModel(BaseModel):
        code: str = Field(regex="^[a-z]+$")
    print("OUTCOME:SUCCESS_ALIAS_WORKS")
except Exception as e:
    print(f"OUTCOME:EXCEPTION_{type(e).__name__}")
""",
        expected_outcomes={"SUCCESS_ALIAS_WORKS": "H1", "EXCEPTION": "H2"},
        likelihood_table={
            "OUTCOME:SUCCESS_ALIAS_WORKS": {"H1": 0.99, "H2": 0.01},
            "OUTCOME:EXCEPTION": {"H1": 0.01, "H2": 0.99}
        },
        cost_estimate=0.001,
        risk_score=0.0,
        rationale="Executes model definition in isolated runtime to verify syntax rejection."
    )
elif "2." in benchmark_option:
    query = "Does SQLite 3.35.0 support RETURNING clauses on UPSERT statements?"
    hypotheses = [
        {"id": "H1", "statement": "SQLite 3.35.0 supports RETURNING on UPSERT."},
        {"id": "H2", "statement": "SQLite 3.35.0 disallows RETURNING on UPSERT; requires SQLite 3.38.0+."}
    ]
    raw_docs = [
        {
            "id": "official_changelog",
            "domain": "sqlite.org",
            "authoritativeness": 0.99,
            "claims": [{"quote": "UPSERT RETURNING fixed in 3.38.0", "assertion": "UPSERT RETURNING fails on 3.35", "supports_hypo": "H2", "weight": 0.99}]
        },
        {
            "id": "flawed_blog_root",
            "domain": "random-medium-post.com",
            "authoritativeness": 0.35,
            "claims": [{"quote": "RETURNING works on everything in 3.35!", "assertion": "Works everywhere", "supports_hypo": "H1", "weight": 0.5}]
        },
        {
            "id": "scraper_a",
            "domain": "dev-mirror-1.xyz",
            "authoritativeness": 0.1,
            "cites": ["flawed_blog_root"],
            "is_copy": True,
            "claims": [{"quote": "RETURNING works on everything in 3.35!", "assertion": "Works everywhere", "supports_hypo": "H1", "weight": 0.5}]
        },
        {
            "id": "scraper_b",
            "domain": "dev-mirror-2.xyz",
            "authoritativeness": 0.1,
            "cites": ["scraper_a"],
            "is_copy": True,
            "claims": [{"quote": "RETURNING works on everything in 3.35!", "assertion": "Works everywhere", "supports_hypo": "H1", "weight": 0.5}]
        }
    ]
    custom_probe = DigitalProbe(
        id="probe_sqlite_upsert",
        target_environment="PYTHON_SUBPROCESS",
        code_or_payload="""
import sqlite3
try:
    conn = sqlite3.connect(":memory:")
    cur = conn.cursor()
    cur.execute("CREATE TABLE t(id INT UNIQUE, val TEXT);")
    cur.execute("INSERT INTO t VALUES(1, 'a') ON CONFLICT(id) DO UPDATE SET val='b' RETURNING *;")
    print("OUTCOME:UPSERT_RETURNING_SUPPORTED")
except sqlite3.OperationalError as e:
    print(f"OUTCOME:UPSERT_RETURNING_ERROR_{e}")
except Exception as e:
    print(f"OUTCOME:EXCEPTION_{type(e).__name__}")
""",
        expected_outcomes={"UPSERT_RETURNING_SUPPORTED": "H1", "UPSERT_RETURNING_ERROR": "H2"},
        likelihood_table={
            "OUTCOME:UPSERT_RETURNING_SUPPORTED": {"H1": 0.99, "H2": 0.01},
            "OUTCOME:UPSERT_RETURNING_ERROR": {"H1": 0.01, "H2": 0.99}
        },
        cost_estimate=0.001,
        risk_score=0.0,
        rationale="Executes live SQLite DDL/DML to verify UPSERT RETURNING syntax."
    )
else:
    query = "How to authenticate against the v1 secure endpoint: X-API-Key or Bearer Token?"
    hypotheses = [
        {"id": "H1", "statement": "Authentication requires 'X-API-Key' header."},
        {"id": "H2", "statement": "Authentication requires 'Authorization: Bearer <token>' header."}
    ]
    raw_docs = [
        {
            "id": "stale_docs",
            "domain": "docs.api-spec.internal",
            "authoritativeness": 0.6,
            "claims": [{"quote": "Pass secret in X-API-Key header", "assertion": "X-API-Key required", "supports_hypo": "H1", "weight": 0.8}]
        }
    ]
    custom_probe = DigitalProbe(
        id="probe_http_auth",
        target_environment="HTTP_REST",
        code_or_payload="GET\nhttp://127.0.0.1:8000/api/v1/secure-data\nX-API-Key: test_key",
        expected_outcomes={"400": "H2", "200": "H1"},
        likelihood_table={
            "400": {"H1": 0.01, "H2": 0.99},
            "200": {"H1": 0.99, "H2": 0.01}
        },
        cost_estimate=0.002,
        risk_score=0.0,
        rationale="Probes the live API with the legacy header to verify rejection code."
    )

st.subheader("Research Question")
st.info(query)

if st.button("🚀 Execute Epistemic Agent Loop", type="primary"):
    agent = EpistemicAgent(tau_stop=tau_stop, lambda_info=lambda_info)
    with st.spinner("Analyzing web topology, calculating entropy, and evaluating causal probes..."):
        response = agent.run(
            query=query,
            initial_hypotheses=hypotheses,
            raw_documents=raw_docs,
            custom_probes=[custom_probe]
        )

    col1, col2, col3 = st.columns([1, 1, 1])

    with col1:
        st.subheader("1. Provenance DAG & Sources")
        st.metric("Total Scraped Documents", response.total_sources_scraped)
        st.metric("Independent Roots", response.independent_roots_count)
        if response.echo_chamber_pruned:
            st.warning("⚠️ Echo Chamber Detected: Derivative scrapers discounted to zero weight.")
        else:
            st.success("✅ Clean Source Topology.")

        st.markdown("**Ingested Documents:**")
        for doc in raw_docs:
            st.write(f"- **{doc['domain']}** (Auth: {doc['authoritativeness']}, Copy: {doc.get('is_copy', False)})")

    with col2:
        st.subheader("2. Epistemic Dynamics")
        st.metric("Epistemic Regime", response.epistemic_regime)
        st.metric("Entropy Reduction", f"{response.initial_entropy:.3f} -> {response.final_entropy:.3f} bits")
        st.metric("Final Confidence", f"{response.confidence * 100:.1f}%")

    with col3:
        st.subheader("3. Active Probing Telemetry")
        st.metric("Causal Probes Executed", len(response.probes_executed))
        for p in response.probes_executed:
            st.code(f"Probe: {p['probe_id']}\nEVOI: {p['evoi']:.3f} | EIG: {p['eig']:.3f} bits\nExit Code: {p['exit_code']}\nOutput: {p['stdout'] or p['stderr']}")

    st.markdown("---")
    st.subheader("🎯 Verified Calibrated Output")
    st.success(response.verified_answer)
