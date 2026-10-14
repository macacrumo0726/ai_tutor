from __future__ import annotations
from .schema import AssessmentResult, PedagogicalDecision


def decide(result: AssessmentResult, mastery: float, attempt_number: int,
           prerequisites=None) -> PedagogicalDecision:
    prerequisites=prerequisites or []
    if result.correct and mastery>=.65:
        return PedagogicalDecision("advance","Respuesta correcta y dominio estimado suficiente.")
    if result.correct:
        return PedagogicalDecision("consolidate","Respuesta correcta, pero el dominio aún requiere otra oportunidad.")
    if attempt_number<=2:
        return PedagogicalDecision("hint",f"Intento {attempt_number} incorrecto: ofrecer pista progresiva.",attempt_number)
    if prerequisites:
        return PedagogicalDecision("remediate_prerequisite","Errores persistentes: activar el prerrequisito más cercano.",3,prerequisites[0])
    return PedagogicalDecision("worked_example","Errores persistentes sin prerrequisito disponible: mostrar ejemplo trabajado.",3)
