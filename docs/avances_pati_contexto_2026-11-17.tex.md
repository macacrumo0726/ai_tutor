```latex
\documentclass[10pt,aspectratio=169]{beamer}
\usetheme{Madrid}
\usecolortheme{default}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb,booktabs,xcolor,tikz}
\usetikzlibrary{arrows.meta,positioning,calc}

\definecolor{patiBlue}{RGB}{24,67,120}
\definecolor{patiMid}{RGB}{49,105,168}
\definecolor{patiLight}{RGB}{232,241,251}
\setbeamercolor{structure}{fg=patiBlue}
\setbeamercolor{frametitle}{bg=patiBlue,fg=white}
\setbeamercolor{title}{fg=patiBlue}
\setbeamercolor{block title}{bg=patiBlue,fg=white}
\setbeamercolor{block body}{bg=patiLight,fg=black}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}[frame number]

\title[PATI: avances de implementación]{PATI: contexto, guardrails y tutoría paso a paso}
\subtitle{Avances recientes, arquitectura final y validación de desempeño}
\author{M. Cruz, F. Lozano, A. Gonzalez}
\institute{Universidad de Los Andes, Colombia}
\date{20 de noviembre de 2026}

\begin{document}
\begin{frame}\titlepage\end{frame}

\begin{frame}{1. Cambio implementado: del historial al estado activo}
\small
\begin{columns}[T]
\column{0.48\textwidth}
\textbf{Problema detectado}
\begin{itemize}
  \item El tutor recibía historial y evidencia, pero no distinguía el ejercicio vigente del anterior.
  \item ``Resuélvelo tú'' podía activar un ejercicio nuevo.
  \item ``No, ya sé que da 0'' podía interpretarse como duda y repetir la comprobación.
\end{itemize}
\column{0.48\textwidth}
\textbf{Corrección}
\begin{itemize}
  \item Cada actividad guarda su expresión, tipo, pregunta pendiente y siguiente acción.
  \item El controlador decide primero el significado del turno.
  \item El LLM redacta la respuesta cuando la decisión no es inequívoca.
\end{itemize}
\end{columns}
\vspace{3mm}
\begin{block}{Resultado observable}
El modelo puede conversar con naturalidad, pero el sistema ya no le pide inferir
por sí solo qué ejercicio está abierto ni qué paso pedagógico sigue.
\end{block}
\end{frame}

\begin{frame}{2. Arquitectura final del tutor}
\small
\begin{center}
\begin{tikzpicture}[font=\scriptsize,node distance=5mm and 7mm,
  box/.style={draw=patiBlue,rounded corners=2pt,fill=patiLight,minimum height=11mm,text width=27mm,align=center},
  arrow/.style={-{Latex[length=2mm]},thick,patiBlue}]
\node[box] (ui) {Next.js\\tutor y admin};
\node[box,right=of ui] (api) {FastAPI\\sesión y protocolo};
\node[box,right=of api] (memory) {ConversationMemory\\estado activo};
\node[box,below=of memory] (router) {Router conversacional\\ML + reglas de estado};
\node[box,left=of router] (pep) {PEP-Plan-RAG v3\\dense + BM25 + grafo};
\node[box,right=of router] (llm) {GPT principal\\fallback local};
\node[box,right=of llm] (guard) {Guardrails\\respuesta y evidencia};
\node[box,below=of guard] (db) {PostgreSQL\\turnos y métricas};
\node[box,below=of pep] (kb) {Base instruccional\\chunks, conceptos, índices};
\draw[arrow](ui)--(api)--(memory);
\draw[arrow](memory)--(router);
\draw[arrow](router)--(pep);
\draw[arrow](kb)--(pep);
\draw[arrow](router)--(llm)--(guard)--(db);
\draw[arrow](db.south) |- (memory.south);
\end{tikzpicture}
\end{center}
\vspace{2mm}
\textbf{Principio:} PEP v3 selecciona evidencia; el estado selecciona la acción
pedagógica; el LLM convierte ambas señales en una respuesta conversacional.
\end{frame}

\begin{frame}{3. Memoria y lógica de contexto}
\small
\begin{center}
\begin{tikzpicture}[font=\scriptsize,node distance=5mm and 8mm,
  item/.style={draw=patiBlue,rounded corners=2pt,fill=patiLight,minimum height=9mm,text width=32mm,align=center},
  arrow/.style={-{Latex[length=2mm]},thick,patiBlue}]
\node[item](turn){turno actual};
\node[item,right=of turn](state){estado pedagógico};
\node[item,right=of state](query){consulta compacta};
\node[item,right=of query](evidence){evidencia PEP v3};
\node[item,below=of state](answer){respuesta y siguiente acción};
\draw[arrow](turn)--(state)--(query)--(evidence);
\draw[arrow](evidence)--(answer);
\draw[arrow](answer)--(state);
\end{tikzpicture}
\end{center}
\vspace{2mm}
\begin{center}
\begin{tabular}{ll}
\toprule
Campo & Ejemplo\\
\midrule
\texttt{exercise\_expression} & $x^2+5x+6$\\
\texttt{pending\_kind} & factorización\\
\texttt{expected\_response\_type} & intento del estudiante\\
\texttt{next\_action} & comprobar suma y producto\\
\texttt{last\_step\_closed} & verdadero / falso\\
\bottomrule
\end{tabular}
\end{center}
\textbf{Efecto:} ``3 y 2'' se interpreta contra el ejercicio activo, no contra todo el historial.
\end{frame}

\begin{frame}{4. Módulos de guardrails implementados}
\scriptsize
\begin{tabular}{p{3.2cm}p{5.0cm}p{5.0cm}}
\toprule
\textbf{Módulo} & \textbf{Qué controla} & \textbf{Lógica utilizada}\\
\midrule
\texttt{response\_verifier.py} & Respuestas matemáticas cortas & Denominadores, pares de factores, factores escritos como $x+2$ y variables comunes.\\
\texttt{conversation/controller.py} & Intención y tipo de turno & Centroides sobre hashing; margen de confianza y estado pendiente.\\
\texttt{services.py} & Transiciones pedagógicas & Comprobar, rechazar, continuar o resolver una actividad.\\
\texttt{Tutor.ask} & Evidencia y prompt & Limita chunks y separa estado, historial, evidencia y traza.\\
\texttt{llm\_guardrail.py} & Segunda revisión opcional & DeepSeek revisa respuestas ambiguas del proveedor principal.\\
\texttt{\_response\_passes\_guardrails} & Salida final & Idioma, fuga de prompt, relevancia y ejercicio accionable.\\
\bottomrule
\end{tabular}
\vspace{3mm}
\begin{block}{Criterio}
Los guardrails bloquean errores de estado o matemática y dejan al LLM la explicación,
el tono y la transición natural.
\end{block}
\end{frame}

\begin{frame}{5. Lógica matemática para factorización}
\small
Para $x^2+bx+c$, el verificador busca $r_1,r_2$ tales que:
\[
r_1+r_2=b,\qquad r_1r_2=c,\qquad x^2+bx+c=(x+r_1)(x+r_2).
\]
\begin{columns}[T]
\column{0.48\textwidth}
\textbf{Intentos reconocidos}
\begin{itemize}
  \item ``4 y 3''
  \item ``-3 y -4''
  \item ``x+2 y x+3''
  \item ``(x-3)(x-4)''
\end{itemize}
\column{0.48\textwidth}
\textbf{Salida pedagógica}
\begin{itemize}
  \item calcula suma y producto del intento;
  \item indica qué condición falla;
  \item muestra el par correcto;
  \item ofrece comprobar o continuar.
\end{itemize}
\end{columns}
\vspace{3mm}
Esto evita que el LLM acepte una respuesta incorrecta solo porque suena plausible
y evita mezclar dos polinomios consecutivos.
\end{frame}

\begin{frame}{6. Modelos implementados y arquitectura LLM}
\tiny
\begin{center}
\begin{tikzpicture}[font=\tiny,node distance=2.5mm and 2.7mm,
  box/.style={draw=patiBlue,rounded corners=1.5pt,fill=patiLight,
    minimum height=7mm,text width=18mm,align=center,inner sep=1.5pt},
  fallback/.style={box,draw=patiMid,fill=patiBlue!8},
  arrow/.style={-{Latex[length=1.6mm]},thick,patiBlue}]
\node[box] (question) {Pregunta del\\estudiante};
\node[box,right=of question] (memory) {Memoria + estado\\pedagógico};
\node[box,right=of memory] (pep) {PEP-Plan-RAG v3\\selecciona evidencia};
\node[box,right=of pep] (context) {Contexto educativo\\seleccionado};
\node[box,right=of context] (gpt) {GPT principal\\GPT-4.1-mini};
\node[box,right=of gpt] (guard) {Guardrails\\deterministas};
\node[box,right=of guard] (answer) {Respuesta visible\\al estudiante};
\draw[arrow] (question) -- (memory) -- (pep) -- (context) -- (gpt) -- (guard) -- (answer);

\node[fallback,below=4mm of gpt] (provider) {Proveedor fallback\\configurado};
\node[fallback,left=of provider,text width=22mm] (failure) {GPT falla, responde vacío\\o fuera de contexto};
\node[fallback,right=of provider,text width=23mm] (models) {DeepSeek o modelo local\\Qwen/Ollama};
\draw[arrow] (gpt) -- (failure);
\draw[arrow] (failure) -- (provider) -- (models);
\draw[arrow] (models.east) -| (guard.south);
\node[fallback,below=of provider,text width=29mm] (emergency) {Instructional emergency fallback\\determinista y local};
\draw[arrow,dashed] (provider) -- node[right,font=\tiny]{si todos fallan} (emergency);
\draw[arrow,dashed] (emergency.east) -| (guard.south);
\end{tikzpicture}
\end{center}

\vspace{-1mm}
\begin{columns}[T,onlytextwidth]
\column{0.50\textwidth}
\textbf{Responsabilidad de cada componente}
\vspace{0.5mm}

\begin{tabular}{p{2.55cm}p{5.05cm}}
\toprule
\textbf{Componente} & \textbf{Función}\\
\midrule
PEP-Plan-RAG v3 & Selecciona la evidencia educativa; no genera la respuesta.\\
GPT-4.1-mini & Redacta la explicación pedagógica.\\
Guardrails & Verifican idioma, relevancia, fugas y coherencia.\\
DeepSeek & Revisión opcional o fallback.\\
Qwen/Ollama & Fallback local.\\
Instructional fallback & Garantiza disponibilidad.\\
\bottomrule
\end{tabular}

\column{0.48\textwidth}
\textbf{PEP v3 recupera:} chunks, conceptos, prerrequisitos, activaciones,
plan pedagógico y estado del estudiante.

\vspace{1mm}
\textbf{GPT-4.1-mini recibe:} pregunta actual, estado conversacional, perfil del
estudiante, evidencia recuperada por PEP v3 y prompt pedagógico.

\vspace{1mm}
\textbf{DeepSeek tiene dos funciones posibles:} proveedor fallback o segundo
verificador opcional de la respuesta de otro modelo. No se ejecuta siempre después de GPT.

\vspace{1mm}
Si todos los proveedores fallan, la respuesta determinista local mantiene disponible
el tutor. Los errores técnicos quedan en logs y metadata; no se muestran al estudiante.
\end{columns}

\vspace{1mm}
\begin{block}{Control experimental}
\tiny \textbf{Idea central:} PEP v3 decide qué conocimiento necesita el estudiante;
GPT lo explica; los guardrails verifican la respuesta; y los fallbacks mantienen disponible el tutor.\\
La comparación entre modelos LLM mantiene constante el retrieval: mismo corpus,
PEP v3, top-$k$, estado pedagógico y prompt. La única variable modificada es el
generador o el fallback.
\end{block}
\end{frame}

\begin{frame}{7. Persistencia y panel administrativo}
\small
\begin{center}
\begin{tikzpicture}[font=\scriptsize,node distance=6mm and 9mm,
  box/.style={draw=patiBlue,rounded corners=2pt,fill=patiLight,minimum height=10mm,text width=34mm,align=center},
  arrow/.style={-{Latex[length=2mm]},thick,patiBlue}]
\node[box](tutor){Tutor};
\node[box,right=of tutor](api){API autenticada};
\node[box,right=of api](pg){PostgreSQL};
\node[box,below=of pg](admin){Panel admin};
\draw[arrow](tutor)--(api)--(pg)--(admin);
\end{tikzpicture}
\end{center}
\begin{itemize}
  \item PostgreSQL guarda usuarios, mensajes, estado, modelos, retrieval, latencia y evidencias.
  \item El panel consulta la misma base que utiliza el tutor.
  \item El usuario investigador tenía 12 conversaciones y estaba oculto por el filtro de cuentas de demostración.
  \item Ahora aparecen investigador, estudiantes demo y ``test''; se excluyen solo cuentas efímeras de carga.
\end{itemize}
\end{frame}

\begin{frame}{8. Pruebas de desempeño y latencia}
\scriptsize
\begin{tabular}{p{4.0cm}p{3.0cm}p{6.0cm}}
\toprule
\textbf{Prueba} & \textbf{Resultado} & \textbf{Qué demuestra}\\
\midrule
Suite de regresión & 149/149 pasan & Integración de router, memoria, verificador, API y panel.\\
Banco conversacional & 100/100 válidos & Diez conversaciones y diez temas sin deriva en el banco.\\
Graph-RAG ($n=135$) & Hit@5=.5852; prereq=.7429 & Mejor recuperación del benchmark en esta ejecución.\\
PEP-Plan v3 ($n=135$) & Hit@5=.5037; prereq=.7143 & Añade perfil y planificación, aunque no lidera todas las métricas.\\
Latencia retrieval v3 & 59.65 ms & Coste de planificación, utilidad y selección de evidencia.\\
\bottomrule
\end{tabular}
\vspace{3mm}
\begin{center}
\begin{tikzpicture}[x=0.0012cm,y=0.42cm,font=\scriptsize]
\draw[->](0,0)--(19000,0) node[right]{milisegundos};
\foreach \x/\label in {0/0,5000/5k,10000/10k,15000/15k,19000/19k}
  \draw (\x,0.08)--(\x,-0.08) node[below]{\label};
\fill[patiBlue](0,0.45) rectangle (1032,0.85) node[pos=0.5,white]{Qwen 1.7B};
\fill[patiMid](0,1.15) rectangle (6226,1.55) node[pos=0.5,white]{Phi-4 mini};
\fill[patiBlue!55](0,1.85) rectangle (17747,2.25) node[pos=0.5,white]{Qwen 4B};
\end{tikzpicture}
\end{center}
\scriptsize Smoke tests locales: Qwen 1.7B = 1031.8 ms, Phi-4 mini = 6225.9 ms,
Qwen 4B = 17746.5 ms. El banco conversacional incluye fallback instruccional;
no es una medición de red de GPT.
\end{frame}

\begin{frame}{9. Pruebas de carga y resiliencia}
\scriptsize
\begin{tabular}{r r r r r p{3.8cm}}
\toprule
\textbf{Concurrencia} & \textbf{Solicitudes} & \textbf{Éxitos} & \textbf{Fallbacks} & \textbf{p95} & \textbf{Lectura}\\
\midrule
1 & 1 & 1/1 & 0 & 19.6 s & operación nominal\\
3 & 3 & 3/3 & 1 & 21.7 s & primera espera controlada\\
5 & 5 & 5/5 & 3 & 22.0 s & disponibilidad preservada\\
10 & 10 & 10/10 & 8 & 22.1 s & saturación absorbida por fallback\\
\bottomrule
\end{tabular}
\vspace{3mm}
\begin{columns}[T]
\column{0.48\textwidth}
\textbf{Mecanismos implementados}
\begin{itemize}
  \item semáforo de generaciones concurrentes;
  \item cola con timeout configurable;
  \item fallback local de emergencia;
  \item errores técnicos sólo en logs y metadata.
\end{itemize}
\column{0.48\textwidth}
\textbf{Interpretación}
\begin{itemize}
  \item La prueba inicial con el proveedor externo llegó a 429 con concurrencia 10.
  \item La versión resiliente terminó 10/10 solicitudes sin error visible.
  \item Debe medirse por separado la calidad de respuestas generadas por fallback.
\end{itemize}
\end{columns}
\vspace{2mm}
\scriptsize Fuente: \texttt{docs/resilience\_load\_test.md} y
\texttt{data/evaluation/load\_test\_chat\_context\_v2.json}.
\end{frame}

\begin{frame}{10. Productos científicos en construcción}
\small
\begin{columns}[T]
\column{0.48\textwidth}
\begin{block}{Artículo orientado al tutor}
\textbf{PATI: A Context-Aware LLM Tutor for Pedagogically Guided Precalculus Learning}
\end{block}
\begin{itemize}
  \item Arquitectura web y memoria conversacional.
  \item Guardrails, rutas de aprendizaje y personalización.
  \item Evaluación de naturalidad, andamiaje, usabilidad y aprendizaje.
\end{itemize}
\column{0.48\textwidth}
\begin{block}{Artículo orientado al retrieval}
\textbf{Beyond Semantic Similarity: A Comparative Study of Prerequisite-Aware Retrieval for LLM-Based Precalculus Tutors}
\end{block}
\begin{itemize}
  \item Comparación RAG, Graph-RAG y PEP-Plan-RAG v3.
  \item Ablaciones, recall conceptual y de prerrequisitos.
  \item Latencia, costo y reproducibilidad experimental.
\end{itemize}
\end{columns}
\vspace{3mm}
\begin{block}{Estrategia posterior para revista}
La versión de revista ampliará el trabajo de retrieval con el experimento completo con estudiantes,
análisis pedagógico, nuevas ablaciones y una descripción técnica más extensa; no repetirá únicamente el artículo de conferencia.
\end{block}
\end{frame}

\begin{frame}{11. Estado actual y siguiente medición}
\small
\begin{block}{Estado actual}
PATI combina PEP-Plan-RAG v3, estado conversacional explícito, verificadores
matemáticos y un LLM generador. La respuesta visible mantiene un estilo natural;
la traza técnica queda en la base de datos.
\end{block}
\begin{itemize}
  \item 149 pruebas automatizadas pasan.
  \item El banco de 100 turnos alcanzó 100\% de turnos válidos.
  \item La persistencia del investigador y del estudiante es consultable desde admin.
  \item El siguiente paso es medir continuidad, andamiaje y prerrequisitos con estudiantes reales.
\end{itemize}
\vfill
\centering
\textcolor{patiBlue}{El avance central: controlar el contexto sin quitarle al LLM la fluidez de la conversación.}
\end{frame}
\end{document}
```
