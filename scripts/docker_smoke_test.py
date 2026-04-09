#!/usr/bin/env python3
"""End-to-end Docker smoke checks for the Zydus predictive maintenance stack.

Default behavior is read-only for business state. Mutation endpoint checks are
skipped unless --allow-mutations is provided.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from dataclasses import dataclass
from typing import Callable
from urllib import error, parse, request


class SkipCheck(Exception):
    """Raised to mark a check as intentionally skipped."""


@dataclass
class Context:
    compose_file: str
    base_url: str
    airflow_url: str
    mlflow_url: str
    allow_mutations: bool
    username: str
    password: str
    token: str | None = None
    equipment_id: int | None = None
    alert_id: int | None = None
    workorder_id: int | None = None


def run_cmd(cmd: list[str], timeout: int = 120, stdin: str | None = None) -> str:
    result = subprocess.run(
        cmd,
        input=stdin,
        text=True,
        capture_output=True,
        timeout=timeout,
    )
    if result.returncode != 0:
        stderr = result.stderr.strip()
        stdout = result.stdout.strip()
        details = stderr or stdout or "no output"
        raise RuntimeError(f"command failed ({' '.join(cmd)}): {details}")
    return result.stdout.strip()


def http_call(
    method: str,
    url: str,
    token: str | None = None,
    form: dict | None = None,
    json_body: dict | None = None,
    timeout: int = 20,
) -> tuple[int, str]:
    headers: dict[str, str] = {}
    payload = None

    if token:
        headers["Authorization"] = f"Bearer {token}"

    if form is not None:
        payload = parse.urlencode(form).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"
    elif json_body is not None:
        payload = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"

    req = request.Request(url=url, data=payload, headers=headers, method=method)
    try:
        with request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8", errors="replace")
    except error.HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def expect_status(status: int, expected: tuple[int, ...], body: str) -> None:
    if status not in expected:
        snippet = body[:220].replace("\n", " ")
        raise RuntimeError(f"expected {expected}, got {status}; body={snippet}")


def expect_json(body: str):
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"invalid JSON response: {exc}") from exc


def run_checks(ctx: Context) -> int:
    failures: list[str] = []
    skips = 0

    def check(name: str, func: Callable[[], str]) -> None:
        nonlocal skips
        try:
            details = func()
            print(f"[PASS] {name}: {details}")
        except SkipCheck as exc:
            skips += 1
            print(f"[SKIP] {name}: {exc}")
        except Exception as exc:  # pragma: no cover - integration behavior only
            failures.append(f"{name}: {exc}")
            print(f"[FAIL] {name}: {exc}")

    def check_compose_health() -> str:
        output = run_cmd(["docker", "compose", "-f", ctx.compose_file, "ps"])
        lower = output.lower()
        if "unhealthy" in lower:
            raise RuntimeError("one or more compose services are unhealthy")
        required_markers = [
            "zydus-backend",
            "zydus-kafka",
            "zydus-postgres",
            "zydus-redis",
            "zydus-airflow",
            "zydus-mlflow",
            "zydus-zookeeper",
        ]
        missing = [name for name in required_markers if name not in output]
        if missing:
            raise RuntimeError(f"missing services in compose output: {missing}")
        return "all required services listed and no unhealthy state found"

    def check_health_endpoint() -> str:
        status, body = http_call("GET", f"{ctx.base_url}/health")
        expect_status(status, (200,), body)
        payload = expect_json(body)
        if payload.get("status") != "ok":
            raise RuntimeError(f"unexpected health payload: {payload}")
        return json.dumps(payload)

    def check_root_endpoint() -> str:
        status, body = http_call("GET", f"{ctx.base_url}/")
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return payload.get("message", "root endpoint ok")

    def check_login() -> str:
        status, body = http_call(
            "POST",
            f"{ctx.base_url}/auth/login",
            form={"username": ctx.username, "password": ctx.password},
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        token = payload.get("access_token")
        if not token:
            raise RuntimeError("login response missing access_token")
        ctx.token = token
        return f"role={payload.get('role')}"

    def check_me() -> str:
        assert ctx.token is not None
        status, body = http_call("GET", f"{ctx.base_url}/auth/me", token=ctx.token)
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return f"user={payload.get('username')} role={payload.get('role')}"

    def check_equipment() -> str:
        assert ctx.token is not None
        status, body = http_call("GET", f"{ctx.base_url}/api/equipment", token=ctx.token)
        expect_status(status, (200,), body)
        payload = expect_json(body)
        if not isinstance(payload, list) or not payload:
            raise RuntimeError("equipment payload is empty")
        ctx.equipment_id = payload[0]["id"]
        return f"equipment_count={len(payload)} first_id={ctx.equipment_id}"

    def check_equipment_detail() -> str:
        assert ctx.token is not None and ctx.equipment_id is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/equipment/{ctx.equipment_id}",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return f"name={payload.get('name')} health={payload.get('current_health')}"

    def check_equipment_sensors() -> str:
        assert ctx.token is not None and ctx.equipment_id is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/equipment/{ctx.equipment_id}/sensors",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return f"sensor_groups={len(payload.keys())}"

    def check_equipment_prediction() -> str:
        assert ctx.token is not None and ctx.equipment_id is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/equipment/{ctx.equipment_id}/prediction",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return f"failure_probability={payload.get('failure_probability', 'n/a')}"

    def check_equipment_history() -> str:
        assert ctx.token is not None and ctx.equipment_id is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/equipment/{ctx.equipment_id}/history",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return f"history_points={len(payload)}"

    def check_dashboard() -> str:
        assert ctx.token is not None
        status, body = http_call("GET", f"{ctx.base_url}/api/dashboard/summary", token=ctx.token)
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return (
            "total_equipment="
            f"{payload.get('total_equipment')} avg_health_score={payload.get('avg_health_score')}"
        )

    def check_alerts() -> str:
        assert ctx.token is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/alerts?severity=ALL&status=ALL&page=1&limit=10",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        items = payload.get("items", [])
        if items:
            ctx.alert_id = items[0]["id"]
        return f"alerts_returned={len(items)}"

    def check_viewer_denied_alert_ack() -> str:
        status, body = http_call(
            "POST",
            f"{ctx.base_url}/auth/login",
            form={"username": "viewer1", "password": "view123"},
        )
        expect_status(status, (200,), body)
        viewer_token = expect_json(body).get("access_token")
        if not viewer_token:
            raise RuntimeError("viewer login did not return access_token")

        status, body = http_call(
            "PATCH",
            f"{ctx.base_url}/api/alerts/999999/acknowledge",
            token=viewer_token,
            json_body={},
        )
        expect_status(status, (401,), body)
        payload = expect_json(body)
        detail = payload.get("detail", {})
        if detail.get("message") != "Insufficient permissions":
            raise RuntimeError(f"unexpected permission payload: {payload}")
        return "viewer blocked from acknowledge endpoint"

    def check_acknowledge_alert() -> str:
        if not ctx.allow_mutations:
            raise SkipCheck("read-only mode enabled")
        if ctx.alert_id is None:
            raise SkipCheck("no alert found")
        assert ctx.token is not None
        status, body = http_call(
            "PATCH",
            f"{ctx.base_url}/api/alerts/{ctx.alert_id}/acknowledge",
            token=ctx.token,
            json_body={},
        )
        expect_status(status, (200,), body)
        return f"alert_id={ctx.alert_id} acknowledged"

    def check_workorders() -> str:
        assert ctx.token is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/workorders?status=all",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        if payload:
            ctx.workorder_id = payload[0]["id"]
        return f"workorders_returned={len(payload)}"

    def check_viewer_denied_workorder_complete() -> str:
        status, body = http_call(
            "POST",
            f"{ctx.base_url}/auth/login",
            form={"username": "viewer1", "password": "view123"},
        )
        expect_status(status, (200,), body)
        viewer_token = expect_json(body).get("access_token")
        if not viewer_token:
            raise RuntimeError("viewer login did not return access_token")

        status, body = http_call(
            "PATCH",
            f"{ctx.base_url}/api/workorders/999999/complete",
            token=viewer_token,
            json_body={},
        )
        expect_status(status, (401,), body)
        payload = expect_json(body)
        detail = payload.get("detail", {})
        if detail.get("message") != "Insufficient permissions":
            raise RuntimeError(f"unexpected permission payload: {payload}")
        return "viewer blocked from complete endpoint"

    def check_complete_workorder() -> str:
        if not ctx.allow_mutations:
            raise SkipCheck("read-only mode enabled")
        if ctx.workorder_id is None:
            raise SkipCheck("no workorder found")
        assert ctx.token is not None
        status, body = http_call(
            "PATCH",
            f"{ctx.base_url}/api/workorders/{ctx.workorder_id}/complete",
            token=ctx.token,
            json_body={},
        )
        expect_status(status, (200,), body)
        return f"workorder_id={ctx.workorder_id} completed"

    def check_logs_endpoint() -> str:
        assert ctx.token is not None
        status, body = http_call(
            "GET",
            f"{ctx.base_url}/api/logs?event_type=ALL&limit=20",
            token=ctx.token,
        )
        expect_status(status, (200,), body)
        payload = expect_json(body)
        return f"log_items={payload.get('total')}"

    def check_airflow_health() -> str:
        status, body = http_call("GET", f"{ctx.airflow_url}/health")
        expect_status(status, (200,), body)
        payload = expect_json(body)
        scheduler = payload.get("scheduler", {})
        if scheduler.get("status") != "healthy":
            raise RuntimeError(f"scheduler not healthy: {scheduler}")
        return "scheduler healthy"

    def check_airflow_dag() -> str:
        output = run_cmd(["docker", "exec", "zydus-airflow", "airflow", "dags", "list"])
        if "zydus_ml_etl_pipeline" not in output:
            raise RuntimeError("zydus_ml_etl_pipeline not found")
        return "zydus_ml_etl_pipeline present"

    def check_mlflow_health() -> str:
        status, body = http_call("GET", f"{ctx.mlflow_url}/health")
        expect_status(status, (200,), body)
        return body.strip() or "ok"

    def check_kafka_topics() -> str:
        output = run_cmd(
            [
                "docker",
                "exec",
                "zydus-kafka",
                "kafka-topics",
                "--bootstrap-server",
                "kafka:29092",
                "--list",
            ]
        )
        topic_count = len([line for line in output.splitlines() if line.strip()])
        if topic_count == 0:
            raise RuntimeError("no kafka topics listed")
        return f"topic_count={topic_count}"

    def check_postgres_counts() -> str:
        output = run_cmd(
            [
                "docker",
                "exec",
                "zydus-postgres",
                "psql",
                "-U",
                "zydus_user",
                "-d",
                "zydus_db",
                "-t",
                "-A",
                "-c",
                "SELECT COUNT(*) FROM sensor_readings;",
            ]
        )
        count = int(output.strip())
        if count <= 0:
            raise RuntimeError("sensor_readings has no rows")
        return f"sensor_rows={count}"

    def check_postgres_freshness() -> str:
        output = run_cmd(
            [
                "docker",
                "exec",
                "zydus-postgres",
                "psql",
                "-U",
                "zydus_user",
                "-d",
                "zydus_db",
                "-t",
                "-A",
                "-c",
                "SELECT EXTRACT(EPOCH FROM (NOW() - MAX(timestamp)))::int FROM sensor_readings;",
            ]
        )
        lag_seconds = int(output.strip())
        if lag_seconds > 120:
            raise RuntimeError(f"sensor lag too high: {lag_seconds}s")
        return f"sensor_lag_seconds={lag_seconds}"

    def check_redis() -> str:
        output = run_cmd(["docker", "exec", "zydus-redis", "redis-cli", "PING"])
        if output.strip() != "PONG":
            raise RuntimeError(f"unexpected redis ping output: {output}")
        return output.strip()

    def check_zookeeper() -> str:
        output = run_cmd(
            ["docker", "exec", "zydus-zookeeper", "sh", "-lc", "echo ruok | nc localhost 2181"]
        )
        if "imok" not in output:
            raise RuntimeError(f"unexpected zookeeper output: {output}")
        return output.strip()

    def check_websocket() -> str:
        snippet = (
            "import asyncio, json, websockets\n"
            "async def _main():\n"
            "    async with websockets.connect('ws://localhost:8000/ws/live', open_timeout=10, close_timeout=5) as ws:\n"
            "        msg = await asyncio.wait_for(ws.recv(), timeout=10)\n"
            "        payload = json.loads(msg)\n"
            "        print(payload.get('type', 'unknown'))\n"
            "asyncio.run(_main())\n"
        )
        output = run_cmd(["docker", "exec", "-i", "zydus-backend", "python", "-"], stdin=snippet)
        if "initial_summary" not in output:
            raise RuntimeError(f"unexpected websocket payload marker: {output}")
        return output.strip()

    checks = [
        ("Compose health", check_compose_health),
        ("GET /health", check_health_endpoint),
        ("GET /", check_root_endpoint),
        ("POST /auth/login", check_login),
        ("GET /auth/me", check_me),
        ("GET /api/equipment", check_equipment),
        ("GET /api/equipment/{id}", check_equipment_detail),
        ("GET /api/equipment/{id}/sensors", check_equipment_sensors),
        ("GET /api/equipment/{id}/prediction", check_equipment_prediction),
        ("GET /api/equipment/{id}/history", check_equipment_history),
        ("GET /api/dashboard/summary", check_dashboard),
        ("GET /api/alerts", check_alerts),
        ("RBAC viewer denied /api/alerts/{id}/acknowledge", check_viewer_denied_alert_ack),
        ("PATCH /api/alerts/{id}/acknowledge", check_acknowledge_alert),
        ("GET /api/workorders", check_workorders),
        ("RBAC viewer denied /api/workorders/{id}/complete", check_viewer_denied_workorder_complete),
        ("PATCH /api/workorders/{id}/complete", check_complete_workorder),
        ("GET /api/logs", check_logs_endpoint),
        ("Airflow health", check_airflow_health),
        ("Airflow DAG registration", check_airflow_dag),
        ("MLflow health", check_mlflow_health),
        ("Kafka topics", check_kafka_topics),
        ("Postgres row counts", check_postgres_counts),
        ("Postgres freshness", check_postgres_freshness),
        ("Redis ping", check_redis),
        ("Zookeeper ruok", check_zookeeper),
        ("WebSocket live stream", check_websocket),
    ]

    for name, func in checks:
        check(name, func)

    print("\nSmoke summary")
    print(f"  failures: {len(failures)}")
    print(f"  skipped: {skips}")

    if failures:
        print("\nFailed checks:")
        for item in failures:
            print(f"  - {item}")
        return 1

    return 0


def parse_args() -> Context:
    parser = argparse.ArgumentParser(description="Run docker smoke checks")
    parser.add_argument("--compose-file", default="infra/docker-compose.yml")
    parser.add_argument("--base-url", default="http://localhost:8000")
    parser.add_argument("--airflow-url", default="http://localhost:8080")
    parser.add_argument("--mlflow-url", default="http://localhost:5000")
    parser.add_argument("--username", default="admin")
    parser.add_argument("--password", default="admin123")
    parser.add_argument(
        "--allow-mutations",
        action="store_true",
        help="Enable state-changing endpoint checks for alerts/workorders.",
    )
    args = parser.parse_args()

    return Context(
        compose_file=args.compose_file,
        base_url=args.base_url.rstrip("/"),
        airflow_url=args.airflow_url.rstrip("/"),
        mlflow_url=args.mlflow_url.rstrip("/"),
        allow_mutations=args.allow_mutations,
        username=args.username,
        password=args.password,
    )


def main() -> int:
    ctx = parse_args()
    mode = "mutation-enabled" if ctx.allow_mutations else "read-only"
    print(f"Running docker smoke tests in {mode} mode")
    return run_checks(ctx)


if __name__ == "__main__":
    raise SystemExit(main())
