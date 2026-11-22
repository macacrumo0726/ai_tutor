#!/usr/bin/env python3
"""HTTP load test for the student chat flow.

Creates temporary users, accepts the current protocol, opens one conversation
per user and sends one question at concurrency levels 1, 3, 5 and 10. It does
not print response contents or credentials; only availability and latency
metrics are saved.
"""
from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request
import uuid
import re
from pathlib import Path


def request(base: str, path: str, method: str = "GET", payload=None, token: str = ""):
    body = None if payload is None else json.dumps(payload).encode()
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = urllib.request.Request(base.rstrip("/") + path, body, headers, method=method)
    with urllib.request.urlopen(req, timeout=90) as response:
        raw = response.read().decode()
        return response.status, json.loads(raw) if raw else {}


def worker(base: str, index: int):
    user = f"load_{uuid.uuid4().hex[:12]}"
    pin = "LoadTest-1234"
    try:
        _, session = request(base, "/api/auth/register", "POST", {"user_id": user, "display_name": "Load Test", "pin": pin})
        token = session["token"]
        _, protocol = request(base, "/api/protocol")
        request(base, "/api/me/protocol/accept", "POST", {"protocol_version": protocol["version"], "accepted": True}, token)
        _, conversation = request(base, "/api/conversations", "POST", {"title": "Load test"}, token)
        started = time.perf_counter()
        # Read SSE bytes directly; the success criterion is a done event and
        # no error event, not a particular wording from the model.
        body = json.dumps({"message": "Ayúdame a factorizar x² - 5x + 6"}).encode()
        req = urllib.request.Request(
            base.rstrip("/") + f"/api/conversations/{conversation['conversation_id']}/messages/stream",
            body,
            {"Content-Type": "application/json", "Authorization": f"Bearer {token}"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as response:
            text = response.read().decode()
            status = response.status
        done = {}
        match = re.search(r"event: done\ndata: (.+?)\n\n", text)
        if match:
            try:
                done = json.loads(match.group(1))
            except json.JSONDecodeError:
                done = {}
        return {"ok": status == 200 and "event: done" in text and "event: error" not in text,
                "status": status, "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "fallback": bool(done.get("fallback_used")) or "instructional_emergency" in text,
                "provider": done.get("model_provider", "unknown"),
                "model": done.get("effective_model", "unknown"), "error": ""}
    except Exception as exc:
        return {"ok": False, "status": 0, "latency_ms": None, "fallback": False,
                "provider": "error", "model": "error", "error": str(exc)[:200]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--levels", nargs="+", type=int, default=[1, 3, 5, 10])
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/load_test_chat.json"))
    args = parser.parse_args()
    levels = []
    for concurrency in args.levels:
        started = time.perf_counter()
        with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
            rows = list(pool.map(lambda i: worker(args.base_url, i), range(concurrency)))
        valid_latencies = [row["latency_ms"] for row in rows if row["latency_ms"] is not None]
        levels.append({
            "concurrency": concurrency,
            "requests": len(rows),
            "successful": sum(row["ok"] for row in rows),
            "failed": sum(not row["ok"] for row in rows),
            "fallbacks": sum(row["fallback"] for row in rows),
            "providers": {provider: sum(row.get("provider") == provider for row in rows) for provider in sorted({row.get("provider") for row in rows})},
            "wall_time_ms": round((time.perf_counter() - started) * 1000, 1),
            "p50_latency_ms": round(statistics.median(valid_latencies), 1) if valid_latencies else None,
            "p95_latency_ms": round(sorted(valid_latencies)[max(0, int(len(valid_latencies) * .95) - 1)], 1) if valid_latencies else None,
            "errors": [row["error"] for row in rows if row["error"]],
        })
        print(levels[-1])
    payload = {"description": "HTTP chat load test; one isolated user/conversation per request.", "levels": levels}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")


if __name__ == "__main__":
    main()
