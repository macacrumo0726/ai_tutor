# Experimento de retrieval con perfiles simulados

> Documento técnico preparado como fuente para una presentación de avances.
> Ejecución: `profiles-validation-full`, 17 de septiembre de 2026.

## Resumen ejecutivo

Esta prueba no pregunta solamente cuál método recupera más evidencia. Comprueba
si el retrieval responde de manera distinta y pedagógicamente razonable cuando
cambia el estado del estudiante, manteniendo constante la pregunta.

El resultado tiene dos partes:

1. **Calidad absoluta:** Graph-RAG obtuvo los mejores resultados tradicionales:
   Hit@5 `0,571`, Concept Recall `0,590` y Prerequisite Recall `0,743`.
2. **Adaptación:** solamente PEP-Plan-RAG v3 cambió el contexto según el perfil.
   Entre dominio alto y brecha cambió `15,9 %` del conjunto de evidencia,
   aumentó `2,9` puntos el recall de prerrequisitos y no presentó pérdida media
   del concepto objetivo.

Por tanto, esta ejecución no demuestra que v3 sea el mejor recuperador general.
Sí aporta evidencia funcional de que v3 implementa una recuperación sensible al
estado del estudiante, propiedad que RAG y Graph-RAG no tienen.

## Pregunta experimental

¿PEP-Plan-RAG v3 modifica el contexto recuperado cuando el estudiante tiene una
brecha de prerrequisitos, manteniendo la evidencia del concepto objetivo, a
diferencia de RAG y Graph-RAG?

### Hipótesis

- **H1 — invariancia de los controles:** RAG y Graph-RAG deben devolver el mismo
  contexto cuando sólo cambia el perfil, porque sus rankings no usan dominio.
- **H2 — sensibilidad de v3:** PEP-Plan debe cambiar parte de su contexto entre
  dominio alto y brecha.
- **H3 — dirección pedagógica:** ante una brecha, v3 debe aumentar la presencia
  o cobertura de los prerrequisitos necesarios.
- **H4 — conservación del objetivo:** esa adaptación no debe eliminar evidencia
  esencial del concepto preguntado.

No se formuló como hipótesis que v3 debía superar necesariamente a Graph-RAG en
las métricas documentales tradicionales.

## Diseño

- Split: validación; el test retenido no se utilizó.
- Muestra: las 105 preguntas de validación con prerrequisitos anotados.
- Métodos: RAG, Graph-RAG y PEP-Plan-RAG v3.
- `top_k`: 5.
- Diseño intra-pregunta: cada pregunta se ejecutó con los mismos tres perfiles.
- Variables constantes: consulta, corpus, índices, grafo, embeddings y `top_k`.
- No se utilizó un LLM generador: el experimento aísla el retrieval.

### Unidad de análisis y número de ejecuciones

La unidad de análisis es una combinación de:

```text
pregunta × método × perfil
```

Se utilizaron 105 preguntas, 3 métodos y 3 perfiles:

```text
105 × 3 × 3 = 945 ejecuciones de retrieval
```

Para el contraste causal principal se emparejó, dentro de cada pregunta, la
salida del perfil con dominio alto con la salida del perfil con brecha. De este
modo, la consulta, el gold y todos los componentes técnicos permanecen iguales.

### Métodos comparados

- **RAG:** dense retrieval + BM25 + fusión. No usa el grafo ni el perfil.
- **Graph-RAG:** parte de RAG y expande conceptos mediante vecinos,
  prerrequisitos y Personalized PageRank. No usa dominio del estudiante.
- **PEP-Plan-RAG v3:** combina recuperación directa, Graph-RAG, spreading
  activation, planificación de prerrequisitos y una utilidad dependiente de las
  brechas del estudiante.

De forma simplificada, v3 puntúa cada chunk mediante:

```text
U(chunk) = w_d·direct + w_g·PPR + w_t·target
         + w_p·prerequisite_need + w_s·student_gap
         + w_m·misconception + w_i·instructional + w_a·activation
```

El término diferencial es `student_gap`: un chunk asociado con un concepto de
bajo dominio puede recibir mayor utilidad. Después se selecciona un contexto de
cinco chunks conservando cuotas de evidencia directa, prerrequisitos y contenido
instruccional.

### Perfiles contrafactuales

1. `unknown`: dominio inicial 0,50 y sin evidencia previa.
2. `high_prerequisite_mastery`: dominio 0,90 en los prerrequisitos y conceptos
   objetivo de esa pregunta.
3. `prerequisite_gap`: dominio 0,10 en sus prerrequisitos y 0,55 en el objetivo.

Los perfiles de dominio alto y brecha son contrafactuales de la misma pregunta:
sólo cambia el estado simulado del estudiante. RAG y Graph-RAG reciben el perfil
pero conceptualmente deben ignorarlo; funcionan como controles de invariancia.

