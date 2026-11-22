# Resultados de calidad de modelos y carga

Este documento consolida los resultados para reutilizarlos en la presentación
del proyecto doctoral. Los datos crudos permanecen en `data/evaluation/`.

## 1. Benchmark conversacional de modelos locales

Archivo crudo: [`local_model_benchmark_v2.json`](../data/evaluation/local_model_benchmark_v2.json)

Se mantuvieron constantes:

- el problema: `x^2 - 5x + 6`;
- el contexto conversacional;
- los dos turnos: pregunta inicial y el intento incorrecto `4 y 6`;
- idioma español;
- temperatura 0;
- contexto de 4096 tokens;
- máximo de 768 tokens;
- Ollama local y control `/no_think`.

| Modelo | Respuestas válidas | Latencia media | Resultado cualitativo |
|---|---:|---:|---|
| Qwen3 1.7B | 2/2 | 1,03 s | Correcto y en español. El segundo turno fue correcto, aunque muy breve. |
| Phi-4-mini | 2/2 | 6,23 s | Explicación más completa y buena corrección del intento del estudiante. Requiere guardrails para evitar frases ambiguas. |
| Qwen3 4B | 1/2 | 17,75 s en la respuesta válida | Una solicitud agotó el timeout y la respuesta válida apareció en inglés. No se selecciona para el piloto local. |

El benchmark es exploratorio: dos turnos por modelo no permiten afirmar
superioridad pedagógica. Sirve para seleccionar candidatos y diseñar la
evaluación posterior con estudiantes.

El archivo `local_model_benchmark.json` es un resultado preliminar que usó un
límite de 256 tokens. Las respuestas Qwen quedaron truncadas (`finish=length`),
por lo que no debe utilizarse para comparar calidad.

## 2. Prueba de carga del tutor

Archivo crudo: [`load_test_chat.json`](../data/evaluation/load_test_chat.json)

La prueba recorrió el flujo HTTP real: registro, aceptación del protocolo,
creación de conversación y envío de una pregunta. Se utilizaron usuarios y
conversaciones aisladas en niveles de 1, 3, 5 y 10 solicitudes simultáneas.

| Concurrencia | Éxitos | Fallbacks | p50 | p95 | Errores visibles |
|---:|---:|---:|---:|---:|---:|
| 1 | 1/1 | 0 | 19,6 s | 19,6 s | 0 |
| 3 | 3/3 | 1 | 21,7 s | 21,7 s | 0 |
| 5 | 5/5 | 3 | 12,6 s | 22,0 s | 0 |
| 10 | 10/10 | 8 | 12,9 s | 22,1 s | 0 |

Interpretación: el PC local no puede producir diez respuestas Qwen completas en
paralelo con la misma latencia. Sin embargo, la cola y el fallback evitaron
errores HTTP: las diez solicitudes recibieron respuesta. En ocho casos se usó
la respuesta instruccional local de emergencia. Esa señal se conserva para
analizar disponibilidad y calidad por separado.

## 3. Proveedor activo actualmente

La aplicación **no está usando Gemini como proveedor principal en este momento**.
La configuración activa de referencia es:

```text
Proveedor principal: local_qwen3_1_7b
Retrieval: PEP-Plan-RAG v3
Fallback local: instructional / instructional_emergency
Fallback remoto opcional: Gemini
```

Esto se mantiene así porque permite trabajar sin cuota ni dependencia de red.

## 4. Configuración propuesta para el piloto con estudiantes

Para priorizar naturalidad conversacional se propone una segunda configuración
de piloto:

```text
Gemini Flash
    ↓ timeout, 429, 503 o respuesta inválida
Qwen3 1.7B local
    ↓
InstructionalGenerator local
```

PEP-Plan-RAG v3 permanece igual en las dos configuraciones. Cambia únicamente
el modelo que redacta la respuesta, lo que mantiene la comparabilidad
experimental.

Antes de activar Gemini como principal se debe ejecutar el mismo script de
carga con la cuota real. Esa prueba consume solicitudes de Gemini y por eso no
se mezcló con el benchmark local.

## 5. Comandos de reproducción

```bash
# Calidad conversacional de modelos locales
.venv/bin/python scripts/benchmark_local_models.py

# Carga HTTP del tutor
.venv/bin/python scripts/load_test_chat.py

# Suite automatizada
PYTHONPATH=src .venv/bin/pytest -q
```

## 6. Ejecución con Gemini como proveedor principal

Se activó temporalmente en `.env`:

```text
AI_TUTOR_DEFAULT_PROVIDER=gemini
AI_TUTOR_FALLBACK_PROVIDERS=local_qwen3_1_7b,instructional
```

El smoke test de una solicitud fue exitoso. Después se ejecutó la carga
completa y se guardó separadamente en
[`gemini_load_test_chat.json`](../data/evaluation/gemini_load_test_chat.json).

| Concurrencia | Éxitos | Fallbacks registrados | p50 | p95 | Errores visibles |
|---:|---:|---:|---:|---:|---:|
| 1 | 1/1 | 0 | 7,2 s | 7,2 s | 0 |
| 3 | 3/3 | 0 | 13,8 s | 13,8 s | 0 |
| 5 | 5/5 | 3 | 12,3 s | 20,7 s | 0 |
| 10 | 10/10 | 8 | 12,6 s | 12,7 s | 0 |

La capa de resiliencia mantuvo 100% de solicitudes exitosas y ocultó los
errores técnicos. En los niveles de 5 y 10 usuarios se activó el fallback en
parte de las respuestas; esto confirma que Gemini funciona como proveedor
principal, pero que el piloto debe conservar Qwen3 y el fallback instruccional.

El archivo se generó antes de añadir el desglose detallado del proveedor en el
script; por ello el campo `fallbacks` cuenta los fallbacks observables en el
evento SSE, mientras que las próximas ejecuciones también guardarán el
proveedor y modelo efectivos por nivel.
