# Arquitectura de modelos recomendada para el piloto

## Evidencia disponible

Se ejecutó un benchmark conversacional fijo de dos turnos sobre el mismo
problema (`x^2 - 5x + 6`) y el mismo contexto: pregunta inicial y seguimiento
incorrecto (`4 y 6 son la respuesta correcta?`). Se usó Ollama local,
temperatura 0, contexto 4096 y hasta 768 tokens de salida.

| Modelo | Respuestas | Latencia media | Resultado observado |
|---|---:|---:|---|
| Qwen3 1.7B | 2/2 | 1.032 s | Español, respuesta correcta; el segundo turno fue correcto pero muy breve. |
| Phi-4-mini | 2/2 | 6.226 s | Explicación más completa; corrigió el intento, aunque una frase intermedia puede ser ambigua. |
| Qwen3 4B | 1/2 | 17.747 s (la primera solicitud agotó 45 s) | Potencialmente más capaz, pero no adecuado como servicio principal en este PC. |

El resultado no pretende ser una comparación estadística definitiva: es un
smoke benchmark de disponibilidad, latencia, idioma, coherencia temática y
corrección matemática. El archivo reproducible es
`data/evaluation/local_model_benchmark_v2.json` y se ejecuta con:

```bash
.venv/bin/python scripts/benchmark_local_models.py
```

## Arquitectura para 10 estudiantes

```text
interfaz → FastAPI → autenticación/protocolo vigente
         → memoria + perfil persistente
         → PEP-Plan-RAG v3 (retrieval común a todos los modelos)
         → Qwen3 1.7B en Ollama (respuesta principal)
         → guardrails de idioma, tema y verificación matemática
         → fallback InstructionalGenerator (local, inmediato)
         → fallback Gemini opcional y registrado
         → PostgreSQL/SQLite: turnos, latencias, proveedor y evidencia
```

La separación es intencional: PEP v3 decide la evidencia y el plan de
prerrequisitos; el modelo sólo redacta la respuesta. Un cambio de modelo no
cambia la condición de recuperación y por tanto mantiene la comparación
experimental.

### Política de proveedores

1. **Producción piloto:** Qwen3 1.7B como proveedor primario. Su latencia y
   consumo permiten atender varias sesiones en el PC local.
2. **Fallo o respuesta inválida:** respuesta instruccional determinista local.
   Se activa si hay timeout, salida vacía, inglés dominante, fuga de prompt,
   tema incorrecto o inconsistencia matemática. No se espera a Gemini para
   resolver fallos conocidos.
3. **Condición de investigación:** Phi-4-mini como segundo modelo local para
   comparar calidad conversacional, con timeout controlado. Debe medirse con el
   mismo banco y el mismo PEP v3 antes de convertirlo en proveedor automático.
4. **Qwen3 4B:** sólo pruebas controladas o una máquina con más recursos; no es
   el default del piloto por su latencia observada.
5. **Gemini:** fallback remoto explícito, útil cuando los dos proveedores
   locales fallan, pero sujeto a cuota, red y errores 503/504. Toda activación se
   registra en la metadata del turno.

## Qué se debe medir antes de abrir el enlace

Para cada modelo se repite el banco con al menos 100 conversaciones sintéticas
y, posteriormente, con las sesiones reales: latencia p50/p95, tasa de timeout,
respuesta en español, relevancia temática, corrección matemática, aceptación
del guardrail, uso de fallback y calidad pedagógica evaluada por jueces.

El benchmark local de este documento no sustituye la evaluación pedagógica:
sirve para escoger una arquitectura estable. La hipótesis de investigación se
prueba después manteniendo PEP v3, preguntas, top-k y prompt constantes, y
cambiando únicamente el modelo generador.
