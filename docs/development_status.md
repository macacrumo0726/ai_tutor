# Estado vivo del desarrollo

> Documento de seguimiento de la plataforma doctoral de tutoría de Precálculo.
> Debe actualizarse cuando cambien el código, los datos, el grafo, las pruebas o
> los resultados experimentales.

**Última actualización:** 2026-08-20  
**Versión del dataset:** 1.0.0-corpus-draft  
**Estado general:** base corpus-wide completa estructuralmente; contenido generado e inferido pendiente de validación experta.

## 1. Alcance desarrollado

Se extrajo la implementación funcional de los notebooks históricos y se creó un
paquete Python reproducible. Los notebooks, el PDF y los artefactos originales
se conservan sin modificaciones.

La plataforma permite construir y comparar:

1. RAG: recuperación dense + BM25 + Reciprocal Rank Fusion.
2. Graph-RAG: RAG común + expansión del grafo + prerrequisitos + PPR.
3. PEP-SA-RAG: RAG común + grafo pedagógico + spreading activation.
4. PEP-Plan-RAG v3: Graph-RAG + spreading activation + estado del estudiante,
   ruta de aprendizaje y optimización de utilidad pedagógica del contexto.

Los tres métodos utilizan el mismo corpus, prompt, generador, preguntas y
parámetros comunes para preservar la comparabilidad experimental.

## 2. Base de datos basada en el libro

Existe una base reconstruida directamente desde las **1.014 páginas y 639
marcadores del PDF**. Los chunks históricos se preservan, pero dejaron de usarse
como fuente de metadata porque 1.792 de sus 1.794 filas estaban erróneamente
marcadas como un único rango de páginas 6-1014.

### Artefactos actuales

| Artefacto | Archivo | Cantidad |
|---|---|---:|
| Chunks documentales | `data/processed/chunks.jsonl` | 1.863 |
| Conceptos | `data/instructional/concepts.jsonl` | 448 |
| Unidades instruccionales | `data/instructional/instructional_units.jsonl` | 448 |
| Relaciones instruccionales | `data/instructional/relations.jsonl` | 702 |
| Preguntas | `data/evaluation/questions.jsonl` | 1.344 |
| Grafo pedagógico | `data/artifacts/pedagogical_graph.pkl` | 4.103 nodos / 8.088 aristas |
| Índices de recuperación | `data/artifacts/retrieval_indexes.pkl` | 1.863 documentos |

Los 448 conceptos tienen páginas y chunks fuente. Los chunks cubren los 13
capítulos académicos y conservan página, sección, tema, subtema, tipo y conceptos.

### Taxonomía inicial

La versión actual contiene 448 conceptos: 97 secciones y 351 subtemas extraídos
de la tabla de contenido real. Cubre fundamentos, funciones, polinomios,
exponenciales, logaritmos, trigonometría, coordenadas polares, vectores, sistemas,
cónicas, sucesiones, series y límites.

La selección no pretende afirmar que estos sean todos los conceptos del libro.
Es una ontología corpus-wide automatizada. Las relaciones de prerrequisito se marcan
como `expert_curated` porque son hipótesis pedagógicas explícitas, no citas
textuales extraídas del libro.

## 3. Diseño instruccional implementado

Cada concepto tiene el schema solicitado:

- identidad, nombre canónico, descripción, tema y subtema;
- dificultad y objetivo de aprendizaje;
- prerrequisitos y sucesores;
- palabras clave y alias;
- páginas y chunks fuente;
- procedencia de los campos.

Cada unidad instruccional incluye todos los campos estructurales definidos, pero
su nivel de completitud actual es el siguiente:

| Campo pedagógico | Completos | Estado |
|---|---:|---|
| Objetivo de aprendizaje | 448/448 | Generado y etiquetado |
| Explicación del concepto | 448/448 | Corpus |
| Pregunta diagnóstica | 448/448 | Generada y etiquetada |
| Pregunta de práctica | 448/448 | Corpus cuando fue detectable; si no, generada |
| Hint niveles 1–3 | 448/448 | Generados y etiquetados |
| Ejemplo resuelto | 448/448 | 175 extraídos; 273 scaffolds generados |
| Ejemplo guiado | 448/448 | Generado y etiquetado |
| Errores frecuentes | 448/448 | Inferidos y etiquetados |
| Solución | 448/448 | 175 extractos; 273 orientaciones generadas |

