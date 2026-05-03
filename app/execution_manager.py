from __future__ import annotations

import ast
import subprocess
import tempfile
import threading
from dataclasses import dataclass
from pathlib import Path

from .database import save_execution


MAX_CONCURRENT_EXECUTIONS = 2
EXECUTION_TIMEOUT_SECONDS = 5
DOCKER_IMAGE = "python:3.11-slim"

_execution_slots = threading.BoundedSemaphore(MAX_CONCURRENT_EXECUTIONS)


class CodeValidationError(ValueError):
    pass


@dataclass(frozen=True)
class ExecutionResult:
    stdout: str
    stderr: str
    exit_code: int
    execution_id: int | None = None

    def as_dict(self) -> dict:
        return {
            "stdout": self.stdout,
            "stderr": self.stderr,
            "exit_code": self.exit_code,
            "execution_id": self.execution_id,
        }


FORBIDDEN_IMPORTS = {
    "ctypes",
    "multiprocessing",
    "os",
    "pathlib",
    "pty",
    "shutil",
    "socket",
    "subprocess",
    "sys",
}

FORBIDDEN_CALLS = {
    "eval",
    "exec",
    "open",
    "__import__",
    "compile",
    "input",
}

FORBIDDEN_ATTRIBUTES = {
    "system",
    "popen",
    "spawn",
    "fork",
    "remove",
    "unlink",
    "rmdir",
    "rename",
    "replace",
}


def validate_python(code: str) -> None:
    if not code.strip():
        raise CodeValidationError("code must not be empty")
    if len(code) > 20_000:
        raise CodeValidationError("code is too large")

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        raise CodeValidationError(f"syntax error: {exc.msg}") from exc

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                root_name = alias.name.split(".", 1)[0]
                if root_name in FORBIDDEN_IMPORTS:
                    raise CodeValidationError(f"forbidden import: {root_name}")
        elif isinstance(node, ast.ImportFrom):
            root_name = (node.module or "").split(".", 1)[0]
            if root_name in FORBIDDEN_IMPORTS:
                raise CodeValidationError(f"forbidden import: {root_name}")
        elif isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                raise CodeValidationError(f"forbidden call: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRIBUTES:
                raise CodeValidationError(f"forbidden attribute call: {node.func.attr}")


def execute_python(code: str) -> dict:
    try:
        validate_python(code)
    except CodeValidationError as exc:
        stderr = str(exc)
        execution_id = save_execution(code, "", stderr, 2)
        return ExecutionResult("", stderr, 2, execution_id).as_dict()

    acquired = _execution_slots.acquire(blocking=False)
    if not acquired:
        stderr = "too many concurrent executions"
        execution_id = save_execution(code, "", stderr, 429)
        return ExecutionResult("", stderr, 429, execution_id).as_dict()

    try:
        result = _execute_python_in_docker(code)
    finally:
        _execution_slots.release()

    execution_id = save_execution(code, result.stdout, result.stderr, result.exit_code)
    return ExecutionResult(result.stdout, result.stderr, result.exit_code, execution_id).as_dict()


def _execute_python_in_docker(code: str) -> ExecutionResult:
    with tempfile.TemporaryDirectory(prefix="qwen-agent-") as tmpdir:
        script_path = Path(tmpdir) / "main.py"
        script_path.write_text(code, encoding="utf-8")
        mount_source = str(script_path.resolve())
        command = [
            "docker",
            "run",
            "--rm",
            "--network",
            "none",
            "--memory",
            "512m",
            "--cpus",
            "1",
            "--pids-limit",
            "100",
            "--read-only",
            "--security-opt",
            "no-new-privileges",
            "--tmpfs",
            "/tmp:rw,nosuid,nodev,size=64m",
            "-v",
            f"{mount_source}:/tmp/main.py:ro",
            DOCKER_IMAGE,
            "python",
            "/tmp/main.py",
        ]
        try:
            completed = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=EXECUTION_TIMEOUT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired as exc:
            return ExecutionResult(
                exc.stdout or "",
                (exc.stderr or "") + "\nexecution timed out",
                124,
            )
        except FileNotFoundError:
            return ExecutionResult("", "docker command not found", 127)

        return ExecutionResult(
            completed.stdout,
            completed.stderr,
            completed.returncode,
        )
