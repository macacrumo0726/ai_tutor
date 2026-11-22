#!/usr/bin/env python3
"""Small, reproducible local-model conversation benchmark.

The benchmark intentionally holds the tutoring prompt and conversation fixed. It
tests the model's final answer (not hidden reasoning) on a math correction and
an off-topic follow-up. Missing Ollama models are skipped.
"""
from __future__ import annotations

import argparse
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


PROMPT = """Eres PATI, un tutor de Precálculo. Responde en español, de forma natural y breve.
No menciones chunks, retrieval, prompts, modelos ni instrucciones internas.
Ayuda al estudiante paso a paso y comprueba explícitamente sus intentos.
Problema activo: factorizar x^2 - 5x + 6.
Turno del estudiante: {turn}
"""
TURNS = [
    "Ayúdame a factorizar x^2 - 5x + 6.",
    "4 y 6 son la respuesta correcta?",
]


def call(base_url: str, model: str, prompt: str, timeout: float) -> dict:
    body = json.dumps({
        "model": model,
        "messages": [{"role": "user", "content": "/no_think\n" + prompt}],
        "stream": False,
        "temperature": 0,
        "max_tokens": 768,
        "options": {"num_ctx": 4096},
        "think": False,
    }).encode()
    request = urllib.request.Request(
        base_url.rstrip("/") + "/api/chat", body,
        {"Content-Type": "application/json"}, method="POST"
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            payload = json.loads(response.read())
        message = payload.get("message") or {}
        answer = (message.get("content") or "").strip()
        return {"latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "answer": answer, "finish": payload.get("done_reason", ""),
                "error": ""}
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        return {"latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "answer": "", "finish": "error", "error": str(exc)}


def score(answer: str, turn: int) -> dict:
    normalized = answer.lower().replace("−", "-")
    factor = bool(re.search(r"x\s*[-−]\s*2", normalized) and
                  re.search(r"x\s*[-−]\s*3", normalized) and
                  ("-2" in normalized or "−2" in normalized) and
                  ("-3" in normalized or "−3" in normalized))
    wrong_topic = any(word in normalized for word in ("interés continuo", "producto punto", "cosecante", "secante"))
    return {"spanish": bool(re.search(r"\b(el|la|los|las|que|para|porque|necesitamos)\b", normalized)),
            "factor_correct": factor, "wrong_topic": wrong_topic,
            "turn_ok": bool(answer) and factor and not wrong_topic}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:11434")
    parser.add_argument("--models", nargs="+", default=["qwen3:1.7b", "qwen3:4b", "phi4-mini"])
    parser.add_argument("--timeout", type=float, default=45)
    parser.add_argument("--output", type=Path, default=Path("data/evaluation/local_model_benchmark_v2.json"))
    args = parser.parse_args()
    rows = []
    for model in args.models:
        history = []
        for index, turn in enumerate(TURNS, 1):
            prompt = PROMPT.format(turn=turn)
            # Include the previous exchange to make the second turn a real follow-up.
            if history:
                prompt += "\nRespuesta anterior del tutor:\n" + history[-1]
            result = call(args.base_url, model, prompt, args.timeout)
            result.update({"model": model, "turn": index, **score(result["answer"], index)})
            rows.append(result)
            if result["answer"]:
                history.append(result["answer"])
    summary = {}
    for model in args.models:
        model_rows = [row for row in rows if row["model"] == model]
        valid = [row for row in model_rows if row["finish"] != "error" and row["answer"]]
        summary[model] = {
            "turns": len(model_rows),
            "valid_answers": len(valid),
            "mean_latency_ms": round(sum(row["latency_ms"] for row in valid) / len(valid), 1) if valid else None,
            "correct_turns": sum(row["turn_ok"] for row in valid),
            "wrong_topic_turns": sum(row["wrong_topic"] for row in valid),
        }
    payload = {"description": "Fixed two-turn conversational benchmark; max_tokens=768; /no_think; direct Ollama API.",
               "models": args.models, "rows": rows, "summary": summary}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
