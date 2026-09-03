# Guion para explicar los algoritmos

## 1. Introducción a la comparación

> En esta investigación comparamos cuatro aproximaciones de recuperación. Todas
> trabajan con el mismo libro, los mismos fragmentos, las mismas preguntas y el
> mismo modelo generador.
>
> La diferencia está en cómo seleccionan la información que recibirá el tutor.
> La primera aproximación busca contenido parecido. La segunda añade relaciones
> entre conceptos. La tercera propaga activación hacia conocimientos relacionados
> y prerrequisitos. Finalmente, la cuarta incorpora el estado del estudiante para
> intentar seleccionar la evidencia que esa persona necesita.

---

## 2. RAG baseline

### Explicación oral

> RAG es nuestra línea base. Su objetivo es encontrar en el libro los fragmentos
> más relacionados con la pregunta del estudiante.
>
> Para hacerlo, utiliza dos tipos de búsqueda. La primera es *dense retrieval*.
> Esta convierte la pregunta y los fragmentos en vectores o *embeddings*. Así
> puede encontrar textos con significado parecido, incluso cuando no usan
> exactamente las mismas palabras.
>
> La segunda es BM25. Esta es una búsqueda léxica: identifica coincidencias
> importantes entre las palabras de la pregunta y las palabras del corpus.
>
> Por ejemplo, si el estudiante pregunta cómo encontrar el dominio de una
> función racional, *dense retrieval* puede encontrar explicaciones
> semánticamente relacionadas con dominio, mientras que BM25 puede localizar
> fragmentos que contienen literalmente las palabras “dominio”, “función” y
> “racional”.

### Fusión RRF

Después se combinan las dos listas mediante Reciprocal Rank Fusion:

$$
RRF(d)=\sum_r \frac{w_r}{k_{rrf}+\operatorname{rank}_r(d)}
$$

- `d`: fragmento del libro.
- `r`: cada ranking, por ejemplo dense o BM25.
- `rank`: posición del fragmento en esa lista.
- `w`: importancia asignada al ranking.
- `k_rrf`: suaviza la diferencia entre las primeras posiciones.

> Un fragmento recibe una puntuación mayor cuando aparece bien posicionado en
> una o en ambas búsquedas.

### Objetivo y limitación

> El objetivo de RAG es proporcionar evidencia relevante y reducir respuestas
> inventadas por el LLM. Su punto fuerte es que es rápido, sencillo y
> reproducible.
>
> Su limitación es que no conoce la estructura educativa. Puede recuperar
> directamente ecuaciones cuadráticas, pero no sabe que el estudiante podría
> necesitar primero factorización o la propiedad del producto cero.

**Frase corta:**

> RAG encuentra lo que más se parece a la pregunta.

---

## 3. Graph-RAG

### Qué se agrega

> Graph-RAG comienza con el mismo proceso de RAG. No reemplaza la búsqueda
> dense, BM25 ni RRF. Lo que agrega es un grafo de conocimiento.
>
> En este grafo tenemos nodos como conceptos, fragmentos, unidades
> instruccionales y preguntas. También tenemos relaciones como
> `PREREQUISITE_OF`, `RELATED_TO`, `EXPLAINS` y `REQUIRES`.
>
> Después de obtener los primeros resultados de RAG, identificamos qué conceptos
> aparecen en esos fragmentos. Estos conceptos se convierten en las semillas del
> recorrido por el grafo.

### Pipeline

```text
Pregunta
→ RAG
→ fragmentos semilla
→ conceptos semilla
→ expansión del grafo
→ Personalized PageRank
→ reranking
→ top-5
```

### Expansión controlada

- `max_hops`: cantidad máxima de saltos desde las semillas.
- `max_nodes`: cantidad máxima de nodos procesados.
- `max_neighbors_per_node`: número máximo de vecinos revisados por concepto.
- `use_neighbors`: activa o desactiva conceptos vecinos.
- `use_prerequisites`: activa o desactiva prerrequisitos.
- `use_ppr`: activa o desactiva Personalized PageRank.

