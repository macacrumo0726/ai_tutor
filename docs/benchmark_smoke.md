# Smoke benchmark (2026-08-19)

Ejecución offline reproducible: cinco preguntas del split `test`, tres métodos, `top_k=5`, embedding hashing y generador extractivo. Este smoke test valida funcionamiento y latencia; **no es evidencia de calidad doctoral**.

| Método | N | Latencia total media (ms) | Recuperación media (ms) | Token F1 | Hit@5 |
|---|---:|---:|---:|---:|---:|
| RAG | 5 | 141.68 | 10.14 | 0.1193 | 0.20 |
| Graph-RAG | 5 | 216.00 | 81.25 | 0.1064 | 0.60 |
| PEP-SA-RAG | 5 | 161.33 | 14.06 | 0.1193 | 0.20 |

Perfil caliente aislado de PEP-SA-RAG: 20.80 ms totales; 3.19 ms de dinámica, 1.42 ms de reranking, 27 nodos, 38 aristas y 12 iteraciones. La implementación ya no exhibe latencias de cientos o miles de segundos. Graph-RAG obtuvo mayor Hit@5 en esta muestra, pero menor token F1; PEP-SA-RAG empató con RAG en ambas métricas observadas. No se infiere superioridad.

El archivo por pregunta es `data/evaluation/smoke_results.jsonl`. Las preguntas y gold evidence se generan a partir de la taxonomía inicial y requieren validación experta para un benchmark publicable.
