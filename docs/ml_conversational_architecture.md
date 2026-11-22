# Arquitectura ML conversacional de PATI

## Propósito

Se incorporó una capa de modelos de machine learning antes del retrieval para interpretar respuestas breves y mantener el hilo conversacional sin depender únicamente del LLM. PEP-Plan-RAG v3 continúa siendo el mecanismo de recuperación para preguntas conceptuales nuevas.

## Flujo

```text
mensaje -> clasificador de intención -> estado conversacional
        -> tipo de respuesta esperada -> evaluación simbólica/ML
        -> PEP-Plan-RAG v3 -> LLM -> guardrails -> respuesta
```

## Modelos

La implementación está en `src/ai_tutor/conversation/ml_models.py`.

### `CentroidClassifier`

Es un clasificador local entrenable basado en `HashingEncoder`. Para cada clase calcula un centroide:

\[
\mu_k = \frac{1}{n_k}\sum_{i=1}^{n_k}x_i
\]

La predicción utiliza la mayor similitud coseno:

\[
\hat{y}=\arg\max_k(x\cdot\mu_k)
\]

La confianza se estima mediante el margen entre las dos mejores clases. No requiere API externa ni un servidor adicional.

### Clasificador de intención

Clases:

```text
choose_for_student
feedback_check
feedback_uncertain
exercise_request
topic_switch
```

### Clasificador de respuesta esperada

Clases:

```text
example_submission
student_choice
conceptual_answer
```

Después de `¿Tienes una función concreta?`, la entrada `1/(x+2)` se interpreta como ejemplo matemático, no como pregunta nueva.

### Clasificador de siguiente acción

Clases preparadas:

```text
provide_scaffold
check_attempt
offer_exercise
activate_prerequisite
```

Este componente está disponible para experimentos de política pedagógica. La política actual mantiene una capa determinista mientras se recopilan datos reales.

## Integración

1. El modelo ML clasifica el turno si tiene suficiente confianza.
2. El estado guarda `active_problem`, `pending_question`, `expected_response_type`, `current_activity` y `next_action`.
3. Si la confianza es baja, se usa el fallback determinista.
4. PEP v3 se mantiene sin cambios y se aplica a preguntas conceptuales nuevas.

## Métricas ejecutadas

Las métricas se obtuvieron con los ejemplos semilla incluidos en el código. No representan aún desempeño con estudiantes reales.

### Entrenamiento

| Modelo | Ejemplos | Accuracy train |
|---|---:|---:|
| Intención | 27 | 1.00 |
| Tipo de respuesta | 10 | 1.00 |
| Siguiente acción | 12 | 1.00 |

Estas cifras solo verifican que el pipeline funciona. El conjunto es pequeño y los ejemplos fueron usados durante el ajuste.

### Prueba reproducible

Se reservó el último ejemplo de cada clase para `test` y se utilizaron los restantes para `train`.

| Modelo | Train | Test | Accuracy | Precision macro | Recall macro | F1 macro |
|---|---:|---:|---:|---:|---:|---:|
| Intención | 22 | 5 | 0.20 | 0.067 | 0.20 | 0.10 |
| Tipo de respuesta | 7 | 3 | 0.333 | 0.111 | 0.333 | 0.167 |
| Siguiente acción | 8 | 4 | 0.00 | 0.00 | 0.00 | 0.00 |

### Latencia

Se ejecutaron 1.500 predicciones combinando los tres modelos.

| Medida | Resultado |
|---|---:|
| Predicciones | 1.500 |
| Tiempo total | 25.64 ms |
| Tiempo medio por predicción | 0.051 ms |

## Interpretación

La prueba de test es baja porque hay pocos ejemplos y poca diversidad lingüística. No debe presentarse como desempeño final.

La conclusión válida es:

```text
La infraestructura ML funciona y es muy ligera,
pero todavía necesita conversaciones anotadas para generalizar.
```

La diferencia entre train y test demuestra que se necesita un dataset mayor antes de usar los clasificadores como única fuente de decisión.

## Evaluación futura

El dataset debe dividirse por conversación o estudiante para evitar fuga de información. Se medirán macro-F1, precisión, recall, calibración, matriz de confusión, latencia p50/p95, cambios incorrectos de tema y retrieval fuera de contexto.

También se evaluarán corrección matemática, activación de prerrequisitos, calidad de pistas, reconocimiento de errores y coherencia entre turnos.

La comparación experimental será:

```text
LLM + PEP v3
vs
LLM + PEP v3 + router ML
```

## Estado

Implementado:

- clasificador de intención;
- clasificador de respuesta esperada;
- clasificador de siguiente acción;
- integración con el controlador conversacional;
- fallback determinista por baja confianza;
- pruebas unitarias y benchmark de latencia;
- regresión para `no` seguido de `1/(x+2)`;
- 131 pruebas automatizadas pasando.

Pendiente:

- anotar conversaciones reales;
- aumentar la diversidad de ejemplos;
- separar train/validation/test por estudiante;
- calibrar las probabilidades;
- comparar contra un LLM como router;
- medir impacto pedagógico con estudiantes.

## Referencia metodológica

La separación entre enrutamiento, evaluación del estudiante y generación se inspira en el diseño de tutores conversacionales educativos discutido por Guatibonza Briceño et al. en ITS 2025:

<https://doi.org/10.1007/978-3-031-98281-1_19>

PATI adapta esa idea a Precálculo y mantiene PEP-Plan-RAG v3 como núcleo de recuperación pedagógicamente consciente.
