# Experimento comparativo de generación con GPT y PEP-Plan-RAG v3

## 1. Objetivo

Evaluar si utilizar GPT como modelo generador principal mejora la calidad conversacional y pedagógica de PATI frente a las configuraciones actuales, manteniendo fijo el mecanismo de recuperación.

La condición científica central es:

```text
misma base instruccional
misma pregunta
mismo perfil de estudiante
mismo prompt pedagógico
mismo top-k
mismo PEP-Plan-RAG v3
solo cambia la arquitectura de generación
```

No se debe comparar GPT + PEP v3 contra un modelo local usando otro retrieval. La variable independiente será el modelo y su política de fallback.

## 2. Arquitectura común

Todas las condiciones usarán:

```text
router ML conversacional
        ↓
memoria y estado pedagógico
        ↓
PEP-Plan-RAG v3
        ↓
prompt precalculus_tutor.txt
        ↓
modelo generador de la condición
        ↓
guardrails y verificación matemática
        ↓
respuesta
```

El retrieval PEP v3 debe producir y registrar los mismos campos en todas las condiciones:

```text
retrieved_chunk_ids
retrieved_concept_ids
required_prerequisites
retrieval scores
retrieval latency
```

## 3. Condiciones experimentales

### A. Configuración actual

```text
principal: Qwen local mediante Ollama
fallback: Gemini / instructional
retrieval: PEP-Plan-RAG v3
```

Representa el sistema disponible para el piloto local.

### B. GPT como principal

```text
principal: OpenAI gpt-4.1-mini
fallback 1: Qwen local
fallback 2: instructional deterministic
retrieval: PEP-Plan-RAG v3
```

Esta es la condición recomendada para el primer experimento porque GPT-4.1 mini está configurado en el proyecto y usa el endpoint Responses API.

### C. GPT como principal con fallback remoto

```text
principal: OpenAI gpt-4.1-mini
fallback 1: Gemini
fallback 2: instructional deterministic
retrieval: PEP-Plan-RAG v3
```

Permite medir disponibilidad cuando Ollama no está activo.

### D. Gemini como principal

```text
principal: Gemini Flash
fallback: instructional deterministic
retrieval: PEP-Plan-RAG v3
```

Sirve como comparación de un proveedor remoto alternativo.

### E. Local-first con fallback GPT

```text
principal: Qwen local
fallback 1: OpenAI gpt-4.1-mini
fallback 2: instructional deterministic
retrieval: PEP-Plan-RAG v3
```

Esta condición puede reducir costos, pero solo usa GPT cuando el modelo local falla guardrails, produce una respuesta vacía o supera el tiempo máximo.

### F. GPT con router ML y guardrails

```text
router conversacional ML
PEP-Plan-RAG v3
OpenAI gpt-4.1-mini
evaluación matemática
guardrails de relevancia y fuga de prompt
```

Es la condición completa propuesta para estudiar si el problema observado era generación, contexto o ambos.

## 4. Hipótesis

### Hipótesis principal

GPT como generador principal, manteniendo PEP v3 y el controlador ML, reducirá las respuestas fuera de contexto y mejorará la continuidad conversacional frente a Qwen local.

### Hipótesis secundaria

La configuración local-first tendrá menor costo, pero GPT como fallback reducirá los errores graves sin enviar todas las conversaciones a la API.

### Hipótesis nula

Las diferencias observadas se explican por el retrieval o por el manejo del contexto, no por el modelo generador.

## 5. Banco de pruebas

Se recomienda un banco de 120 conversaciones, con 20 conversaciones por categoría:

| Categoría | Ejemplo de comportamiento |
|---|---|
| pregunta conceptual | “¿Cuál es la diferencia entre relación y función?” |
| ejercicio procedimental | “Factoriza x² - 5x + 6” |
| respuesta corta | “no”, “mmm”, “7”, “eso” |
| seguimiento | “explícamelo”, “¿por qué?”, “dame un ejemplo” |
| corrección | respuesta correcta, incorrecta y parcial |
| prerrequisitos | factorización antes de ecuaciones cuadráticas |
| cambio de tema | pasar de funciones a trigonometría |
| conversación larga | 8–12 turnos sobre el mismo problema |
| expresión matemática | `1/(x+2)`, `2^3 * 2^2`, `f(3)` |
| disponibilidad | timeout, respuesta vacía o error del proveedor |
| pedagogía | pedir pista, explicación o repaso |
| adversarial | texto ambiguo o evidencia irrelevante |

