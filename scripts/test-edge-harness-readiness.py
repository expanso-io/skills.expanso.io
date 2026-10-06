# /// script
# requires-python = ">=3.11"
# dependencies = ["pyyaml", "requests"]
# ///
"""Regress the Edge harness startup ordering that caused early job deletion."""

from __future__ import annotations

import copy
import importlib.util
import json
import socket
import sys
import tempfile
from pathlib import Path
from types import SimpleNamespace
from unittest import mock


ROOT = Path(__file__).resolve().parents[1]


def load_module(name: str, path: Path):
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


recipes = load_module("readiness_recipes", ROOT / "scripts/test-recipes.py")
skills = load_module("readiness_skills", ROOT / "scripts/test-skills.py")
regressions = load_module(
    "readiness_regressions", ROOT / "scripts/test-review-regressions.py"
)


def cli_result(payload, returncode: int = 0):
    return SimpleNamespace(
        returncode=returncode,
        stdout=json.dumps(payload),
        stderr="",
    )


def check_pending_then_running(module) -> None:
    states = iter(["pending", "running"])
    commands: list[list[str]] = []

    def run(command, **_kwargs):
        commands.append(command)
        if command[1:3] == ["job", "describe"]:
            return cli_result({"id": "job-123"})
        assert command[1:3] == ["execution", "list"], command
        state = next(states)
        return cli_result(
            [{"status": {"observed_state": {"state_type": state}}}]
        )

    with (
        mock.patch.object(module.subprocess, "run", side_effect=run),
        mock.patch.object(module.time, "monotonic", return_value=0.0),
        mock.patch.object(module.time, "sleep"),
    ):
        ready, reason = module.wait_for_execution_running(
            "expanso-cli", "fixture-job", "http://127.0.0.1:1", timeout=45
        )

    assert ready and reason == "running", (ready, reason)
    assert [command[1:3] for command in commands] == [
        ["job", "describe"],
        ["execution", "list"],
        ["execution", "list"],
    ], commands

    if module is recipes:
        commands.clear()
        states = iter(["running"])
        with (
            mock.patch.object(module.subprocess, "run", side_effect=run),
            mock.patch.object(module.time, "monotonic", return_value=0.0),
        ):
            ready, reason = module.wait_for_execution_running(
                "expanso-cli",
                "fixture-job",
                "http://127.0.0.1:1",
                timeout=45,
                namespace="production",
            )
        assert ready and reason == "running", (ready, reason)
        assert commands[0][-2:] == ["--namespace", "production"], commands


def check_terminal_and_timeout(module) -> None:
    def terminal_run(command, **_kwargs):
        if command[1:3] == ["job", "describe"]:
            return cli_result({"id": "job-123"})
        return cli_result(
            [{"status": {"observed_state": {"state_type": "failed"}}}]
        )

    with (
        mock.patch.object(module.subprocess, "run", side_effect=terminal_run),
        mock.patch.object(module.time, "monotonic", return_value=0.0),
    ):
        ready, reason = module.wait_for_execution_running(
            "expanso-cli", "fixture-job", "http://127.0.0.1:1", timeout=45
        )
    assert not ready and reason == "execution reached terminal state failed"

    clock = [0.0]

    def monotonic():
        return clock[0]

    def sleep(duration):
        clock[0] += duration

    def pending_run(command, **_kwargs):
        if command[1:3] == ["job", "describe"]:
            return cli_result({"id": "job-123"})
        return cli_result(
            [{"status": {"observed_state": {"state_type": "pending"}}}]
        )

    with (
        mock.patch.object(module.subprocess, "run", side_effect=pending_run),
        mock.patch.object(module.time, "monotonic", side_effect=monotonic),
        mock.patch.object(module.time, "sleep", side_effect=sleep),
    ):
        ready, reason = module.wait_for_execution_running(
            "expanso-cli", "fixture-job", "http://127.0.0.1:1", timeout=0.4
        )
    assert not ready, (ready, reason)
    assert reason == (
        "execution did not reach running within 0.4s (last state: pending)"
    ), reason
    assert clock[0] >= 0.4, clock