### Advertencia sobre el perfil simulado

Para construir el contraste se utilizaron los prerrequisitos gold de cada
pregunta. Esto es deliberado: prueba si el mecanismo responde correctamente
cuando el perfil contiene una brecha conocida. No representa todavía el caso
real, donde la brecha debe inferirse de pretest, conversación y micro-checks.
Los gold no se añadieron a RAG ni Graph-RAG para mejorar sus rankings.

### Procedimiento exacto

Para cada pregunta:

1. Se recuperaron sus conceptos objetivo, prerrequisitos y chunks gold.
2. Se construyeron los tres estados simulados.
3. Se ejecutó cada método con la misma consulta y `top_k=5`.
4. Se guardaron chunks, conceptos, prerrequisitos activados, latencia y métricas.
5. Se compararon de forma pareada dominio alto y brecha.
6. Se agregaron resultados mediante media aritmética sobre las 105 preguntas.

El split `test` permaneció intacto; se usó exclusivamente `validation`.

## Métricas

- `Hit@5`, `Recall@5`, `nDCG@5`: recuperación documental tradicional.
- `Concept Recall`: recuperación del concepto objetivo.
- `Prerequisite Recall`: recuperación o activación de prerrequisitos gold.
- `Prerequisite context share`: fracción del contexto final asociada a esos
  prerrequisitos.
- `Chunk Jaccard distance`: cuánto cambia el conjunto de chunks entre dominio
  alto y brecha; 0 significa que el perfil no tuvo efecto.
- `Prerequisite recall lift`: recall con brecha menos recall con dominio alto.
- `Target recall cost`: recall objetivo con dominio alto menos recall con brecha;
  cero o negativo indica que la adaptación no perjudicó el objetivo.

### Fórmulas e interpretación

Sea `R_k` el conjunto de resultados en las primeras `k` posiciones y `G` el
conjunto gold.

```text
Hit@K = 1 si R_k ∩ G ≠ ∅; de lo contrario 0

Recall@K = |R_k ∩ G| / |G|

Concept Recall = |conceptos recuperados ∩ conceptos gold| / |conceptos gold|

Prerequisite Recall =
  |prerrequisitos recuperados/activados ∩ prerrequisitos gold|
  / |prerrequisitos gold|
```

`nDCG@5` también considera la posición: recompensa que los chunks relevantes
aparezcan antes. Toma valores entre 0 y 1; mayor es mejor.

Para medir adaptación se utilizó la distancia de Jaccard entre los chunks del
perfil de dominio alto `C_alto` y los de brecha `C_brecha`:

```text
Jaccard distance = 1 - |C_alto ∩ C_brecha| / |C_alto ∪ C_brecha|
```

- `0`: exactamente el mismo contexto; no hubo adaptación observable.
- `1`: conjuntos completamente distintos.
- `0,159`: cambio parcial; aproximadamente 15,9 % en la escala agregada.

Los lifts se calcularon de forma pareada:

```text
Prerequisite Recall Lift = Recall_prereq(brecha) - Recall_prereq(alto)

Prerequisite Context Lift = Share_prereq(brecha) - Share_prereq(alto)

Target Recall Cost = ConceptRecall(alto) - ConceptRecall(brecha)
```

Un lift positivo de prerrequisitos es deseable. En `Target Recall Cost`, un
valor positivo implica deterioro; cero indica conservación y un valor negativo
indica que el perfil con brecha incluso recuperó mejor el objetivo.

## Resultados

### Resultados completos por perfil

| Método | Perfil | Hit@5 | Recall@5 | nDCG@5 | Concept Recall | Prerequisite Recall | Share prereq. | Latencia ms |
|---|---|---:|---:|---:|---:|---:|---:|---:|
| RAG | desconocido | 0,324 | 0,192 | 0,157 | 0,352 | 0,505 | 0,154 | 11,49 |
| RAG | dominio alto | 0,324 | 0,192 | 0,157 | 0,352 | 0,505 | 0,154 | 10,28 |
| RAG | brecha | 0,324 | 0,192 | 0,157 | 0,352 | 0,505 | 0,154 | 10,65 |
| Graph-RAG | desconocido | 0,571 | 0,346 | 0,317 | 0,590 | 0,743 | 0,200 | 16,85 |
| Graph-RAG | dominio alto | 0,571 | 0,346 | 0,317 | 0,590 | 0,743 | 0,200 | 12,87 |
| Graph-RAG | brecha | 0,571 | 0,346 | 0,317 | 0,590 | 0,743 | 0,200 | 12,48 |
| PEP-Plan v3 | desconocido | 0,476 | 0,308 | 0,270 | 0,505 | 0,714 | 0,215 | 58,63 |
| PEP-Plan v3 | dominio alto | 0,448 | 0,278 | 0,255 | 0,476 | 0,686 | 0,213 | 60,36 |
| PEP-Plan v3 | brecha | 0,476 | 0,311 | 0,275 | 0,514 | 0,714 | 0,229 | 58,52 |