Cada conversación debe ejecutarse contra todas las condiciones, usando el mismo orden de turnos y el mismo perfil simulado.

## 6. Métricas

### Calidad de respuesta

```text
answer_correctness
token_f1
conceptual_accuracy
mathematical_verification_rate
```

### Continuidad conversacional

```text
contextual_coherence
short_turn_resolution_rate
topic_switch_error_rate
active_problem_retention
answer_repetition_rate
```

### Recuperación

```text
Hit@K
MRR
Concept Recall
Prerequisite Recall
retrieval latency
```

La recuperación debería ser casi idéntica entre condiciones. Si cambia, hay una violación del diseño experimental.

### Diseño instruccional

Evaluación humana con rúbrica de 1 a 5:

```text
reconoce la dificultad
activa conocimiento previo
ofrece andamiaje
incluye micro-check
evita revelar la solución prematuramente
mantiene coherencia pedagógica
```

### Operación

```text
latencia p50 / p95
tasa de timeout
tasa de fallback
tasa de respuesta vacía
tokens de entrada y salida
costo por conversación
```

## 7. Protocolo de ejecución

1. Fijar semilla y versión del dataset.
2. Fijar `AI_TUTOR_DEFAULT_RETRIEVAL=pep_plan_rag`.
3. Desactivar cambios dinámicos de `top_k`.
4. Ejecutar cada conversación con un identificador reproducible.
5. Registrar el mismo prompt, contexto, conceptos y chunks para cada condición.
6. Separar latencia de retrieval y latencia de generación.
7. Guardar errores del proveedor sin mostrarlos al estudiante.
8. Repetir cada escenario tres veces si el proveedor remoto presenta variabilidad.
9. Comparar resultados por conversación pareada, no solo por promedio global.
10. Aplicar evaluación humana ciega al modelo utilizado.

## 8. Configuración recomendada para GPT

En `.env`:

```text
OPENAI_API_KEY=<clave_local_no_versionada>
OPENAI_MODEL=gpt-4.1-mini
AI_TUTOR_DEFAULT_PROVIDER=openai
AI_TUTOR_FALLBACK_PROVIDERS=local_qwen3_1_7b,instructional
AI_TUTOR_DEFAULT_RETRIEVAL=pep_plan_rag
```

La clave nunca debe aparecer en el repositorio, logs, resultados ni capturas.