def check_taken_port_is_skipped(module, allocator_name: str) -> None:
    taken = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    taken.bind(("127.0.0.1", 0))
    taken.listen()
    taken_port = taken.getsockname()[1]
    available = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    available.bind(("127.0.0.1", 0))
    available_port = available.getsockname()[1]
    available.close()
    previous_locks = len(module._PORT_LOCKS)
    try:
        with mock.patch.object(
            module,
            "port_candidates",
            return_value=iter([taken_port, available_port]),
        ):
            selected = getattr(module, allocator_name)()
        assert selected == available_port, (taken_port, available_port, selected)
    finally:
        taken.close()
        for lock_handle in module._PORT_LOCKS[previous_locks:]:
            lock_handle.close()
        del module._PORT_LOCKS[previous_locks:]


def check_bind_collision_retries_only_matching_error(directory: Path) -> None:
    edge_log = directory / "edge.log"
    edge_log.write_text("")
    pipeline = {
        "name": "fixture",
        "type": "pipeline",
        "config": {
            "input": {
                "http_server": {
                    "address": "0.0.0.0:${PORT:-8080}",
                    "path": "/test",
                    "allowed_verbs": ["POST"],
                }
            },
            "pipeline": {"processors": []},
            "output": {"sync_response": {}},
        },
    }
    deploys = [0]

    def run(command, **_kwargs):
        if command[1:3] == ["job", "deploy"]:
            deploys[0] += 1
            if deploys[0] == 1:
                with edge_log.open("a") as log_handle:
                    log_handle.write(
                        "ERR failed to bind to address 0.0.0.0:20001: "
                        "listen tcp 0.0.0.0:20001: bind: address already in use\n"
                    )
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    response = SimpleNamespace(status_code=200, text="{}", json=lambda: {})
    with (
        mock.patch.object(
            skills,
            "load_yaml",
            side_effect=lambda _path: copy.deepcopy(pipeline),
        ),
        mock.patch.object(skills, "find_free_port", side_effect=[20001, 20002]),
        mock.patch.object(
            skills,
            "wait_for_execution_running",
            side_effect=[(False, "degraded"), (True, "running")],
        ),
        mock.patch.object(skills, "wait_for_port", return_value=True),
        mock.patch.object(skills.subprocess, "run", side_effect=run),
        mock.patch.object(skills.requests, "request", return_value=response),
        mock.patch.object(skills.time, "sleep"),
    ):
        result, fatal = skills.execute_test(
            skill_name="fixture",
            pipeline_path=directory / "pipeline-mcp.yaml",
            variant="mcp",
            input_value="{}",
            payload={},
            expected={},
            api_url="http://127.0.0.1:1",
            expanso_cli="expanso-cli",
            mock_openai=False,
            run_dir=directory,
            edge_log=edge_log,
        )
    assert not fatal, result
    assert result["status"] == "passed", result
    assert result["listener_bind_retries"] == 1, result
    assert result["listener_ports"] == [20001, 20002], result
    assert deploys[0] == 2, deploys

    edge_log.write_text("")
    deploys[0] = 0

    def other_failure(command, **_kwargs):
        if command[1:3] == ["job", "deploy"]:
            deploys[0] += 1
            with edge_log.open("a") as log_handle:
                log_handle.write("ERR processor configuration failed\n")
        return SimpleNamespace(returncode=0, stdout="", stderr="")

    with (
        mock.patch.object(
            skills,
            "load_yaml",
            side_effect=lambda _path: copy.deepcopy(pipeline),
        ),
        mock.patch.object(skills, "find_free_port", return_value=20003),
        mock.patch.object(
            skills,
            "wait_for_execution_running",
            return_value=(False, "degraded"),
        ),
        mock.patch.object(skills.subprocess, "run", side_effect=other_failure),
    ):
        result, fatal = skills.execute_test(
            skill_name="fixture",
            pipeline_path=directory / "pipeline-mcp.yaml",
            variant="mcp",
            input_value="{}",
            payload={},
            expected={},
            api_url="http://127.0.0.1:1",
            expanso_cli="expanso-cli",
            mock_openai=False,
            run_dir=directory,
            edge_log=edge_log,
        )
    assert not fatal, result
    assert result["status"] == "failed", result
    assert result["listener_bind_retries"] == 0, result
    assert result["listener_ports"] == [20003], result
    assert deploys[0] == 1, deploys


