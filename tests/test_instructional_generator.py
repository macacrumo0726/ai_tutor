from ai_tutor.generation.instructional import InstructionalGenerator


def test_offline_generator_does_not_echo_prompt_context_or_instructions():
    prompt = """Pregunta del estudiante:
-?

Contexto de la conversación:
Problema activo: Ayúdame a factorizar x² - 5x + 6
Últimos turnos:
assistant: Una explicación larga.

<evidence>
La factorización busca dos números cuyo producto sea 6 y cuya suma sea -5.
</evidence>

Conceptos recuperados: factorización
Prerrequisitos detectados: operaciones algebraicas
Plan tutorial sugerido por el recuperador: no disponible
"""
    result = InstructionalGenerator().generate(prompt)
    assert "Contexto de la conversación" not in result.text
    assert "Plan tutorial sugerido" not in result.text
    assert "«-?»" in result.text
