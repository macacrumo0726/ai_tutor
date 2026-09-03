# Diseño experimental

## Etapa 1: protocolo Gemini-first

La primera comparación fija `gemini-3.6-flash`, temperatura 0, `top_k=5`,
semilla 42 y las mismas preguntas. Esto separa cinco condiciones:

| ID | Condición | Base instruccional | Recuperación |
|---|---|---|---|
| C0 | Gemini normal | No | Ninguna |
| C1 | Gemini + prompt pedagógico | No | Ninguna |
| C2 | Gemini + base | Sí | RAG |
| C3 | Gemini + base | Sí | Graph-RAG |
| C4 | Gemini + base | Sí | PEP-SA-RAG |
| C5 | Gemini + base | Sí | PEP-Plan-RAG v3 |

El piloto tendrá 30 preguntas estratificadas por tema, dificultad y tipo. La
ejecución se configura en `configs/gemini_pilot.yaml` y se inicia con:

```bash
python scripts/evaluate_gemini_pilot.py --limit 30
```

Gemini no se considera una condición fine-tuned en esta etapa. El fine-tuning
se estudiará después con Qwen mediante QLoRA, manteniendo separados los efectos
de familia, adaptación, prompt y recuperación.

## Pregunta

¿La estructura explícita de conocimiento y la propagación consciente de prerrequisitos mejoran la evidencia recuperada y el comportamiento pedagógico frente a RAG convencional?

## Condiciones controladas

Las tres condiciones comparten corpus, chunks, preguntas, generador, prompt, `top_k`, embedding inicial, BM25 y RRF. Solo cambia el mecanismo posterior a la recuperación inicial.

| Condición | Recuperación común | Intervención específica |
|---|---|---|
| RAG | Dense + BM25 + RRF | Ninguna estructura del grafo altera el ranking |
| Graph-RAG | Dense + BM25 + RRF | Expansión acotada, prerrequisitos y PPR |
| PEP-SA-RAG | Dense + BM25 + RRF | Grafo pedagógico y spreading activation iterativo |
| PEP-Plan-RAG v3 | Dense + BM25 + RRF | PPR + SA + estado del estudiante + plan de prerrequisitos + utilidad pedagógica |

Las ablaciones se configuran con `use_dense`, `use_sparse`, `use_neighbors`, `use_prerequisites`, `use_ppr` y los parámetros de activación. Una mejora genérica debe aplicarse a las tres condiciones.

## Datos y separación

Los conceptos iniciales se derivan de la taxonomía observable en el índice del corpus y se conectan mediante una hipótesis conservadora marcada `expert_curated`. Los textos generados o inferidos llevan procedencia explícita. El split se asigna determinísticamente; `test` no participa en reglas del retriever. Para resultados doctorales, la ontología, prerrequisitos y gold evidence deben someterse a validación humana independiente.

## Métricas

- Respuesta: exact match y token F1.
- Evidencia: Hit@K, Recall@K, MRR y nDCG@K.
- Estructura: Concept Recall y Prerequisite Recall.
- Eficiencia: latencia total, recuperación, grafo, dinámica, reranking y generación; nodos, aristas e iteraciones.
- Pedagogía futura: reconocimiento de dificultad, activación previa, scaffolding, micro-checks, coherencia y corrección mediante `PedagogicalEvaluator`.

La ausencia de anotación gold se serializa como `not_available`, nunca como un `NaN` silencioso. No se atribuirá causalidad ni superioridad a un método sin intervalos, tamaño muestral suficiente y resultados observados.

## Experimentos

1. Recuperación: C2–C4 con Hit@K, Recall@K, MRR, nDCG, Concept Recall y Prerequisite Recall.
2. Calidad matemática: C0–C4 mediante métricas auxiliares y rúbrica humana ciega.
3. Calidad pedagógica: diagnóstico, conocimiento previo, andamiaje, micro-checks, coherencia y adaptación.
4. Ablaciones: dense, BM25, RRF, vecinos, prerrequisitos, PPR y SA.
5. Robustez: paráfrasis, errores, ambigüedad, fuera de dominio e inyección de prompt.
6. Eficiencia: latencia por etapa, nodos, aristas e iteraciones.

Las respuestas se aleatorizarán y ocultarán la condición a los evaluadores. Se usarán comparaciones pareadas, intervalos de confianza, tamaños de efecto y acuerdo interevaluador.

## Evolución de PEP-SA-RAG

La versión `v1` se conserva en `configs/pep_sa_rag_v1.yaml`. Esta versión usa
propagación acotada y un reranking aditivo simple. La validación mostró que
podía activar prerrequisitos, pero que esa activación desplazaba evidencia
directa del contexto final.

La versión `v2`, configurada en `configs/pep_sa_rag_v2.yaml`, agrega:

1. reinyección de semillas mediante `query_restart`;
2. propagación direccional, favoreciendo prerrequisitos;
3. reranking normalizado con relevancia directa, activación, utilidad del
   prerrequisito y valor instruccional;
4. composición del contexto mediante cuotas configurables y adaptativas;
5. early stopping por estabilidad de la población superior.

V1 y v2 se ejecutan sobre las mismas preguntas. Las variantes de v2 se ajustan
solo sobre validación y la configuración elegida se congelará antes de test.
Los resultados negativos o trade-offs se conservan: una variante no reemplaza
retroactivamente el resultado de otra.

## Reproducibilidad

Cada fila guarda timestamp, commit, configuración, modelos, versión del dataset y semilla. El generador extractivo sirve para smoke tests sin red; los experimentos de calidad deben fijar un mismo proveedor/modelo para las tres condiciones.

## PEP-Plan-RAG v3

V3 prueba una hipótesis distinta: la activación poblacional es una señal útil,
pero no debería decidir sola qué evidencia recibe el LLM. Para cada documento
`d`, consulta `q` y estado de estudiante `s`, calcula una utilidad configurable:

`U(d|q,s) = αR + βPPR + γT + δNpre + εGs + ζM + ηI + θA − λRed`

Los términos representan relevancia directa, PageRank, cobertura del objetivo,
necesidad de prerrequisito, brecha del estudiante, concepción errónea, valor
instruccional, activación y redundancia. La selección mantiene un contexto
pequeño con evidencia directa, previa e instruccional. En la comparación neutral
se usa el perfil `unknown`; los perfiles sintéticos se reservan para evaluar
personalización y no dar una ventaja desigual en recuperación general.

El run de validación `pep-plan-v3-validation-135` incluye la comparación
principal, ablaciones y tres reformulaciones por pregunta. V3 mejoró Hit@5 frente
a v2 (0,5037 vs 0,4519), pero no superó Graph-RAG (0,5852). Esta diferencia se
conserva como resultado negativo/inconcluso y orienta la siguiente calibración.