### Tabla resumida para presentación

| Método | Perfil | Hit@5 | Concept Recall | Prerequisite Recall | Latencia ms |
|---|---|---:|---:|---:|---:|
| RAG | dominio alto | 0,324 | 0,352 | 0,505 | 10,28 |
| RAG | brecha | 0,324 | 0,352 | 0,505 | 10,65 |
| Graph-RAG | dominio alto | 0,571 | 0,590 | 0,743 | 12,87 |
| Graph-RAG | brecha | 0,571 | 0,590 | 0,743 | 12,48 |
| PEP-Plan v3 | dominio alto | 0,448 | 0,476 | 0,686 | 60,36 |
| PEP-Plan v3 | brecha | 0,476 | 0,514 | 0,714 | 58,52 |

| Método | Cambio de contexto | Lift prerrequisitos | Lift de contexto prerrequisito | Costo objetivo |
|---|---:|---:|---:|---:|
| RAG | 0,000 | 0,000 | 0,000 | 0,000 |
| Graph-RAG | 0,000 | 0,000 | 0,000 | 0,000 |
| PEP-Plan v3 | **0,159** | **+0,029** | **+0,015** | **-0,038** |

PEP-Plan cambió los chunks en 47 de 105 preguntas. Mejoró el recall de
prerrequisitos en 3 casos y no lo empeoró en ninguno. El recall del concepto
objetivo mejoró en 4 casos y no empeoró en ninguno. RAG y Graph-RAG no cambiaron
en ningún caso, como se esperaba.

## Qué significan concretamente los resultados

### 1. Graph-RAG recupera mejor en términos absolutos

Con perfil de brecha, Graph-RAG obtuvo Hit@5 `0,571`, frente a `0,476` de v3 y
`0,324` de RAG. Esto significa que Graph-RAG encontró al menos un chunk gold en
aproximadamente 57 de cada 100 preguntas. No debe afirmarse que v3 ya superó a
Graph-RAG en recuperación general.

### 2. RAG y Graph-RAG pasaron el control de invariancia

Sus listas de chunks fueron idénticas con dominio alto y brecha: distancia de
Jaccard `0`. Esto confirma que el protocolo mantuvo constante el retrieval para
los métodos que no deberían usar el perfil.

### 3. v3 sí respondió al perfil

La distancia media `0,159` y los cambios en 47 de 105 preguntas muestran que el
perfil entra efectivamente en la decisión de ranking/selección. No es sólo
metadata mostrada después de recuperar.

### 4. El cambio tuvo la dirección esperada, pero fue pequeño

El Prerequisite Recall pasó de `0,686` con dominio alto a `0,714` con brecha:
un incremento absoluto de `0,029`, aproximadamente 2,9 puntos porcentuales.
La proporción de chunks de prerrequisito pasó de `0,213` a `0,229`.

Sólo 3 de 105 pares mejoraron individualmente el recall de prerrequisitos; 102
quedaron iguales y ninguno empeoró. Por eso la señal es consistente en dirección
pero todavía limitada en cobertura.

### 5. No apareció el trade-off temido

Adaptar hacia prerrequisitos podría desplazar la evidencia principal. En esta
ejecución no ocurrió: el Concept Recall aumentó de `0,476` a `0,514`. Cuatro
preguntas mejoraron y ninguna empeoró. El costo objetivo medio fue `-0,038`, que
en esta convención representa una mejora, no un costo.

### 6. La adaptación tiene costo computacional

v3 tardó alrededor de `58,5–60,4 ms`, frente a `12,5–16,9 ms` de Graph-RAG y
`10,3–11,5 ms` de RAG. Sigue estando muy lejos de las latencias históricas de
cientos de segundos, pero es aproximadamente 4–5 veces más lento que Graph-RAG
en este entorno.

## Ejemplo conceptual de lectura

Supongamos una pregunta sobre raíces de una ecuación cuadrática:

- Con dominio alto en factorización y producto cero, v3 puede priorizar chunks
  directamente relacionados con la ecuación cuadrática.
- Con una brecha `0,10` en esos prerrequisitos, el término `student_gap` aumenta
  la utilidad de chunks que explican factorización o producto cero.
- La prueba verifica si esos chunks cambian, si cubren el prerrequisito gold y si
  se conserva contenido del concepto objetivo.

El experimento ejecutado hace este contraste automáticamente para cada una de
las 105 preguntas; el ejemplo sólo ilustra la lógica y no sustituye los datos.

## Conclusión provisional

