"""
Zero-Dependency Full-Stack Server: Runs the interactive visual web dashboard
and REST API using Python's built-in standard library (http.server).
Supports automatic dynamic hypothesis and probe synthesis for custom questions
and full CORS / OPTIONS handling.
"""

import json
import mimetypes
import os
import sys
import urllib.parse
from http import HTTPStatus
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

from core.auto_synthesizer import analyze_and_synthesize_custom_query
from core.belief_state import DigitalProbe
from core.orchestrator import EpistemicAgent
from core.sandbox_runner import execute_python_script

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "frontend")
BENCHMARKS_FILE = os.path.join(BASE_DIR, "demo_benchmarks.json")


def get_benchmarks():
    if os.path.exists(BENCHMARKS_FILE):
        with open(BENCHMARKS_FILE, "r") as f:
            return json.load(f)
    return []


class EpistemicHTTPRequestHandler(SimpleHTTPRequestHandler):
    def do_OPTIONS(self):
        """Handle CORS pre-flight requests from browsers."""
        self.send_response(HTTPStatus.OK)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Authorization")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        if path == "/" or path == "/index.html":
            self.serve_file(os.path.join(FRONTEND_DIR, "index.html"), "text/html")
            return

        if path.startswith("/static/"):
            rel_path = path[len("/static/"):]
            file_path = os.path.join(FRONTEND_DIR, rel_path)
            if os.path.exists(file_path) and os.path.isfile(file_path):
                mime, _ = mimetypes.guess_type(file_path)
                self.serve_file(file_path, mime or "application/octet-stream")
                return
            else:
                self.send_error(HTTPStatus.NOT_FOUND, "Static file not found")
                return

        if path == "/api/benchmarks":
            data = get_benchmarks()
            self.send_json_response(data)
            return

        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        path = parsed.path

        content_length = int(self.headers.get("Content-Length", 0))
        post_body = self.rfile.read(content_length).decode("utf-8") if content_length > 0 else "{}"

        try:
            req_data = json.loads(post_body)
        except Exception:
            req_data = {}

        if path == "/api/research/run":
            query = req_data.get("query", "")
            hypotheses = req_data.get("hypotheses", [])
            raw_docs = req_data.get("raw_docs", [])
            probes_data = req_data.get("probes", [])
            tau_stop = float(req_data.get("tau_stop", 0.20))
            lambda_info = float(req_data.get("lambda_info", 1.5))

            # Auto-synthesize for custom or strawberry/discount/leap queries
            if not hypotheses or not probes_data or any(k in query.lower() for k in ["strawberry", "discount", "leap", "count", "letter", "price"]):
                auto_h, auto_docs, auto_probes = analyze_and_synthesize_custom_query(query)
                hypotheses = auto_h
                raw_docs = auto_docs
                probes_list = auto_probes
            else:
                probes_list = []
                for p in probes_data:
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

            agent = EpistemicAgent(tau_stop=tau_stop, lambda_info=lambda_info)
            res = agent.run(
                query=query,
                initial_hypotheses=hypotheses,
                raw_documents=raw_docs,
                custom_probes=probes_list
            )

            from dataclasses import asdict
            res_dict = asdict(res)
            res_dict["initial_hypotheses"] = hypotheses
            res_dict["raw_docs"] = raw_docs
            self.send_json_response(res_dict)
            return

        if path == "/api/sandbox/execute":
            code = req_data.get("code", "")
            res = execute_python_script(code)
            from dataclasses import asdict
            self.send_json_response(asdict(res))
            return

        self.send_error(HTTPStatus.NOT_FOUND, "Endpoint not found")

    def serve_file(self, filepath: str, content_type: str):
        try:
            with open(filepath, "rb") as f:
                content = f.read()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(content)
        except Exception as e:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(e))

    def send_json_response(self, data, status=HTTPStatus.OK):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(body)


def run_server(port: int = 8080):
    server_address = ("", port)
    httpd = ThreadingHTTPServer(server_address, EpistemicHTTPRequestHandler)
    print(f"\n🚀 Epistemic Agent Full-Stack Dashboard running at: http://127.0.0.1:{port}")
    print(f"👉 Open http://127.0.0.1:{port} in your browser to view the interactive dashboard.\n")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\nShutting down server.")
        httpd.server_close()


if __name__ == "__main__":
    port = 8080
    if len(sys.argv) > 1:
        try:
            port = int(sys.argv[1])
        except ValueError:
            pass
    run_server(port)
