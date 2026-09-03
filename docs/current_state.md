# Auditoría del estado inicial

Fecha: 2026-08-19. Esta auditoría precede a la refactorización y no elimina artefactos.

## Inventario

- Notebook principal: `notebooks/pep_sa_rag_precalculus_notebook_local_fixed.ipynb` (79 celdas, 54 de código).
- Notebook histórico: `notebooks/pep_sa_rag_precalculus_notebook_v2.ipynb` (66 celdas; conserva `NameError` para `G` y `df_eval_questions`).
- Corpus: `doctorado/libro/libro.pdf` (21 MB, 1003 páginas procesadas).
- Chunks históricos: 1794 filas y nueve columnas.
- Grafo histórico: `DiGraph`, 2228 nodos, 117548 aristas; 435 conceptos y 1792 chunks.
- Índices históricos FAISS/BM25, embeddings, CSV y gráficas se conservan en `doctorado/libro/output/pep_sa_rag_project`.
- Entorno inicial: Python 3.9.6, 148 distribuciones. `pip check` informó que `grpcio 1.80.0` no está soportado en la plataforma.

## Mapeo notebook → paquete

| Celdas / funciones principales | Nuevo módulo |
|---|---|
| 7–11: paths, limpieza, PDF, chunking | `utils.paths`, `ingestion.*`, `instructional.dataset_builder` |
| 14–15: embeddings, dense, BM25, RRF | `embeddings.encoder`, `indexing.*`, `retrieval.rag`, `retrieval.fusion` |
| 17–28: conceptos y prerrequisitos | `instructional.concepts`, `instructional.prerequisites` |
| 30: grafo heterogéneo | `graph.builder`, `graph.schema` |
| 32–35: seeds, vecinos, SA, PPR | `retrieval.graph_rag`, `graph.spreading_activation`, `graph.pagerank` |
| 37: PEP-SA-RAG | `retrieval.pep_sa_rag` |
| 39–43: contexto, prompt, generación | `prompts/`, `generation/`, `tutoring.tutor` |
| 45, 66, 70: métricas y reportes | `evaluation/` |
| 63–75: visualización | `visualization/` |

## Problemas y decisiones

1. Había rutas absolutas y ninguna configuración compartida. El paquete nuevo usa `pathlib` y YAML.
2. Varias funciones estaban redefinidas; la semántica dependía del orden de ejecución. Cada función nueva tiene una única ubicación.
3. Las 76960 aristas históricas `prerequisite_to` son excesivas para 435 conceptos y no constituyen gold data experto. No se migran como verdad pedagógica. Se conserva el archivo y se crea un grafo conservador con procedencia y confianza.
4. La evaluación histórica tiene 18 filas, exact match cero y `retrieval_hit` vacío. El nuevo schema exige gold IDs o produce el valor explícito `not_available`.
5. La latencia histórica de PEP-SA-RAG (~1153 s por caso) mezcla recuperación y generación remota. El profiler nuevo separa etapas y la propagación usa álgebra vectorizada, límites y early stopping.
6. Los chunks iniciales incluyen front matter y OCR ruidoso. Se preservan para comparabilidad; mejorar el filtrado deberá aplicarse a las tres condiciones.

## Dependencias

El `pyproject.toml` usa un núcleo pequeño. FAISS, modelos, PDF, UI y proveedores son extras. El backend por defecto usa embeddings hashing deterministas para permitir CI y experimentos offline; no pretende ser el embedding final del estudio.

