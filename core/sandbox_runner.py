"""
Sandboxed execution engine for safe, isolated code execution and HTTP probing.
Supports Python standard library (urllib, subprocess) with optional httpx support.
"""

import os
import subprocess
import tempfile
import time
import urllib.request
import urllib.error
from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class SandboxResult:
    exit_code: int
    stdout: str
    stderr: str
    duration_sec: float
    is_timeout: bool = False
    error_type: Optional[str] = None
    structured_output: Optional[str] = None


def execute_python_script(
    code_str: str,
    timeout_sec: float = 4.0,
    env_vars: Optional[Dict[str, str]] = None
) -> SandboxResult:
    """
    Executes a Python script in an isolated subprocess (`python3 -I`).

    - `-I`: Isolated mode (ignores python environment variables and user site packages).
    - Enforces strict execution timeout.
    - Captures stdout, stderr, and return codes cleanly.
    """
    start_time = time.time()

    with tempfile.NamedTemporaryFile(suffix=".py", mode="w", delete=False) as f:
        f.write(code_str)
        temp_path = f.name

    try:
        env = os.environ.copy()
        if env_vars:
            env.update(env_vars)

        env["EPISTEMIC_SANDBOX"] = "1"

        proc = subprocess.run(
            ["python3", "-I", temp_path],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout_sec,
            env=env
        )
        duration = time.time() - start_time
        return SandboxResult(
            exit_code=proc.returncode,
            stdout=proc.stdout.strip(),
            stderr=proc.stderr.strip(),
            duration_sec=duration,
            is_timeout=False,
            structured_output=proc.stdout.strip()
        )
    except subprocess.TimeoutExpired:
        duration = time.time() - start_time
        return SandboxResult(
            exit_code=-1,
            stdout="",
            stderr="EXECUTION_TIMEOUT: The script exceeded the time limit.",
            duration_sec=duration,
            is_timeout=True,
            error_type="TimeoutExpired"
        )
    except Exception as e:
        duration = time.time() - start_time
        return SandboxResult(
            exit_code=-1,
            stdout="",
            stderr=f"EXECUTION_ERROR: {str(e)}",
            duration_sec=duration,
            is_timeout=False,
            error_type=type(e).__name__
        )
    finally:
        if os.path.exists(temp_path):
            try:
                os.remove(temp_path)
            except OSError:
                pass


def execute_http_probe(
    url: str,
    method: str = "GET",
    headers: Optional[Dict[str, str]] = None,
    payload: Optional[str] = None,
    timeout_sec: float = 3.0
) -> SandboxResult:
    """
    Executes an HTTP probe against an API or web service with safety guardrails.
    Uses standard library urllib with fallback.
    """
    start_time = time.time()
    method = method.upper()

    # Safety Guardrail: Prevent mutation verbs on remote public hosts
    if method in ["DELETE", "PUT", "PATCH"] and "localhost" not in url and "127.0.0.1" not in url:
        return SandboxResult(
            exit_code=-1,
            stdout="",
            stderr=f"SAFETY_VETO: HTTP method '{method}' is prohibited on public endpoints.",
            duration_sec=0.0,
            is_timeout=False,
            error_type="SafetyVeto"
        )

    try:
        req_headers = headers or {"User-Agent": "EpistemicAgentProber/1.0"}
        data = payload.encode("utf-8") if payload else None
        
        req = urllib.request.Request(url, data=data, headers=req_headers, method=method)
        
        with urllib.request.urlopen(req, timeout=timeout_sec) as response:
            status_code = response.status
            body = response.read().decode("utf-8", errors="replace")
            duration = time.time() - start_time
            stdout_data = f"STATUS: {status_code}\nBODY:\n{body[:2000]}"
            return SandboxResult(
                exit_code=0,
                stdout=stdout_data,
                stderr="",
                duration_sec=duration,
                is_timeout=False,
                structured_output=str(status_code)
            )
    except urllib.error.HTTPError as e:
        duration = time.time() - start_time
        body = e.read().decode("utf-8", errors="replace")
        return SandboxResult(
            exit_code=1,
            stdout=f"STATUS: {e.code}\nBODY:\n{body[:2000]}",
            stderr=f"HTTP_ERROR_{e.code}",
            duration_sec=duration,
            is_timeout=False,
            structured_output=str(e.code)
        )
    except urllib.error.URLError as e:
        duration = time.time() - start_time
        return SandboxResult(
            exit_code=-1,
            stdout="",
            stderr=f"NETWORK_ERROR: {str(e.reason)}",
            duration_sec=duration,
            is_timeout=False,
            error_type="URLError"
        )
    except Exception as e:
        duration = time.time() - start_time
        return SandboxResult(
            exit_code=-1,
            stdout="",
            stderr=f"PROBE_ERROR: {str(e)}",
            duration_sec=duration,
            is_timeout=False,
            error_type=type(e).__name__
        )