La base es **completa estructuralmente respecto a la taxonomía navegable del
libro**. “Completa” no significa “validada”: los campos generados, las relaciones
inferidas y las respuestas esperadas aún necesitan revisión experta.

## 4. Preguntas y splits

Los splits se asignan de forma determinista:

| Split | Preguntas |
|---|---:|
| Train | 1.074 |
| Validation | 135 |
| Test | 135 |

Cada pregunta incluye conceptos requeridos, prerrequisitos y gold IDs iniciales.
Estos gold labels sirven para validar la infraestructura, pero deben revisarse
manualmente antes de considerarse un benchmark doctoral.

## 5. Grafo pedagógico

El grafo nuevo contiene:

| Tipo de nodo | Cantidad |
|---|---:|
| Chunk | 1.863 |
| Concept | 448 |
| InstructionalUnit | 448 |
| Question | 1.344 |

| Tipo de relación | Cantidad |
|---|---:|
| EXPLAINS | 3.245 |
| MENTIONS | 2.797 |
| REQUIRES | 1.344 |
| PREREQUISITE_OF | 351 |
| NEXT_CONCEPT | 351 |

El grafo histórico tenía 117.548 aristas, incluidas 76.960 supuestas relaciones
de prerrequisito. Se conserva como referencia, pero no se trata como verdad
pedagógica por su densidad y falta de validación.

## 6. Validación técnica actual

- Instalación editable `pip install -e .`: validada.
- Construcción de dataset, índices y grafo: validada.
- Tests: **30 passed**.
- Smoke test: **5 preguntas × 3 métodos, 15/15 ejecuciones completadas**.
- Perfil caliente PEP-SA-RAG sobre 448 conceptos: 20,19 ms; dinámica poblacional 7,95 ms.

Estos resultados verifican funcionamiento y latencia. No prueban superioridad
pedagógica o estadística de ningún método.

## 7. Trabajo pendiente prioritario

1. Revisar manualmente los 448 conceptos, alias, prerrequisitos y confianza.
2. Validar los 175 ejemplos extraídos y reemplazar gradualmente los 273 scaffolds
   generados por ejemplos matemáticos revisados.
3. Revisar y balancear las 1.344 preguntas y sus respuestas esperadas.
4. Congelar el test antes de ajustar retrievers.
5. Evaluar embeddings multilingües con exactamente el mismo modelo en las tres
   condiciones.
6. Ejecutar el piloto controlado Gemini sobre 30 preguntas y revisar sus salidas.
7. Completar y validar proveedores DeepSeek y Hugging Face.
8. Resolver los conflictos del entorno histórico `grpcio`/`websockets` mediante
   un entorno limpio con Python 3.10–3.12.

## 8. Política de actualización

En cada cambio relevante se actualizarán:

- la fecha y versión del dataset;
- cantidades de entidades y relaciones;
- campos completos y pendientes;
- comandos y tests ejecutados;
- resultados observados, sin inventar mejoras;
- problemas conocidos;
- registro de cambios siguiente.

## 9. Registro de cambios

### 2026-08-20 — PEP-Plan-RAG v3

- Añadido un modelo explícito y no identificable del estudiante con perfiles
  reproducibles: desconocido, dominio alto, brecha de álgebra, brecha de
  prerrequisitos y posible concepción errónea.
- Implementado un planificador acotado que recorre hacia atrás las relaciones
  `PREREQUISITE_OF` y estima qué conocimientos requieren activación.
- Implementada una función de utilidad que combina relevancia directa, PPR,
  concepto objetivo, necesidad de prerrequisito, brecha de dominio,
  concepciones erróneas, valor instruccional y spreading activation.
- Añadido un selector codicioso de contexto con cuotas y penalización de
  redundancia, además de un plan tutorial visible en modo investigación.
- Integrada v3 en factory, tutor, frontend, comparación lado a lado, profiling,
  evaluación masiva, robustez y ablaciones.
