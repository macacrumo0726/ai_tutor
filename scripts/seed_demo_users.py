#!/usr/bin/env python3
"""Create idempotent, local-only demo accounts for the research interface."""
from __future__ import annotations

from ai_tutor.memory import (AuthenticationService, ConversationMemory,
                             ConversationRepository, LearningProfileService)
from ai_tutor.utils.paths import load_config, project_path


DEMO_USERS = (
    {
        "user_id": "test",
        "display_name": "test",
        "pin": "test",
        "concepts": [],
        "question": "Conversación inicial del usuario de prueba.",
    },
    {
        "user_id": "estudiante_demo_algebra",
        "display_name": "Estudiante demo · Álgebra",
        "pin": "Demo1234",
        "concepts": [("1_3_factorizacion_de_trinomios", "needs_help"),
                     ("1_3_factorizacion_de_factores_comunes", "partial")],
        "question": "¿Cómo puedo factorizar x² - 5x + 6?",
    },
    {
        "user_id": "estudiante_demo_funciones",
        "display_name": "Estudiante demo · Funciones",
        "pin": "Demo1234",
        "concepts": [("2_1_dominio_de_una_funcion", "understood"),
                     ("3_7_funciones_racionales", "partial")],
        "question": "¿Cómo encuentro el dominio de una función racional?",
    },
    {
        "user_id": "investigador_demo",
        "display_name": "Investigador demo",
        "pin": "Investiga1234",
        "concepts": [],
        "question": "Conversación de demostración para revisar el panel investigador.",
    },
)


def main():
    config = load_config()
    repository = ConversationRepository(project_path(config["paths"]["conversations"]))
    auth = AuthenticationService(repository, researcher_ids="investigador_demo")
    learning = LearningProfileService(repository)
    memory = ConversationMemory(repository, **config.get("memory", {}))

    for demo in DEMO_USERS:
        user = repository.get_user(demo["user_id"])
        if not user or not user.get("password_hash"):
            auth.register(demo["user_id"], demo["display_name"], demo["pin"])
        conversations = repository.list_conversations(demo["user_id"])
        if not conversations:
            conversation = memory.create(demo["user_id"], retrieval_method="pep_plan_rag",
                                         student_profile="persistent")
            memory.record_turn(demo["user_id"], conversation.conversation_id,
                               demo["question"], "Esta es una conversación de demostración del tutor.",
                               {"retrieval_method": "pep_plan_rag", "model_provider": "instructional",
                                "student_profile": f"persistent:{demo['user_id']}", "concepts": []})
        report = repository.learning_report(demo["user_id"])
        existing_concepts = {item["concept_id"] for item in report["evidence"]}
        for concept_id, feedback in demo["concepts"]:
            if concept_id not in existing_concepts:
                learning.record_feedback(demo["user_id"], [concept_id], feedback,
                                         metadata={"seed": "demo"})
        print(f"{demo['user_id']} | PIN: {demo['pin']} | role: {repository.get_user(demo['user_id'])['role']}")


if __name__ == "__main__":
    main()
