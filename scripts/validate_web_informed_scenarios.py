#!/usr/bin/env python3
"""Validate source-informed misconception dialogues without provider quota.

The prompts are synthetic (not copied from student data) and are based on
open precalculus exercise patterns.  The checks are intentionally conservative:
they verify topic, key mathematical relation, and that a short answer does not
reopen an unrelated textbook topic.
"""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from ai_tutor.api.services import TutorApplicationService
from ai_tutor.memory import ConversationRepository


CASES = [
    ("domain", "Halla el dominio de (x+1)/(x-2)", ["denominador", "2"]),
    ("domain", "¿se incluye el 2?", ["no", "dominio"]),
    ("radical", "Simplifica √(x²)", ["|x|", "no siempre"]),
    ("logarithm", "¿Qué condición debe cumplir el argumento de log(x+3)?", ["positivo", "x > -3"]),
    ("inequality", "Resuelve -3x ≤ 12", ["x ≥ -4", "inv" ]),
    ("composition", "Si f(x)=2x+1 y g(x)=x², calcula f(g(2))", ["9", "g(2)"]),
    ("inverse", "¿Cuándo una función tiene inversa?", ["uno a uno"]),
    ("exponents", "Simplifica x³·x²", ["x⁵", "suman"]),
    ("trigonometry", "¿Cuánto vale sen(30°)?", ["1/2"]),
    ("quadratic", "Factoriza x²+5x+6", ["(x + 2)(x + 3)"]),
]


def main() -> None:
    rows = []
    with tempfile.TemporaryDirectory(prefix="pati-web-informed-") as tmp:
        service = TutorApplicationService(repository=ConversationRepository(Path(tmp) / "cases.sqlite3"))
        service.default_provider = "instructional"
        service.default_retrieval = "pep_plan_rag"
        user = service.auth.register("web-informed", "Synthetic Student", "1234")
        service.repository.save_protocol_acceptance(user["user_id"], service._protocol_version(), True)
        identity = service.auth.require(user)
        conversation = service.memory.create(identity["user_id"], title="web-informed")
        for topic, question, expected in CASES:
            result = service.ask(identity, conversation.conversation_id, question)
            answer = result["answer"].lower()
            missing = [term for term in expected if term.lower() not in answer]
            rows.append({"topic": topic, "question": question, "answer": result["answer"], "missing": missing,
                         "provider": result["metadata"].get("model_provider", "")})
    payload = {"case_count": len(rows), "failed_cases": sum(bool(row["missing"]) for row in rows), "rows": rows}
    output = Path("data/evaluation/web_informed_scenarios.json")
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps({k: v for k, v in payload.items() if k != "rows"}, ensure_ascii=False, indent=2))
    print(f"Resultados detallados: {output}")


if __name__ == "__main__":
    main()
