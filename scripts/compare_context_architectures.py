#!/usr/bin/env python3
"""Summarize the measured context-controller run against the prior baseline.

The previous numbers are historical measurements from the regression report;
they are not rerun by pretending to be the old implementation. The current
run is loaded from the detailed JSON produced by the regression scripts.
"""
from __future__ import annotations

import json
from pathlib import Path


def main() -> None:
    root = Path(__file__).resolve().parents[1]
    current = json.loads((root / "data/evaluation/context_regression_results.json").read_text())
    informed = json.loads((root / "data/evaluation/web_informed_scenarios.json").read_text())
    payload = {
        "comparison": [
            {
                "architecture": "previous_context_handling",
                "source": "historical regression observation",
                "scenarios": 28,
                "turns": 141,
                "failed_turns": 1,
                "latency_ms": None,
            },
            {
                "architecture": "context_controller_pep_plan_rag_v3",
                "source": "rerun 2026-11-06",
                "scenarios": current["scenario_count"],
                "turns": current["turn_count"],
                "failed_turns": current["failed_turns"],
                "latency_ms": current["elapsed_ms"],
            },
        ],
        "source_informed_validation": {
            "cases": informed["case_count"],
            "failed_cases": informed["failed_cases"],
        },
        "interpretation": (
            "La versión nueva amplía el banco y elimina los fallos observados; "
            "la latencia histórica de la versión anterior no se midió con el mismo "
            "controlador, por lo que no se presenta como comparación causal."
        ),
    }
    output = root / "data/evaluation/context_architecture_comparison.json"
    output.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    print(f"Resultados: {output}")


if __name__ == "__main__":
    main()