- Ejecutado `pep-plan-v3-validation-135` sobre 135 preguntas de validación. V3
  obtuvo Hit@5 0,5037, Concept Recall 0,5259, Prerequisite Recall 0,7143 y
  59,65 ms. Superó a v1/v2 en Hit@5 y Concept Recall, pero Graph-RAG siguió
  liderando (0,5852; 0,6074; 0,7429). No se declara superioridad de v3.
- En robustez (405 consultas por método), v3 obtuvo Hit@5 0,4889 y Graph-RAG
  0,5580. Las ablaciones mostraron que quitar diversidad elevó Hit@5 a 0,5185;
  por tanto esa penalización requiere recalibración antes de congelar test.
- Suite técnica ampliada a 30 tests aprobados.
- Ampliada la presentación a 41 diapositivas con un protocolo explícito de
  evaluación multimétodo: métricas automáticas de recuperación, evaluación
  humana experta ciega y resultados de aprendizaje con estudiantes.
- Definidas para el benchmark personalizado las métricas Needed Prerequisite
  Recall, Unnecessary Prerequisite Rate, Learner-Context Alignment,
  Misconception Targeting y tasas de sobre/subandamiaje.
- Documentado un benchmark de perfiles contrastantes y el criterio de
  inferencia: no inferioridad documental frente a Graph-RAG más superioridad
  adaptativa, seguida de evaluación de respuestas y aprendizaje.
- Creada `docs/research-summary-slides.html`, una presentación ejecutiva de 12
  diapositivas con fórmulas y parámetros, diseño experimental, definición de
  métricas, gráficas de resultados observados, conclusiones y trabajo futuro.
- Simplificadas las diapositivas de algoritmos con explicaciones de qué hacen,
  cuál es su objetivo, qué limitación tienen y una frase breve para exposición.
  También se añadió una definición accesible de ablación y se reescribieron
  conclusiones y trabajo futuro en lenguaje de presentación.
- Añadida a la presentación resumida una diapositiva sobre el perfil de v3:
  dominio continuo entre 0 y 1, clasificación de brecha mediante umbral 0,65,
  ejemplo por concepto y aclaración de que la evaluación reportada utilizó el
  perfil neutral `unknown` con dominio base 0,50 y confianza 0,00.

### 2026-08-19 — Versión 0.1.0

- Auditoría y mapeo de notebooks a módulos.
- Creación del paquete Python, configuración y rutas relativas.
- Construcción inicial de chunks, conceptos, unidades y preguntas.
- Construcción del grafo pedagógico conservador.
- Implementación de RAG, Graph-RAG y PEP-SA-RAG.
- Implementación del tutor, UI, evaluación, profiling y visualizaciones base.
- Instalación editable validada.
- 11 tests aprobados.
- Smoke benchmark 5×3 completado.

### 2026-08-19 — Versión 1.0.0-corpus-draft

- Detectada y descartada como autoridad la metadata de página rota de los chunks históricos.
- Reconstruidos 1.863 chunks directamente desde páginas reales del PDF.
- Extraídos 448 conceptos de 97 secciones y 351 subtemas de los 13 capítulos.
- Generadas 448 unidades completas con procedencia por campo.
- Extraídos 175 ejemplos identificables; los demás campos se completaron como material generado claramente etiquetado.
- Generadas 1.344 preguntas en splits reproducibles.
- Creado `relations.jsonl` con 702 relaciones estructurales/inferidas.
- Migrado el grafo a `MultiDiGraph` para preservar tipos de relación paralelos.
- Regenerados índices y grafo; 13 tests aprobados.
- Añadida una explicación HTML interactiva de arquitecturas, grafo, dinámica,
  resultados observados y pruebas recomendadas.
- Ampliado el frontend con conversación persistente, selector de método, panel
  de investigación y comparación lado a lado.
- Sustituido el generador extractivo que copiaba chunks por un fallback
  instruccional legible; añadidos selectores OpenAI, Gemini y DeepSeek.
- Eliminados los IDs de chunks del prompt visible al estudiante y añadido un
  reranking común por tipo de contenido para reducir listas de ejercicios OCR.
- Separados en la UI los ejes `modelo` y `acceso al conocimiento`: modelo base,
  modelo fine-tuned, sin contexto, RAG, Graph-RAG y PEP-SA-RAG.
