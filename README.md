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

La UI permite elegir `rag`, `graph_rag`, `pep_sa_rag` o `pep_plan_rag` y activar el modo de investigación. Todas las condiciones usan exactamente `prompts/precalculus_tutor.txt`.

### Nueva aplicación web

La experiencia preparada para evolucionar hacia nube está separada de Gradio:

```bash
pip install -e '.[web]'
python scripts/run_api.py
```

En otra terminal:

```bash
cd web
npm install
npm run dev
```

Visite `http://localhost:3000`. La interfaz de estudiante ofrece login,
conversaciones persistentes, respuesta progresiva, avatar y progreso sin exponer
la arquitectura experimental. La ruta `/admin` concentra las funciones de
investigación y requiere un ID incluido en `AI_TUTOR_RESEARCHER_IDS` antes del
registro. Consulte [la arquitectura web](docs/cloud_web_architecture.md) para
conocer límites actuales y decisiones pendientes de Azure.

Antes de entrar al tutor, cada cuenta debe leer y aceptar el protocolo de datos
en `/protocol`. La aplicación muestra el resumen y el PDF completo, mantiene el
botón de aceptación deshabilitado hasta marcar la casilla y bloquea desde el
backend el chat, actividades y perfil mientras no exista una aceptación vigente.
La versión se identifica con un hash del PDF; si cambia el documento se exige
una nueva aceptación. El registro persistido contiene el seudónimo, versión,
aceptación y fecha/hora UTC. El protocolo y su registro también pueden
consultarse desde el perfil del estudiante.

El chatbot guarda memoria local en `data/app/ai_tutor.sqlite3`. La interfaz
incluye registro/inicio de sesión seudónimo con PIN, conversaciones aisladas por
usuario, historial y continuidad de respuestas breves. Los PIN se almacenan como
PBKDF2-HMAC-SHA256 con sal aleatoria, nunca como texto. El archivo SQLite está
ignorado por Git y no debe contener nombres ni datos personales reales.

PEP-Plan-RAG v3 carga automáticamente el perfil longitudinal del usuario antes
del retrieval. El estudiante puede marcar `Lo entendí`, `Entendí parcialmente`
o `Necesito más ayuda`; esa evidencia explícita actualiza el dominio continuo
de los conceptos recuperados mediante:

```text
m_nuevo = m_anterior + alpha × (resultado - m_anterior)
```

Cada actualización conserva fuente, fecha, conversación, resultado y valor
anterior/nuevo. Además, el sistema detecta autorreportes conversacionales como
“ya entendí” o “no entiendo” con peso 0,25. Una respuesta matemática sin gold
se registra como evidencia no calificada, pero no cambia dominio hasta poder
verificar si es correcta. Para
habilitar una cuenta investigadora, incluya previamente su ID seudónimo en
`AI_TUTOR_RESEARCHER_IDS` dentro de `.env`; ese rol puede consultar perfiles e
historiales desde la pestaña **Investigación**.

Para recrear las cuentas locales de demostración de forma idempotente:

```bash
python scripts/seed_demo_users.py
```

El comando muestra los tres usuarios y PIN temporales. Estas credenciales son
únicamente para demostración local y deben retirarse antes de un piloto real.

La pestaña de comparación permanece sin memoria conversacional para que cada
condición reciba exactamente la misma pregunta aislada.

### Práctica guiada y evaluación

Después de una respuesta del tutor, la pestaña **Práctica guiada** puede crear
un micro-check asociado al concepto recuperado. Los validadores soportan
respuestas numéricas seguras, opciones y rúbricas por palabras clave. Cada
intento conserva respuesta, resultado, decisión pedagógica y dominio antes y
después. La política selecciona una de cinco acciones:

```text
advance | consolidate | hint | remediate_prerequisite | worked_example
```

Las preguntas sin una respuesta verificable no se presentan como correctas por
decisión del LLM: usan una rúbrica explícita o quedan como evidencia no calificada.

### Modelos locales open-source

La UI incluye `Qwen3-4B` y `Phi-4-mini` mediante un endpoint local compatible
con OpenAI, como Ollama, vLLM o LM Studio. Para comprobar disponibilidad:

```bash
python scripts/manage_local_models.py
```

Después de instalar Ollama, la descarga explícita es:

```bash
python scripts/manage_local_models.py --pull
```

Los pesos no se descargan automáticamente. Qwen3-4B y Phi-4-mini cuantizado
requieren varios GB de almacenamiento.

El selector **Generador** ofrece `instructional` (fallback offline), `openai`,
`local_base`, `local_finetuned`, `openai`, `gemini` y `deepseek`. Para respuestas naturales con un LLM, copie
`.env.example` a `.env`, configure una clave y seleccione el proveedor en la UI.
Los IDs de chunks solo aparecen en el panel de investigación, nunca en la
respuesta del estudiante.

La UI separa **modelo generador** y **acceso al conocimiento**. Esto permite
comparar el LLM open-source normal, el mismo LLM con RAG/Graph-RAG/PEP-SA-RAG,
y su adaptador fine-tuned bajo las mismas condiciones. Consulte la
[matriz open-source](docs/open-source-experimental-matrix.md).

El selector de modelo permanece visible en el chat. Si un proveedor interactivo
devuelve un error temporal (por ejemplo, Gemini 503), el tutor puede responder
con el generador local de respaldo y registra `requested_provider`,
`effective_provider`, `fallback_used` y el error original. Este reemplazo no se
usa silenciosamente en las comparaciones experimentales.

Los botones de comprensión son **auto-reportes**, no calificaciones: se guardan
en `student_self_reports` y no modifican el dominio. Un evaluador heurístico
independiente analiza la respuesta libre y registra clasificación, puntuación,
confianza y rasgos observados en `understanding_evaluations`. También se guarda
la concordancia o contradicción entre ambas señales. Los micro-checks con una
respuesta verificable continúan siendo evidencia de mayor calidad.

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