> Estos límites evitan que una pregunta active una parte excesivamente grande
> del grafo.

### Personalized PageRank

$$
p(t+1)=\alpha Wp(t)+(1-\alpha)s
$$

- `p(t)`: importancia actual de cada nodo.
- `W`: conexiones posibles en el grafo.
- `s`: vector que concentra importancia en los conceptos semilla.
- `α`: cuánto se explora el grafo.
- `1−α`: probabilidad de volver a las semillas.

> En nuestra configuración, `α=0,85`. El método explora las conexiones, pero
> conserva un vínculo constante con la pregunta original.

### Reranking

$$
score(d)=score_{RAG}(d)+w_g\sum_{c\in d}PPR(c)
$$

`graph_weight`, representado por `w_g`, determina cuánto influye el grafo en el
ranking final.

### Objetivo y limitación

> El objetivo de Graph-RAG es recuperar no solo fragmentos textualmente
> parecidos, sino también evidencia conectada conceptualmente.
>
> Su punto fuerte es que actualmente ofrece la mejor recuperación general.
>
> Su limitación es que responde principalmente a la pregunta, no al estado
> particular del estudiante. Dos estudiantes que realizan la misma pregunta
> probablemente reciben contextos muy parecidos.

**Frase corta:**

> Graph-RAG busca en el libro y también en el mapa de relaciones.

---

## 4. PEP-SA-RAG v1

### Qué se agrega

> PEP-SA-RAG también parte del mismo RAG inicial y utiliza el grafo pedagógico.
> La diferencia es que sustituye PageRank como mecanismo principal por una
> dinámica de *spreading activation*.
>
> La idea es representar cada concepto como una población o unidad con cierto
> nivel de activación. Primero se activan los conceptos relacionados con la
> pregunta. Después esa activación se propaga hacia otros conceptos,
> especialmente hacia sus prerrequisitos.

### Ejemplo

> Si la pregunta trata sobre resolver una ecuación cuadrática, inicialmente se
> activa el concepto de ecuaciones cuadráticas. Después, parte de esa activación
> puede propagarse hacia factorización, propiedad del producto cero, operaciones
> algebraicas y ecuaciones.
>
> La intención es representar que algunos conocimientos deben activarse antes
> de trabajar adecuadamente con el concepto objetivo.

### Fórmula de activación

$$
a_i(t+1)=
\rho a_i(t)
+\lambda\sum_j W_{ij}a_j(t)
+\kappa s_i
-\delta a_i(t)
-\mu I_i(t)
$$

- `aᵢ(t)`: activación del concepto `i` en la iteración `t`.
- `ρ`, retention: proporción de activación que conserva.
- `λ`, propagation rate: cantidad de activación recibida de los vecinos.
- `Wᵢⱼ`: peso y tipo de conexión entre dos conceptos.
- `κsᵢ`, query restart: reinyección de la intención original.
- `δ`, activation decay: reducción gradual de activación.
- `μIᵢ`, inhibition: freno a conceptos poco útiles.

### Parámetros de control

- `activation_threshold`: elimina activaciones demasiado pequeñas.
- `max_iterations`: evita propagación indefinida.
- `top_population`: conserva solo los conceptos más activados.
- `early_stopping_tolerance`: detiene el proceso cuando casi no hay cambios.
- `ranking_stability_patience`: detiene el algoritmo cuando el ranking se estabiliza.
- `max_hops`, `max_nodes` y `max_neighbors_per_node`: limitan la región explorada.

### Pesos por relación

- `prerequisite_weight`: propagación hacia prerrequisitos.
- `related_weight`: propagación por relaciones laterales.
- `forward_successor_weight`: propagación hacia conceptos posteriores.

> Esto permite dar prioridad pedagógica a los conocimientos previos.

### Ranking de v1

$$
score(d)=score_{RAG}(d)+w_a\sum_{c\in d}a_c
$$

> En v1, la activación se sumaba directamente al score. El problema fue que una
> activación alta podía dominar la relevancia directa. El sistema encontraba
> prerrequisitos interesantes, pero podía desplazar la evidencia que respondía
> concretamente la pregunta.