Graph-RAG continúa siendo el mejor método del piloto en recuperación absoluta.
PEP-Plan v3 todavía no lo supera en Hit@5, Concept Recall ni Prerequisite Recall.
Sin embargo, v3 es el único método que reacciona al perfil: ante una brecha
asigna más contexto a prerrequisitos y mejora su recall sin pérdida observada
del objetivo. Éste es un resultado de **adaptación del retrieval**, no evidencia
de ganancia de aprendizaje.

### Estado de las hipótesis

| Hipótesis | Resultado | Evidencia |
|---|---|---|
| H1: controles invariantes | Compatible | Jaccard `0` para RAG y Graph-RAG |
| H2: v3 sensible al perfil | Compatible | Jaccard `0,159`; 47/105 contextos cambiaron |
| H3: dirección pedagógica | Compatible, efecto pequeño | lift prereq. `+0,029`; 3 mejoras, 0 deterioros |
| H4: conservar objetivo | Compatible | costo `-0,038`; 4 mejoras, 0 deterioros |

“Compatible” se usa deliberadamente: sin intervalos de confianza pareados ni
validación humana no corresponde afirmar confirmación estadística definitiva.

## Qué puede y qué no puede concluirse

### Sí puede afirmarse

- Graph-RAG fue el mejor recuperador absoluto en esta ejecución.
- PEP-Plan v3 fue el único método sensible al perfil simulado.
- La adaptación observada se orientó hacia prerrequisitos y no redujo el recall
  objetivo en la muestra agregada.
- El pipeline permite medir por separado recuperación general y personalización.

### Todavía no puede afirmarse

- Que v3 produzca mejores respuestas del LLM.
- Que v3 genere mayor aprendizaje, retención o transferencia.
- Que el efecto se mantenga con perfiles inferidos de estudiantes reales.
- Que la diferencia sea estadísticamente significativa.
- Que los gold sean perfectos antes de una revisión experta.

## Limitaciones y siguiente prueba

- Se requieren intervalos de confianza pareados y revisión por subtema antes de
  congelar parámetros.
- Los perfiles son simulados y utilizan prerrequisitos gold; esto sirve para
  validar el mecanismo, no para estimar desempeño con perfiles inferidos.
- La calidad del gold proviene de alineación corpus-estructura y requiere
  revisión experta.
- La siguiente fase debe usar perfiles estimados a partir de pretest y comparar
  calidad pedagógica ciega, micro-checks y ganancia pretest–postest.

### Próximos análisis recomendados

1. Calcular intervalos de confianza bootstrap pareados y pruebas de permutación.
2. Desagregar por tema, tipo de pregunta, profundidad del prerrequisito y
   cantidad de prerrequisitos gold.
3. Analizar por qué sólo 3 preguntas mejoraron el Prerequisite Recall aunque 47
   cambiaron de contexto: parte del cambio puede ocurrir entre chunks no gold.
4. Ejecutar una ablación sin `student_gap` para atribuir el cambio específicamente
   al perfil y no a otro componente de v3.
5. Añadir generación con el mismo LLM y evaluación ciega de corrección,
   scaffolding, activación de conocimiento previo y micro-checks.
6. Sustituir perfiles gold por perfiles inferidos del pretest y comparar su
   precisión con codificación humana.
7. En estudio con alumnos, medir pretest, postest, retención, tiempo, pistas,
   errores y experiencia percibida.

## Artefactos y reproducibilidad

- Resultados por ejecución: `profile_results.jsonl` y `profile_results.csv`.
- Resumen por método/perfil: `profile_summary.csv`.
- Contraste pareado: `counterfactual_summary.csv`.
- Manifest y resumen legible por máquina: `summary.json`.
- Código del experimento: `scripts/run_profile_experiment.py`.
- Implementación de métricas: `src/ai_tutor/experiments/profile_experiment.py`.
- Validación automatizada: `tests/test_profile_experiment.py`.

Los resultados completos están en
`data/evaluation/runs/profiles-validation-full/` y pueden reproducirse con:

```bash
python scripts/run_profile_experiment.py --split validation --limit 105 --top-k 5 --run-id profiles-validation-full
```

La suite completa después de incorporar el experimento reportó **57 tests
aprobados**.

## Propuesta de estructura para la futura presentación

1. Problema: recuperar evidencia no equivale a adaptarse al estudiante.
2. Pregunta e hipótesis del experimento.
3. Diferencia entre RAG, Graph-RAG y PEP-Plan v3.
4. Diseño contrafactual y perfiles simulados.
5. Métricas tradicionales y métricas de adaptación.
6. Resultado de recuperación absoluta: ventaja de Graph-RAG.
7. Resultado de sensibilidad al perfil: ventaja diferencial de v3.
8. Costo computacional y trade-offs.
9. Qué se concluye y qué no.
10. Siguiente fase con generación y estudiantes reales.