- Añadido cliente local OpenAI-compatible para Ollama/vLLM/SGLang/LM Studio.
- Generado dataset SFT de 1.344 conversaciones y script QLoRA; entrenamiento no
  ejecutado todavía porque requiere hardware CUDA y revisión previa del gold.
- Suite ampliada a 18 tests.
- Reorganizada la UI en cuatro ejes experimentales independientes: familia,
  adaptación, condición instruccional y retriever.
- Registradas Qwen3-8B, DeepSeek-R1-Distill-Qwen-7B, OpenAI, Gemini y DeepSeek
  API con capacidades reales de fine-tuning; combinaciones no disponibles se
  rechazan explícitamente.
- Actualizada la visualización HTML con matriz factorial y nueve familias de
  pruebas experimentales.
- Adoptado Gemini 3.6 Flash como generador inicial para el piloto, manteniendo
  fijos modelo, temperatura, preguntas, prompt y `top_k`.
- Añadidos `configs/gemini_pilot.yaml` y `scripts/evaluate_gemini_pilot.py` para
  comparar LLM normal, prompt pedagógico, RAG, Graph-RAG y PEP-SA-RAG.
- Convertida la presentación HTML en 15 diapositivas navegables, enfocadas en
  avances, diseño experimental, experimentos y plan de ejecución.
- Validada una llamada real a Gemini. La API informó que `gemini-2.5-flash` ya
  no está disponible para usuarios nuevos; se migró a `gemini-3.6-flash` y la
  conexión respondió correctamente (3.365 ms en la llamada mínima observada).
- Corregido el cliente Gemini para conservar el transporte HTTP durante la
  generación; antes podía cerrarse prematuramente al construirse inline.
- Ajustado el prompt y la capa de presentación para mostrar variables sin
  delimitadores LaTeX: `x` en lugar de `$x$`, con preferencia por símbolos
  Unicode legibles en el chat.
- Separada la salida instruccional en una respuesta conversacional para el
  estudiante y una traza pedagógica resumida para investigación. La traza se
  muestra en un panel paralelo y no expone cadena de pensamiento interna.
- Añadido un pipeline masivo sin frontend para recuperación, ablaciones,
  robustez y generación Gemini opcional. Cada run conserva manifest, detalle
  JSONL/CSV, resúmenes con bootstrap e inserta resultados observados en la
  presentación HTML; el split de test queda protegido por confirmación.
- Ejecutado `validation-full-135-v2`: las 135 preguntas de validación, tres
  retrievers, ocho ablaciones y tres reformulaciones de robustez (405 consultas
  por método). Graph-RAG obtuvo los mejores valores observados de Hit@5
  (0,5852), Concept Recall (0,6074) y Prerequisite Recall (0,7429). PEP-SA-RAG
  obtuvo 0,4222, 0,4222 y 0,6952 respectivamente; superó a RAG, pero no a
  Graph-RAG. Son resultados de validación y no evidencia final de test.
- Corregida la dinámica poblacional para respetar `max_hops`, `max_nodes` y
  `max_neighbors_per_node`; dejó de recorrer automáticamente los 448 conceptos.
- Congelada PEP-SA-RAG v1 como condición histórica reproducible y creada v2 con
  query restart, propagación direccional, reranking híbrido, cuotas de contexto
  y estabilidad del ranking.
- Ejecutado `pep-sa-v1-v2-validation-135`. Frente a v1, v2 aumentó Hit@5 de
  0,4222 a 0,4519, Concept Recall de 0,4222 a 0,4593 y Prerequisite Recall de
  0,6952 a 0,7238; redujo Recall@5 de 0,3556 a 0,2568 y nDCG@5 de 0,3222 a
  0,2439. Graph-RAG continuó liderando Hit@5 (0,5852).
- Las ablaciones mostraron un trade-off: retirar cuotas elevó Hit@5 de v2 a
  0,4889; pesos uniformes elevaron Concept Recall a 0,5037 y Prerequisite Recall
  a 0,7524. Estos resultados quedan como búsqueda de validación, no como test.
- Reorganizada la presentación doctoral en 32 diapositivas: problemática,
  vacío, objetivos, construcción de la base, formulaciones RAG/PPR/SA, controles,
  experimentos, interpretación de resultados, evolución v1/v2, protocolo con
  estudiantes, datos, instrumentos, ética, análisis y próximos pasos.
