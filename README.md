# Tutor experimental de Precálculo

Plataforma reproducible para comparar RAG, Graph-RAG, PEP-SA-RAG y PEP-Plan-RAG v3 en un tutor LLM. Los notebooks y artefactos originales se conservan como referencia histórica; el código ejecutable vive en `src/ai_tutor`.

## Research question

¿Agregar estructura explícita de prerrequisitos y propagación dinámica mejora la recuperación de evidencia y el comportamiento pedagógico frente a RAG convencional?

## Arquitectura

Las tres condiciones comparten corpus, chunks, dense retrieval, BM25, RRF, preguntas, `top_k`, prompt y generador:

```text
RAG:        query → dense + BM25 → RRF ───────────────────→ evidence → tutor
Graph-RAG:  query → dense + BM25 → seeds → graph/PPR ─────→ evidence → tutor
PEP-SA-RAG: query → dense + BM25 → seeds → prerequisite SA → evidence → tutor
PEP-Plan v3: query → RAG + PPR + SA → student state → learning path → utility/context plan → tutor
```

El backend offline predeterminado usa embeddings hashing deterministas y generación extractiva. Es útil para reproducibilidad, tests y profiling, no se presenta como el modelo final de calidad.

## Setup

Python 3.9–3.12:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e '.[dev,pdf]'
cp .env.example .env
```

Las integraciones pesadas son opcionales: `dense`, `providers` y `pdf`. Gradio forma parte del núcleo porque `python app/chatbot.py` es un criterio operativo. No se fijó `grpcio`: el error de `grpcio 1.80.0` pertenece al entorno histórico y se evita en una instalación limpia del núcleo.

## Build

```bash
python scripts/build_dataset.py
python scripts/build_indexes.py
python scripts/build_graph.py
```

El constructor lee las páginas y los 639 marcadores del PDF porque la metadata de páginas de los chunks históricos estaba dañada. Produce 1.863 chunks con páginas reales, 448 conceptos, 448 unidades y 1.344 preguntas. No altera el PDF ni los artefactos históricos. Antes de una publicación, el contenido generado y las aristas inferidas deben validarse por expertos.

## Chatbot

```bash
python app/chatbot.py
```

La UI permite elegir `rag`, `graph_rag` o `pep_sa_rag` y activar el modo de investigación. Todas las condiciones usan exactamente `prompts/precalculus_tutor.txt`.

El selector **Generador** ofrece `instructional` (fallback offline), `openai`,
`local_base`, `local_finetuned`, `openai`, `gemini` y `deepseek`. Para respuestas naturales con un LLM, copie
`.env.example` a `.env`, configure una clave y seleccione el proveedor en la UI.
Los IDs de chunks solo aparecen en el panel de investigación, nunca en la
respuesta del estudiante.

La UI separa **modelo generador** y **acceso al conocimiento**. Esto permite
comparar el LLM open-source normal, el mismo LLM con RAG/Graph-RAG/PEP-SA-RAG,
y su adaptador fine-tuned bajo las mismas condiciones. Consulte la
[matriz open-source](docs/open-source-experimental-matrix.md).

## Evaluate

```bash
python scripts/evaluate.py --methods rag graph_rag pep_sa_rag
python scripts/evaluate.py --methods rag graph_rag pep_sa_rag --limit 5 --output data/evaluation/smoke_results.jsonl
python scripts/profile_retriever.py --method pep_sa_rag
pytest
```

Los resultados por pregunta contienen IDs de evidencia/conceptos, métricas de respuesta, Hit@K, Recall@K, MRR, nDCG, recalls estructurales, latencias, configuración, commit, modelos, versión y semilla.

## Reproduce experiments

1. Conserve sin cambios los YAML y dataset usados.
2. Reconstruya dataset, índices y grafo con los tres comandos de build.
3. Use el mismo generador y `top_k` para las tres condiciones.
4. Ejecute `scripts/evaluate.py` sobre `test`.
5. Archive el JSONL, configuración y commit registrados.

Consulte [estado inicial](docs/current_state.md) y [diseño experimental](docs/experimental_design.md). Los resultados históricos no demuestran superioridad de PEP-SA-RAG y no se reutilizan como benchmark nuevo.

El avance, la completitud del dataset y los pendientes se mantienen en el
[estado vivo del desarrollo](docs/development_status.md). Este documento debe
actualizarse con cada cambio relevante.

La explicación visual de la arquitectura, el grafo, la dinámica poblacional y
la presentación navegable de avances, diseño experimental y plan está disponible
en [research-overview.html](docs/research-overview.html).

El piloto inicial fija Gemini 3.6 Flash y compara cinco condiciones:

```bash
python scripts/evaluate_gemini_pilot.py --limit 30
```

La configuración completa está en `configs/gemini_pilot.yaml`.

### Experimentos masivos sin frontend

La ejecución recomendada sobre validación no llama al LLM y genera resultados
detallados, ablaciones, robustez, resúmenes e integra la tabla observada en la
presentación:

```bash
python scripts/run_mass_experiments.py \
  --stages retrieval ablations robustness \
  --split validation \
  --update-html
```

Para añadir generación con Gemini, limitada inicialmente a 30 preguntas:

```bash
python scripts/run_mass_experiments.py \
  --stages all \
  --split validation \
  --generation-limit 30 \
  --update-html
```

Cada ejecución crea un directorio versionado bajo `data/evaluation/runs/` con
manifest, JSONL por pregunta, CSV, resúmenes JSON y resultados parciales de
Gemini para permitir recuperación ante interrupciones. El split `test` exige
el indicador explícito `--confirm-test`.

PEP-SA-RAG mantiene dos configuraciones versionadas:

- `configs/pep_sa_rag_v1.yaml`: implementación histórica congelada;
- `configs/pep_sa_rag_v2.yaml`: query restart, propagación direccional,
  reranking híbrido y composición instruccional del contexto.

El pipeline masivo compara ambas versiones automáticamente para evitar perder
la trazabilidad de por qué se modificó el algoritmo.
