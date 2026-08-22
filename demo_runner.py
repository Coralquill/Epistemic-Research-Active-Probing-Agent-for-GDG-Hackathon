"""
CLI Demonstration Runner: Executes end-to-end benchmark test cases demonstrating
echo-chamber resilience, contradiction resolution, and active sandboxed probing.
"""

import sys
from core.belief_state import DigitalProbe
from core.orchestrator import EpistemicAgent

try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    USE_RICH = True
    console = Console()
except ImportError:
    USE_RICH = False


def print_header(title: str):
    if USE_RICH:
        console.print(f"\n[bold cyan]{title}[/bold cyan]")
    else:
        print("\n" + "=" * 70)
        print(f"  {title}")
        print("=" * 70)


def display_agent_response(resp):
    if USE_RICH:
        table = Table(title="[bold green]Epistemic Agent Audit Trace[/bold green]")
        table.add_column("Metric", style="cyan", no_wrap=True)
        table.add_column("Value", style="magenta")

        table.add_row("Question", resp.query)
        table.add_row("Epistemic Regime", resp.epistemic_regime)
        table.add_row("Entropy Delta", f"{resp.initial_entropy:.3f} bits -> {resp.final_entropy:.3f} bits")
        table.add_row("Scraped vs Root Sources", f"{resp.total_sources_scraped} scraped, {resp.independent_roots_count} independent roots")
        table.add_row("Echo Chamber Pruned?", "YES (Scrapers Discounted)" if resp.echo_chamber_pruned else "NO")
        table.add_row("Active Probes Executed", str(len(resp.probes_executed)))
        table.add_row("Confidence", f"{resp.confidence * 100:.1f}%")

        console.print(table)
        console.print(Panel(resp.verified_answer, title="[bold yellow]Agent Final Output[/bold yellow]", border_style="green"))
    else:
        print("\n--- [EPISTEMIC AGENT AUDIT TRACE] ---")
        print(f"Question:                {resp.query}")
        print(f"Epistemic Regime:        {resp.epistemic_regime}")
        print(f"Entropy Delta:           {resp.initial_entropy:.3f} bits -> {resp.final_entropy:.3f} bits")
        print(f"Scraped vs Root Sources: {resp.total_sources_scraped} scraped, {resp.independent_roots_count} independent roots")
        print(f"Echo Chamber Pruned:     {'YES (Scrapers Discounted)' if resp.echo_chamber_pruned else 'NO'}")
        print(f"Active Probes Executed:  {len(resp.probes_executed)}")
        print(f"Final Confidence:        {resp.confidence * 100:.1f}%")
        print("-" * 50)
        print(f"AGENT FINAL OUTPUT:\n{resp.verified_answer}")
        print("-" * 50)