def suite_without_edge(directory: Path):
    suite = regressions.Suite.__new__(regressions.Suite)
    suite.directory = directory
    suite.api = "http://127.0.0.1:1"
    suite.count = 0
    return suite


def check_suite_waits_before_request(directory: Path) -> None:
    events: list[str] = []

    def deploy(*_args):
        events.append("deploy")
        return True, "regression-1", "deployed"

    def wait_running(*_args, timeout):
        assert timeout == 45
        events.append("running")
        return True, "running"

    def wait_port(*_args, **_kwargs):
        events.append("port")
        return True

    def request(*_args, **_kwargs):
        events.append("request")
        return SimpleNamespace(content=b"{}", json=lambda: {})

    def delete(*_args):
        events.append("delete")

    regressions.CLI = "expanso-cli"
    with (
        mock.patch.object(regressions.runner, "deploy", side_effect=deploy),
        mock.patch.object(
            regressions.runner,
            "wait_for_execution_running",
            side_effect=wait_running,
        ),
        mock.patch.object(
            regressions.runner, "wait_for_port", side_effect=wait_port
        ),
        mock.patch.object(regressions.requests, "post", side_effect=request),
        mock.patch.object(regressions.runner, "delete_job", side_effect=delete),
    ):
        result = suite_without_edge(directory).execute(
            {"pipeline": {"processors": []}}, {"fixture": True}
        )

    assert result == {}, result
    assert events == ["deploy", "running", "port", "request", "delete"], events


def check_suite_cleans_up_after_readiness_failure(directory: Path) -> None:
    events: list[str] = []

    def deploy(*_args):
        events.append("deploy")
        return True, "regression-1", "deployed"

    def wait_running(*_args, timeout):
        assert timeout == 45
        events.append("readiness-timeout")
        return False, "execution did not reach running within 45s"

    def unexpected(*_args, **_kwargs):
        events.append("unexpected-request")
        raise AssertionError("request attempted before execution became running")

    def delete(*_args):
        events.append("delete")

    regressions.CLI = "expanso-cli"
    with (
        mock.patch.object(regressions.runner, "deploy", side_effect=deploy),
        mock.patch.object(
            regressions.runner,
            "wait_for_execution_running",
            side_effect=wait_running,
        ),
        mock.patch.object(regressions.runner, "wait_for_port", side_effect=unexpected),
        mock.patch.object(regressions.requests, "post", side_effect=unexpected),
        mock.patch.object(regressions.runner, "delete_job", side_effect=delete),
    ):
        try:
            suite_without_edge(directory).execute(
                {"pipeline": {"processors": []}}, {"fixture": True}
            )
        except AssertionError as exc:
            assert "within 45s" in str(exc), exc
        else:
            raise AssertionError("readiness failure did not fail the harness")

    assert events == ["deploy", "readiness-timeout", "delete"], events


def main() -> int:
    for module in (recipes, skills):
        check_pending_then_running(module)
        check_terminal_and_timeout(module)
    check_taken_port_is_skipped(recipes, "free_port")
    check_taken_port_is_skipped(skills, "find_free_port")

    conformance = ROOT / ".conformance"
    conformance.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(
        prefix="edge-readiness-", dir=conformance
    ) as temporary:
        directory = Path(temporary)
        check_bind_collision_retries_only_matching_error(directory)
        check_suite_waits_before_request(directory)
        check_suite_cleans_up_after_readiness_failure(directory)

    print(
        "PASS Edge harness waits for running and delays cleanup until readiness resolves"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