**Frase corta:**

> PEP-SA v1 propaga importancia hacia lo que se necesita saber antes.

---

## 5. PEP-SA-RAG v2

### Razón para crear v2

> Observamos que activar buenos prerrequisitos no garantiza que sus fragmentos,
> junto con la evidencia directa, queden correctamente seleccionados. Por eso v2
> modifica cuatro componentes.

### 1. Query restart

> En cada iteración, una parte de la activación inicial vuelve a introducirse.
> Esto evita que la dinámica se aleje demasiado de la consulta. Cuanto mayor es
> `query_restart`, más anclado permanece el algoritmo a la pregunta.

### 2. Propagación direccional

> Las relaciones `PREREQUISITE_OF` reciben más peso que `RELATED_TO`. El flujo
> hacia sucesores se mantiene pequeño. Así se favorece el conocimiento previo
> sin expandirse indiscriminadamente hacia temas posteriores.

### 3. Reranking híbrido

$$
score(d)=\alpha D(d)+\beta A(d)+\gamma P(d)+\eta I(d)
$$

- `D(d)`: relevancia directa de RAG.
- `A(d)`: activación de los conceptos del fragmento.
- `P(d)`: utilidad como prerrequisito.
- `I(d)`: valor instruccional.

Parámetros correspondientes:

- `direct_relevance_weight`;
- `activation_rerank_weight`;
- `prerequisite_utility_weight`;
- `instructional_value_weight`.

### 4. Cuotas de contexto

- `direct_evidence_quota`: evidencia que responde directamente.
- `prerequisite_evidence_quota`: conocimiento previo.
- `instructional_evidence_quota`: definiciones, explicaciones o ejemplos.

> La intención es evitar que todos los fragmentos provengan de una sola
> categoría.

### Resultado de v2

> V2 mejoró Hit@5 frente a v1 y conservó una recuperación alta de
> prerrequisitos. Sin embargo, todavía quedó detrás de Graph-RAG y perdió parte
> de Recall y nDCG.
>
> Esto mostró que agregar estructura pedagógica no garantiza automáticamente un
> ranking documental superior.

**Frase corta:**

> PEP-SA v2 intenta equilibrar respuesta directa, prerrequisitos y material educativo.

---

## 6. PEP-Plan-RAG v3

### Por qué surge v3

> Ni PageRank ni spreading activation saben por sí mismos qué necesita una
> persona concreta. Por eso usamos Graph-RAG como generador de candidatos y la
> activación como una señal adicional. Después introducimos un modelo del
> estudiante y un planificador pedagógico.

V3 añade cuatro componentes:

1. Estado del estudiante.
2. Ruta de prerrequisitos.
3. Función de utilidad pedagógica.
4. Optimizador del contexto.

### Estado del estudiante

Incluye:

- dominio estimado por concepto;
- brechas conocidas;
- concepciones erróneas;
- confianza de la estimación;
- cantidad de evidencia observada.

Perfiles reproducibles actuales:

- estado desconocido;
- dominio alto;
- brecha de álgebra;
- brecha de prerrequisitos;
- posible concepción errónea.

### Ruta de aprendizaje

> El planificador parte del concepto objetivo y recorre el grafo hacia atrás.
> Compara los prerrequisitos con el dominio estimado del estudiante. Los
> conceptos cuyo dominio está por debajo de `mastery_threshold` se consideran
> posibles brechas.

```text
prerrequisito distante
→ prerrequisito inmediato
→ concepto objetivo
```

- `planning_max_depth`: profundidad máxima de la ruta.
- `planning_max_nodes`: máximo de conceptos examinados.
- `mastery_threshold`: dominio mínimo considerado suficiente.
- `max_target_concepts`: número de objetivos iniciales.

### Función de utilidad

$$
U(d\mid q,s)=
\alpha R+
\beta PPR+
\gamma T+
\delta N_{pre}+
\epsilon G_s+
\zeta M+
\eta I+
\theta A-
\lambda Red
$$

