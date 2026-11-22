# Regresión conversacional y memoria

Se amplió el banco de validación para buscar pérdidas de contexto en turnos
cortos. La prueba usa el servicio real, PEP-Plan-RAG v3, memoria persistente,
verificador matemático y `InstructionalGenerator`; no consume cuota de Gemini.

## Casos ejecutados

Se probaron 38 conversaciones y 191 turnos, incluyendo:

- matrices con respuestas numéricas (`4 + 3 → 7`);
- respuesta incorrecta y posterior corrección (`8`, `7`);
- factorización con pares incorrectos y correctos;
- dominio con valores excluidos;
- producto punto sin mezclarlo con interés continuo o trigonometría;
- relación frente a función;
- pendiente y desigualdades;
- cambio explícito de tema hacia logaritmos;
- radicales y trigonometría;
- saludos, agradecimientos, confirmaciones y referencias como “eso”, “¿por qué?” y “ahora sí”.
- dominio de logaritmos, composición e inversas;
- valor absoluto de √(x²), leyes de exponentes y grados frente a radianes;
- desigualdades con divisor negativo y nuevos casos de factorización/matrices.

## Resultado inicial

La primera ejecución encontró un fallo en el turno `ahora sí` después de una
respuesta incorrecta sobre matrices. El retriever terminaba recuperando
modelado con ecuaciones y topografía porque el turno corto no contenía un tema.

## Correcciones

1. Se añadieron matrices, escalares, vectores, suma y resta al detector de
   problema activo.
2. Las consultas cortas conservan el problema activo y la última pregunta del
   tutor como ancla limitada.
3. “Sí”, “ahora sí”, “correcto”, “exacto”, “vale” y “de acuerdo” se reconocen
   como confirmaciones conversacionales y no disparan un nuevo retrieval.
4. El verificador identifica micro-preguntas de suma de entradas de matrices,
   incluso cuando el tutor escribe “si tenemos 4 y 3 en la misma posición”.
5. La respuesta numérica se comprueba antes de que el LLM pueda cambiar de
   tema o felicitar una respuesta incorrecta.
6. Se añadieron respuestas locales específicas para dimensiones de matrices,
   evaluación de funciones, pendiente, desigualdades, ecuaciones lineales,
   ecuaciones cuadráticas y valores trigonométricos básicos.
7. Un cambio explícito como “cambiemos a ecuaciones lineales” reemplaza el
   ancla anterior antes de consultar el grafo.

## Resultado posterior

```text
Escenarios: 38
Turnos: 191
Turnos fallidos: 0
Latencia total local: aproximadamente 71 s
```

El detalle por turno queda en
[`context_regression_results.json`](../data/evaluation/context_regression_results.json).

Los casos adicionales informados por recursos educativos abiertos están
documentados en [`web_informed_validation.md`](web_informed_validation.md) y
sus resultados en [`web_informed_scenarios.json`](../data/evaluation/web_informed_scenarios.json).

## Reproducción

```bash
.venv/bin/python scripts/validate_context_regressions.py
PYTHONPATH=src .venv/bin/pytest -q
```
