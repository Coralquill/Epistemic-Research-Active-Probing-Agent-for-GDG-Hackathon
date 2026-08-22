"""
FastAPI Server for Epistemic Research Agent.
Provides REST APIs, WebSocket real-time streaming, and serves the interactive frontend dashboard.
"""

import json
import os
from typing import Dict, List, Optional
from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from core.orchestrator import EpistemicAgent
from core.streaming_agent import StreamingEpistemicAgent
from core.sandbox_runner import execute_python_script, execute_http_probe

app = FastAPI(
    title="Epistemic Research & Active Probing Agent",
    description="Full-stack AI research agent with real-time provenance tracking, entropy measurement, and active sandboxed probing."
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BENCHMARKS_FILE = os.path.join(os.path.dirname(__file__), "demo_benchmarks.json")
FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "frontend")


def load_benchmarks() -> List[Dict]:
    if os.path.exists(BENCHMARKS_FILE):
        with open(BENCHMARKS_FILE, "r") as f:
            return json.load(f)
    return []


# ============================================================================
# Mock API Endpoints for Live Probing Demonstrations
# ============================================================================

@app.get("/api/v1/secure-data")
def mock_secure_endpoint(authorization: Optional[str] = None):
    """Live API Endpoint simulating modern Bearer token auth vs legacy X-API-Key."""
    if authorization and authorization.startswith("Bearer "):
        return {
            "status": "SUCCESS",
            "message": "Authenticated successfully using Bearer token.",
            "data": [10, 20, 30, 40]
        }
    raise HTTPException(
        status_code=400,
        detail="DEPRECATED_AUTH_METHOD: 'X-API-Key' is removed. Use 'Authorization: Bearer <token>'."
    )


# ============================================================================
# REST API Routes
# ============================================================================

@app.get("/api/benchmarks")
def get_benchmarks():
    """Returns the list of pre-configured demonstration benchmarks."""
    return load_benchmarks()


class ResearchRequest(BaseModel):
    query: str
    hypotheses: List[Dict[str, str]]
    raw_docs: List[Dict]
    probes: Optional[List[Dict]] = None
    tau_stop: float = 0.20
    lambda_info: float = 1.5


@app.post("/api/research/run")
def run_research_synchronous(req: ResearchRequest):
    """Runs a complete research cycle synchronously."""
    agent = EpistemicAgent(tau_stop=req.tau_stop, lambda_info=req.lambda_info)
    # Convert probes if supplied
    from core.belief_state import DigitalProbe
    probes_list = []
    if req.probes:
        for p in req.probes:
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
    response = agent.run(
        query=req.query,
        initial_hypotheses=req.hypotheses,
        raw_documents=req.raw_docs,
        custom_probes=probes_list
    )
    from dataclasses import asdict
    return asdict(response)


class SandboxExecRequest(BaseModel):
    code: str
    timeout_sec: float = 3.0


@app.post("/api/sandbox/execute")
def test_sandbox_code(req: SandboxExecRequest):
    """Executes arbitrary Python code in the isolated subprocess sandbox."""
    res = execute_python_script(req.code, timeout_sec=req.timeout_sec)
    from dataclasses import asdict
    return asdict(res)


# ============================================================================
# WebSocket Streaming Route
# ============================================================================

@app.websocket("/ws/run-agent")
async def websocket_run_agent(websocket: WebSocket):
    """
    WebSocket endpoint that receives a research payload and streams
    live lifecycle events, DAG updates, terminal telemetry, and posterior changes.
    """
    await websocket.accept()
    try:
        data = await websocket.receive_json()
        query = data.get("query", "")
        hypotheses = data.get("hypotheses", [])
        raw_docs = data.get("raw_docs", [])
        probes = data.get("probes", [])
        tau_stop = float(data.get("tau_stop", 0.20))
        lambda_info = float(data.get("lambda_info", 1.5))

        streaming_agent = StreamingEpistemicAgent(
            tau_stop=tau_stop,
            lambda_info=lambda_info,
            step_delay_sec=0.5
        )

        async for event in streaming_agent.run_stream(
            query=query,
            initial_hypotheses=hypotheses,
            raw_documents=raw_docs,
            custom_probes=probes
        ):
            await websocket.send_json(event)

    except WebSocketDisconnect:
        pass
    except Exception as e:
        await websocket.send_json({
            "event": "ERROR",
            "message": f"Server processing error: {str(e)}"
        })


# ============================================================================
# Static Files & Frontend Serving
# ============================================================================

if os.path.exists(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

@app.get("/")
def serve_index():
    index_path = os.path.join(FRONTEND_DIR, "index.html")
    if os.path.exists(index_path):
        return FileResponse(index_path)
    return {"message": "Epistemic Agent Server is running. Frontend static files not found."}


if __name__ == "__main__":
    import uvicorn
    print("Starting Epistemic Agent Full-Stack Server at http://127.0.0.1:8000")
    uvicorn.run(app, host="127.0.0.1", port=8000)