- `R`: relevancia directa con la pregunta.
- `PPR`: importancia estructural.
- `T`: cobertura del concepto objetivo.
- `Npre`: utilidad como prerrequisito necesario.
- `Gs`: correspondencia con una brecha del estudiante.
- `M`: utilidad para tratar una concepción errónea.
- `I`: valor instruccional del fragmento.
- `A`: spreading activation.
- `Red`: redundancia con fragmentos ya seleccionados.

> Las letras griegas son pesos configurables. No representan constantes
> universales: indican cuánto valor damos experimentalmente a cada señal.

### Selección del contexto

El selector intenta conservar:

- evidencia directa;
- evidencia de prerrequisitos;
- contenido instruccional;
- baja redundancia.

> La idea es que el contexto final no sea solamente relevante, sino útil para
> construir la intervención tutorial.

### Ejemplo con perfiles

Ante una pregunta sobre ecuaciones cuadráticas:

- Un estudiante con dominio alto puede recibir evidencia directa y verificación.
- Un estudiante con brecha en factorización puede recibir primero factorización y producto cero.
- Un estudiante con una concepción errónea puede recibir un contraejemplo y un micro-check diagnóstico.

### Resultado actual

> V3 mejora a RAG, v1 y v2 en Hit@5, pero todavía queda por debajo de
> Graph-RAG. Por tanto, hoy no podemos decir que sea el mejor recuperador.
>
> Su aporte potencial está en adaptar el contexto al estudiante. Esa ventaja
> requiere un benchmark específico y evaluación humana.

**Frase corta:**

> PEP-Plan v3 no pregunta solamente qué documento es relevante; pregunta qué evidencia es útil para este estudiante.

---

## 7. Qué son las ablaciones

> Una ablación consiste en quitar una pieza del algoritmo y repetir exactamente
> el mismo experimento.
>
> Es parecido a probar una receta retirando un ingrediente. Si al quitarlo el
> resultado empeora, el ingrediente ayudaba. Si no cambia, su aporte puede ser
> pequeño. Si mejora, probablemente estaba perjudicando la receta.

### Ejemplos ejecutados

- RAG solo dense.
- RAG solo BM25.
- Graph-RAG sin PPR.
- Graph-RAG solamente con prerrequisitos.
- PEP-SA sin query restart.
- PEP-SA sin cuotas.
- V3 sin activación.
- V3 sin brecha del estudiante.
- V3 sin utilidad de prerrequisitos.
- V3 sin penalización de redundancia.

### Interpretación actual

> Al quitar la activación de v3, Hit@5 permaneció igual, aunque nDCG bajó
> ligeramente. Esto indica que la activación puede ayudar al orden, pero su
> aporte todavía es pequeño.
>
> Al quitar la penalización de redundancia, Hit@5 mejoró. Esto indica que esa
> parte está demasiado fuerte o mal calibrada.
>
> Las ablaciones no buscan demostrar que todo funciona. Sirven para descubrir
> qué componentes ayudan, cuáles no y cuáles deben modificarse.

---

## 8. Cierre sugerido

> Los resultados muestran una progresión clara.
>
> RAG encuentra contenido parecido. Graph-RAG mejora la recuperación al utilizar
> relaciones conceptuales. PEP-SA incorpora una dinámica para activar
> prerrequisitos. PEP-Plan añade el estado del estudiante y convierte las
> señales anteriores en una decisión pedagógica.
>
> Actualmente Graph-RAG es el mejor recuperador general. PEP-Plan v3 es mejor
> que RAG y que las versiones anteriores de PEP-SA, pero todavía no supera a
> Graph-RAG.
>
> Por eso el siguiente paso no consiste únicamente en seguir ajustando pesos
> hasta obtener un número mayor. Debemos medir la pregunta que realmente
> diferencia nuestra propuesta: si el contexto seleccionado se adapta mejor a
> lo que cada estudiante sabe, no sabe o comprende incorrectamente.
>
> La contribución buscada sería demostrar que PEP-Plan mantiene una recuperación
> competitiva y, al mismo tiempo, mejora la adaptación, el andamiaje y finalmente
> el aprendizaje.
