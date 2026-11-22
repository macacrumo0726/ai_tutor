# Controlador general de contexto de PATI

Implementación inspirada en arquitecturas de tutor conversacional con routers
conceptuales, routers de feedback, resumen de conversación y evaluación de
respuestas. PEP-Plan-RAG v3 no se modifica: el controlador decide qué significa
el turno y qué contexto debe recibir el retriever.

## Flujo

```text
mensaje del estudiante
        |
        v
router conceptual ──> cambio de tema o pregunta conceptual
        |
        +────────────> router de feedback
                         |
                         +--> evaluación matemática determinista
                         +--> evaluación conceptual conservadora
        |
        v
resumen + estado pedagógico + historial relevante
        |
        v
PEP-Plan-RAG v3 (sin modificar)
        |
        v
LLM con evidencia acotada y trazable
```

## Componentes

`src/ai_tutor/conversation/controller.py` contiene:

- `route_turn`: clasifica una entrada como pregunta conceptual, respuesta de
  feedback, delegación de elección o cambio de tema.
- `evaluate_conceptual_answer`: devuelve `correct`, `incorrect` o `uncertain`.
  Nunca convierte una respuesta no soportada en correcta.
- `ContextDecision`: registra intención, consulta, seguimiento, tema activo y
  evaluación.

La memoria genera un resumen extractivo y auditable con tema activo, actividad,
pregunta pendiente y fragmentos recientes. No se utiliza otro LLM para resumir,
por lo que el control no añade latencia ni variabilidad de proveedor.

## Separación de responsabilidades

1. El controlador interpreta la conversación.
2. PEP-Plan-RAG v3 recupera evidencia y prerrequisitos.
3. El generador redacta la explicación pedagógica.
4. Los evaluadores verifican respuestas breves y señales conceptuales.

Esta separación permite comparar modelos y retrievals sin cambiar el algoritmo
PEP v3 ni confundir un error de contexto con un error de recuperación.

## Validación

- Suite automatizada: 120 pruebas aprobadas.
- Se añadieron pruebas para `dime tú`, `dime tu`, feedback conceptual y estados
  de incertidumbre.
- Se mantienen los bancos de regresión de 38 conversaciones/191 turnos y de 10
  casos informados de Precálculo.

## Referencia metodológica

La organización toma como inspiración el trabajo *Evaluating an AI-Driven
Chatbot Tutor for Enhancing Introductory Programming Learning* (ITS 2025),
adaptando sus ideas de enrutamiento y evaluación al dominio de Precálculo.
La referencia no se copia literalmente: se implementa como una capa de control
compatible con el retrieval pedagógico existente.