def run_benchmark_1_pydantic_assertion():
    """
    Benchmark 1: Library Invariant Verification
    Question: In Pydantic v2, does `Field(regex='...')` still work as a compatibility alias?
    """
    print_header("BENCHMARK 1: Software Invariant Verification (Pydantic v2 Regex)")

    query = "Does Pydantic v2 support Field(regex='^[a-z]+$') via backward compatibility, or does it throw an error in favor of pattern=?"

    hypotheses = [
        {"id": "H1", "statement": "Field(regex=...) is supported via backward compatibility alias in Pydantic v2."},
        {"id": "H2", "statement": "Field(regex=...) is completely removed and raises an error; pattern= must be used."}
    ]

    raw_docs = [
        {
            "id": "doc_old_tutorial",
            "domain": "legacy-py-guide.dev",
            "authoritativeness": 0.4,
            "claims": [
                {"quote": "Pydantic v2 still accepts regex kwarg.", "assertion": "Field(regex) works", "supports_hypo": "H1", "weight": 0.8}
            ]
        },
        {
            "id": "doc_migration_guide",
            "domain": "docs.pydantic.dev",
            "authoritativeness": 0.95,
            "claims": [
                {"quote": "regex argument is removed in v2 in favor of pattern.", "assertion": "Field(regex) raises error", "supports_hypo": "H2", "weight": 0.95}
            ]
        },
        {
            "id": "doc_scraper_blog",
            "domain": "ai-python-scraps.io",
            "authoritativeness": 0.2,
            "cites": ["doc_old_tutorial"],
            "is_copy": True,
            "claims": [
                {"quote": "Pydantic v2 still accepts regex kwarg.", "assertion": "Field(regex) works", "supports_hypo": "H1", "weight": 0.8}
            ]
        }
    ]

    # Pre-synthesized discriminative probe
    probe_code = """
try:
    from pydantic import BaseModel, Field
    class TestModel(BaseModel):
        code: str = Field(regex="^[a-z]+$")
    print("OUTCOME:SUCCESS_ALIAS_WORKS")
except Exception as e:
    print(f"OUTCOME:EXCEPTION_{type(e).__name__}")
"""
    pydantic_probe = DigitalProbe(
        id="probe_pydantic_regex",
        target_environment="PYTHON_SUBPROCESS",
        code_or_payload=probe_code,
        expected_outcomes={
            "SUCCESS_ALIAS_WORKS": "H1",
            "EXCEPTION": "H2"
        },
        likelihood_table={
            "OUTCOME:SUCCESS_ALIAS_WORKS": {"H1": 0.99, "H2": 0.01},
            "OUTCOME:EXCEPTION": {"H1": 0.01, "H2": 0.99}
        },
        cost_estimate=0.001,
        risk_score=0.0,
        rationale="Executes dynamic model definition in isolated Python runtime to verify syntax rejection."
    )

    agent = EpistemicAgent(tau_stop=0.15)
    response = agent.run(
        query=query,
        initial_hypotheses=hypotheses,
        raw_documents=raw_docs,
        custom_probes=[pydantic_probe]
    )

    display_agent_response(response)


def run_benchmark_2_echo_chamber_audit():
    """
    Benchmark 2: Echo-Chamber Resilience
    Question: Resolving claim when 4 scraper blogs contradict 1 official source.
    """
    print_header("BENCHMARK 2: Echo-Chamber Scraper De-Duplication (SQLite UPSERT)")

    query = "Does SQLite 3.35.0 support RETURNING clauses on UPSERT statements?"

    hypotheses = [
        {"id": "H1", "statement": "SQLite 3.35.0 supports RETURNING on UPSERT."},
        {"id": "H2", "statement": "SQLite 3.35.0 disallows RETURNING on UPSERT; full support required SQLite 3.38.0."}
    ]

    # 4 Scraper blogs copying 1 bad source vs 1 official changelog
    raw_docs = [
        {
            "id": "official_changelog",
            "domain": "sqlite.org",
            "authoritativeness": 0.99,
            "claims": [
                {"quote": "UPSERT RETURNING was fixed in 3.38.0", "assertion": "UPSERT RETURNING fails on 3.35", "supports_hypo": "H2", "weight": 0.99}
            ]
        },
        {
            "id": "flawed_blog_root",
            "domain": "random-medium-post.com",
            "authoritativeness": 0.35,
            "claims": [
                {"quote": "RETURNING works on everything in 3.35!", "assertion": "Works everywhere", "supports_hypo": "H1", "weight": 0.5}
            ]
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

    probe_sqlite = DigitalProbe(
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
        expected_outcomes={
            "UPSERT_RETURNING_SUPPORTED": "H1",
            "UPSERT_RETURNING_ERROR": "H2"
        },
        likelihood_table={
            "OUTCOME:UPSERT_RETURNING_SUPPORTED": {"H1": 0.99, "H2": 0.01},
            "OUTCOME:UPSERT_RETURNING_ERROR": {"H1": 0.01, "H2": 0.99}
        },
        cost_estimate=0.001,
        risk_score=0.0,
        rationale="Executes live SQLite DDL & DML to verify UPSERT RETURNING syntax support."
    )

    agent = EpistemicAgent(tau_stop=0.15)
    response = agent.run(
        query=query,
        initial_hypotheses=hypotheses,
        raw_documents=raw_docs,
        custom_probes=[probe_sqlite]
    )

    display_agent_response(response)


if __name__ == "__main__":
    if USE_RICH:
        console.print("[bold yellow]Running Epistemic Research Agent Demonstration Benchmarks...[/bold yellow]")
    else:
        print("Running Epistemic Research Agent Demonstration Benchmarks...")
    run_benchmark_1_pydantic_assertion()
    run_benchmark_2_echo_chamber_audit()