El modelo configurado actualmente es `gpt-4.1-mini`, cuyo precio publicado es de USD 0.40 por millón de tokens de entrada y USD 1.60 por millón de tokens de salida. [Precios oficiales de OpenAI](https://developers.openai.com/api/docs/models/gpt-4.1-mini)

## 9. Proyección de costos de GPT

### Supuestos

Para una conversación típica se presupone:

```text
1.800 tokens de entrada
350 tokens de salida
```

El cálculo es:

\[
C = \frac{I}{1{,}000{,}000}p_i + \frac{O}{1{,}000{,}000}p_o
\]

Con GPT-4.1 mini:

```text
entrada: 1.800 × 0.40 / 1.000.000 = USD 0.00072
salida:    350 × 1.60 / 1.000.000 = USD 0.00056
total aproximado por turno = USD 0.00128
```

### Escenarios

| Uso | Turnos | Costo GPT estimado |
|---|---:|---:|
| smoke test | 100 | USD 0.13 |
| benchmark inicial | 1.000 | USD 1.28 |
| 10 estudiantes × 100 turnos | 1.000 | USD 1.28 |
| 10 estudiantes × 500 turnos | 5.000 | USD 6.40 |
| prueba con 20% de repetición/fallback | 6.000 | USD 7.68 |
| 10 estudiantes × 1.000 turnos | 10.000 | USD 12.80 |

Estos valores son proyecciones, no cargos reales. El costo final depende de los tokens reales, reintentos, fallbacks y del modelo vigente.

### Comparación de reducción por arquitectura

Si la política local-first envía solo el 30% de los turnos a GPT:

```text
1.000 turnos × 30% × USD 0.00128 = USD 0.384
```

La política local-first es atractiva para el piloto si la calidad no cae y el fallback se activa solo ante errores o baja confianza.

## 10. Tabla comparativa de arquitecturas

| Arquitectura | Calidad esperada | Latencia | Costo API | Riesgo principal | Uso recomendado |
|---|---|---|---|---|---|
| Qwen local + PEP v3 | media, variable | baja después de cargar modelo | USD 0 | respuestas fuera de contexto | desarrollo local |
| Gemini + PEP v3 | media-alta | media | bajo o gratuito según cuota | límites y disponibilidad | comparación económica |
| GPT principal + PEP v3 | alta esperada | media | pago por tokens | costo y dependencia externa | experimento controlado |
| Qwen principal + GPT fallback + PEP v3 | alta con menor costo | variable | bajo-medio | fallback tardío | piloto con estudiantes |
| GPT + router ML + PEP v3 | condición más completa | media | pago por tokens | requiere validar router | condición recomendada |
| GPT fine-tuned + PEP v3 | desconocida | media | entrenamiento/inferencia | datos insuficientes | fase posterior |

Las calificaciones de calidad son hipótesis de diseño, no resultados. Deben sustituirse por métricas obtenidas en el benchmark.

## 11. Criterios de decisión

Se recomendará GPT como principal solo si, frente a la configuración actual:

```text
mejora la corrección matemática;
reduce respuestas fuera de contexto;
reduce cambios incorrectos de tema;
mantiene o mejora la calidad pedagógica;
mantiene p95 dentro del límite definido;
el costo es aceptable para el piloto.
```

Una regla inicial para el piloto podría ser:

```text
calidad pedagógica >= 4/5
answer correctness >= 90%
topic switch error rate <= 5%
fallback rate <= 20%
latencia p95 <= 12 segundos
```

Estos umbrales son criterios operativos iniciales, no resultados observados.

## 12. Resultado esperado del experimento

El experimento no debe afirmar que GPT es mejor antes de ejecutarse. Puede producir cualquiera de estos resultados:

```text
GPT mejora calidad y continuidad, con costo aceptable;
GPT mejora redacción, pero no el retrieval;
GPT no mejora frente a Qwen cuando el contexto está bien controlado;
la arquitectura local-first ofrece la mejor relación costo-calidad.
```

La conclusión debe basarse en los resultados pareados por conversación y no solamente en la percepción de fluidez.

## 13. Reproducibilidad

Cada registro debe guardar:

```text
question_id
conversation_id
condition
provider
model
retrieval_method
retrieval_query
retrieved_chunk_ids
retrieved_concept_ids
prompt_version
input_tokens
output_tokens
latency_ms
fallback_used
answer
metrics
timestamp_utc
git_commit
```

La comparación final debe generar un archivo tabular con una fila por conversación y condición.

## 14. Ejecución piloto realizada

Se ejecutó una primera prueba real con:

```text
provider: openai
model: gpt-4.1-mini
retrieval: pep_plan_rag
split: validation
preguntas: 10
top_k: 5
```

Comando utilizado:

```bash
.venv/bin/python scripts/evaluate.py \
  --provider openai \
  --methods pep_plan_rag \
  --split validation \
  --limit 10 \
  --output data/evaluation/openai_pep_v3_validation_10.jsonl
```

Resultados observados:

| Métrica | Resultado |
|---|---:|
| Solicitudes | 10 |
| Errores de generación | 0 |
| Latencia total media | 5.122 s |
| Latencia de generación media | 4.757 s |
| Latencia de retrieval media | 0.160 s |
| Token F1 medio | 0.223 |
| Hit@5 medio | 0.400 |
| Concept Recall medio | 0.400 |
| Prerequisite Recall medio | 0.600 |

Archivo generado:

```text
data/evaluation/openai_pep_v3_validation_10.jsonl
```

Esta ejecución confirma que la ruta GPT + PEP v3 funciona técnicamente y que las solicitudes llegaron a OpenAI sin fallback. No permite todavía afirmar que GPT sea mejor: hace falta ejecutar las mismas diez preguntas con Qwen, Gemini y las arquitecturas de fallback, y después comparar por pregunta.

Como referencia técnica se ejecutó el mismo conjunto con el generador determinista `instructional`:

| Condición | Latencia total media | Generación media | Retrieval Hit@5 | Concept Recall | Prerequisite Recall | Token F1 |
|---|---:|---:|---:|---:|---:|---:|
| GPT-4.1 mini + PEP v3 | 5.122 s | 4.757 s | 0.400 | 0.400 | 0.600 | 0.223 |
| Instructional + PEP v3 | 0.330 s | 0.001 s | 0.400 | 0.400 | 0.600 | 0.300 |

El retrieval es prácticamente idéntico, como exige el diseño. La diferencia observada está en la generación y en la latencia. El Token F1 no es una medida suficiente de calidad pedagógica y, en esta muestra pequeña, no favorece a GPT; se requiere una evaluación humana ciega para valorar naturalidad, corrección, andamiaje y continuidad.

## 15. Comparación real de cuatro arquitecturas LLM

Se ejecutó un benchmark pareado con 3 preguntas de validation, 4 arquitecturas, 12 ejecuciones, PEP-Plan-RAG v3 fijo y `top_k=5`.

```bash
.venv/bin/python scripts/compare_llm_architectures.py \
  --architectures gpt_primary gemini_primary \
  qwen_primary_gemini_fallback deepseek_primary_gemini_fallback \
  --split validation --limit 3 \
  --output data/evaluation/llm_architectures_pep_v3_validation_3.jsonl
```

Resultados observados:

| Arquitectura | Proveedor efectivo | Éxito | Fallbacks | Latencia media | Token F1 | Hit@5 | Concept Recall | Prerequisite Recall |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| GPT principal | OpenAI | 3/3 | 0 | 4.972 s | 0.227 | 1.00 | 1.00 | 1.00 |
| Gemini principal | Instructional fallback | 3/3 | 3 | 0.316 s | 0.466 | 1.00 | 1.00 | 1.00 |
| Qwen + Gemini fallback | Qwen local | 3/3 | 0 | 20.497 s | 0.225 | 1.00 | 1.00 | 1.00 |
| DeepSeek + Gemini fallback | DeepSeek | 3/3 | 0 | 5.096 s | 0.223 | 1.00 | 1.00 | 1.00 |

### Incidencia de Gemini

Las tres llamadas a Gemini fallaron con `400 API_KEY_INVALID`. La arquitectura completó las conversaciones gracias al fallback determinista, pero no es una medición válida de Gemini. La clave presente en `.env` debe verificarse antes de repetir el benchmark.

### Interpretación

- GPT respondió las tres preguntas sin fallback y con una latencia media de aproximadamente 5 segundos.
- Qwen local respondió, pero su latencia media fue aproximadamente 20.5 segundos.
- DeepSeek respondió sin fallback, con latencia similar a GPT.
- Gemini no fue evaluado realmente por una clave inválida.
- Las métricas de retrieval son idénticas porque PEP v3 se mantuvo fijo.
- Token F1 no es suficiente para afirmar calidad pedagógica.

Los resultados se guardaron en `data/evaluation/llm_architectures_pep_v3_validation_3.jsonl` y `data/evaluation/llm_architectures_pep_v3_validation_3_summary.json`.

Este benchmark es un smoke test técnico, no una conclusión científica. Debe repetirse con al menos 30–50 preguntas y evaluación humana ciega.

## 16. Matriz activa sin Gemini

Gemini se retiró de la matriz activa porque la clave configurada devolvió `API_KEY_INVALID` y no permitió medir ese proveedor de forma válida. Los artefactos históricos de Gemini se conservan para trazabilidad, pero no participa en los fallbacks ni en las opciones experimentales actuales.

La matriz vigente es:

| Condición activa | Cadena de proveedores |
|---|---|
| GPT principal | OpenAI → instructional |
| DeepSeek principal | DeepSeek → instructional |
| Qwen local | Qwen → DeepSeek → OpenAI → instructional |
| Phi-4 local | Phi-4 → DeepSeek → OpenAI → instructional |

## 17. Ranking provisional de la ejecución sin Gemini

Se ejecutaron 3 preguntas por arquitectura. El ranking siguiente combina latencia, disponibilidad y métricas automáticas; no sustituye la evaluación conversacional humana.

| Puesto provisional | Arquitectura | Lectura |
|---:|---|---|
| 1 | GPT principal | Mejor equilibrio entre disponibilidad y latencia entre los modelos remotos probados; respondió 3/3 sin fallback. |
| 2 | DeepSeek principal | Menor latencia media que GPT y disponibilidad completa; requiere evaluación humana para confirmar naturalidad pedagógica. |
| 3 | Qwen local + fallbacks | Sin costo API y respuestas completas, pero con latencia media cercana a 20.5 s. |
| 4 | Phi-4 local + fallbacks | Una ejecución necesitó fallback y la latencia media fue 13.3 s; su calidad conversacional necesita más ejemplos. |

Esta clasificación es provisional porque la muestra contiene solo tres preguntas de un mismo subtema. Para un ranking conversacional válido se requiere evaluar turnos cortos, correcciones, cambios de tema, solicitudes de pistas y conversaciones de 8–12 turnos con una rúbrica humana ciega.

## 18. Ranking conversacional provisional

El ranking conversacional no puede considerarse definitivo todavía porque no se ha aplicado una evaluación humana ciega. Sin embargo, combinando las respuestas observadas, la latencia, la estabilidad y las métricas automáticas, el orden provisional es:

| Puesto | Modelo | Evidencia observada | Recomendación |
|---:|---|---|---|
| 1 | DeepSeek API | Menor latencia media entre los modelos remotos (4.50 s) y respuestas más extensas y naturales en el smoke test. | Candidato principal para el piloto. |
| 2 | GPT-4.1 mini | Mayor estabilidad, buen seguimiento de instrucciones y 3/3 respuestas sin fallback; latencia media de 5.25 s. | Principal premium o fallback prioritario. |
| 3 | Qwen3-1.7B local | Sin costo API y respuestas utilizables, pero latencia media de 20.47 s y menor riqueza conversacional. | Desarrollo local o fallback económico. |
| 4 | Phi-4-mini local | Latencia media de 13.34 s y una ejecución necesitó fallback; menor consistencia observada. | Modelo experimental. |

### Métricas automáticas asociadas

| Modelo | Token F1 | Latencia media |
|---|---:|---:|
| GPT-4.1 mini | 0.241 | 5.25 s |
| Qwen3-1.7B | 0.225 | 20.47 s |
| DeepSeek | 0.224 | 4.50 s |
| Phi-4-mini | 0.216 | 13.34 s |

Token F1 no mide por sí solo naturalidad, continuidad ni calidad pedagógica. Por eso, el ranking anterior debe validarse con una rúbrica humana de 1 a 5 que mida:

```text
naturalidad
continuidad conversacional
corrección matemática
calidad del andamiaje
interpretación de respuestas cortas
manejo de cambios de tema
coherencia con PEP-Plan-RAG v3
```

### Arquitecturas recomendadas

Configuración orientada a calidad y costo:

```text
DeepSeek principal
→ GPT-4.1 mini
→ InstructionalGenerator
```

Configuración orientada a máxima estabilidad:

```text
GPT-4.1 mini principal
→ DeepSeek
→ InstructionalGenerator
```

Estas recomendaciones son provisionales y no constituyen una conclusión final hasta ejecutar la evaluación conversacional humana con al menos 30–50 conversaciones.
