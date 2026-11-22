\documentclass[10pt,aspectratio=169]{beamer}

\usetheme{Madrid}
\usecolortheme{default}
\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage{amsmath,amssymb}
\usepackage{booktabs}
\usepackage{xcolor}
\usepackage{tikz}
\usepackage{hyperref}
\usetikzlibrary{arrows.meta,positioning,fit,calc}

\definecolor{patiBlue}{RGB}{24,67,120}
\definecolor{patiLight}{RGB}{231,240,250}
\setbeamercolor{structure}{fg=patiBlue}
\setbeamercolor{frametitle}{bg=patiBlue,fg=white}
\setbeamercolor{title}{fg=patiBlue}
\setbeamercolor{block title}{bg=patiBlue,fg=white}
\setbeamercolor{block body}{bg=patiLight,fg=black}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{footline}[frame number]

\title[Arquitectura PATI]{Arquitectura híbrida para un tutor conversacional de Precálculo}
\subtitle{PEP-Plan-RAG v3, modelos de machine learning y comparación de generadores LLM}
\author{M. Cruz, F. Lozano, A. Gonzalez}
\institute{Universidad de Los Andes, Colombia}
\date{Seminario doctoral \textbar{} 2026}

\begin{document}

\begin{frame}
  \titlepage
\end{frame}

\begin{frame}{Arquitectura completa de PATI}
\centering
\begin{tikzpicture}[font=\scriptsize, node distance=4mm and 6mm,
  box/.style={draw=patiBlue, rounded corners=2pt, fill=patiLight,
              minimum height=10mm, text width=25mm, align=center},
  arrow/.style={-{Latex[length=2mm]}, thick, patiBlue}]
\node[box] (ui) {Interfaz\(tutor / admin)};
\node[box, right=of ui] (auth) {API y autorización\sesión + protocolo};
\node[box, right=of auth] (mem) {Memoria y perfil\problema activo};
\node[box, below=of mem] (ml) {Routers ML\intención + acción};
\node[box, left=of ml] (pep) {PEP-Plan-RAG v3\conceptos + prerrequisitos};
\node[box, left=of pep] (guard) {Guardrails\tema + idioma + matemática};
\node[box, right=of ml] (llm) {LLM generador\política de fallback};
\node[box, right=of llm] (db) {SQLite/PostgreSQL\turnos + métricas};
\draw[arrow] (ui)--(auth)--(mem);
\draw[arrow] (mem)--(ml);
\draw[arrow] (ml)--(pep);
\draw[arrow] (pep)--(guard);
\draw[arrow] (guard)--(llm);
\draw[arrow] (llm)--(db);
\draw[arrow] (db.south) |- (mem.south);
\end{tikzpicture}
\vfill
\footnotesize El estudiante ve una conversación; el sistema registra estados,
evidencia, proveedor, latencia, fallback y señales pedagógicas para reproducir
cada turno.
\end{frame}

\begin{frame}{Memoria y modelos ML conversacionales}
\small
\textbf{Qué se añadió:} tres clasificadores ML locales, rápidos y sin API antes
del retrieval. Se entrenaron con ejemplos semilla mediante centroides sobre un
codificador hashing; no son fine-tunings de un LLM.
\begin{columns}[T]
\column{0.48\textwidth}
\begin{itemize}
  \item \textbf{Intención:} elegir, comprobar respuesta, expresar duda, pedir ejercicio o cambiar de tema.
  \item \textbf{Tipo de respuesta:} ejemplo matemático, elección del estudiante o respuesta conceptual.
  \item \textbf{Siguiente acción:} dar pista, comprobar intento, proponer práctica o activar prerrequisito.
  \item El estado conserva problema activo, pregunta pendiente y acción esperada.
\end{itemize}
\column{0.48\textwidth}
Para cada clase $k$ se calcula un centroide de ejemplos:
\[
\mu_k=\frac{1}{n_k}\sum_{i=1}^{n_k}x_i,
\qquad
\hat y=\arg\max_k\;x\cdot\mu_k
\]
La confianza usa el margen entre las dos mejores clases. Si el margen es bajo,
el controlador determinista conserva el estado y evita inventar un cambio de tema.
\end{columns}
\vspace{2mm}
\scriptsize
\begin{tabular}{l r r r}
\toprule
Modelo ML & Ejemplos train & Test & F1 macro test\\
\midrule
Intención & 22 & 5 & 0.10\\
Tipo de respuesta & 7 & 3 & 0.167\\
Siguiente acción & 8 & 4 & 0.00\\
\bottomrule
\end{tabular}
\hspace{4mm}\footnotesize 1.500 predicciones: 25.64 ms en total. El test pequeño
no demuestra generalización; requiere conversaciones anotadas y separación por estudiante.
\end{frame}

\begin{frame}{PEP-Plan-RAG v3: recuperación pedagógica}
\small
\begin{enumerate}
  \item El router identifica si el turno continúa un problema o inicia una pregunta nueva.
  \item PEP v3 recupera chunks con dense + BM25 y expande conceptos del grafo.
  \item El planificador ordena evidencia directa y prerrequisitos según el perfil del estudiante.
  \item El LLM recibe solo contexto seleccionado y un prompt pedagógico común.
\end{enumerate}
\begin{block}{Puntuación conceptual simplificada}
\[
U(c)=w_dD(c)+w_pP(c)+w_tT(c)+w_gG(c)+w_mM(c)+w_iI(c)+w_aA(c)
\]
\scriptsize $D$: similitud directa; $P$: PageRank; $T$: objetivo de la pregunta;
$G$: brecha del estudiante; $M$: posible misconception; $I$: valor instruccional;
$A$: activación poblacional. Los pesos están en YAML y se registran por ejecución.
\end{block}
\textbf{Idea clave:} el perfil modifica la prioridad de apoyo, no la respuesta del
estudiante ni el corpus; así se puede comparar la recuperación de forma controlada.
\end{frame}

\begin{frame}{Guardrails y control del flujo conversacional}
\small
Los guardrails se ejecutan después de generar y antes de mostrar la respuesta:
\begin{columns}[T]
\column{0.48\textwidth}
\begin{itemize}
  \item idioma esperado: español;
  \item relevancia con el problema activo;
  \item separación entre evidencia e instrucciones;
  \item detección de respuesta vacía o fuga de prompt.
\end{itemize}
\column{0.48\textwidth}
\begin{itemize}
  \item verificación matemática cuando hay una respuesta explícita;
  \item doble check opcional con DeepSeek para respuestas ambiguas del GPT;
  \item no marcar ``correcto'' sin comprobarlo;
  \item si falla, reintento con otro proveedor o respuesta instruccional local;
  \item el error técnico queda en logs, no en el chat.
\end{itemize}
\end{columns}
\vspace{3mm}
El diseño separa \textit{router conceptual}, \textit{evaluación de respuesta},
\textit{resumen/estado} y generación. Esta separación adapta a Precálculo la
idea de enrutamiento y evaluación modular de Guatibonza Briceño et al.\footnote{Guatibonza Briceño et al., ``Evaluating an AI-Driven Chatbot Tutor for Enhancing Introductory Programming Learning'', ITS 2025, \url{https://doi.org/10.1007/978-3-031-98281-1_19}.}
\end{frame}

\begin{frame}{Arquitectura activa y condiciones comparadas}
\scriptsize
Todas usan PEP-Plan-RAG v3, el mismo prompt y el mismo conjunto de preguntas.
Gemini quedó fuera de la política activa por disponibilidad y cuota.
\vspace{2mm}
\begin{tabular}{l l l l}
\toprule
Condición & Principal & Fallback & Propósito\\
\midrule
GPT & GPT-4.1 mini & -- & referencia remota estable\\
DeepSeek & DeepSeek API & -- & proveedor remoto de menor latencia observada\\
Qwen local & Qwen3 1.7B (Ollama) & DeepSeek, GPT & costo API cero como primera opción\\
Phi local & Phi-4-mini (Ollama) & DeepSeek, GPT & alternativa local más grande\\
\bottomrule
\end{tabular}
\vspace{3mm}
\begin{block}{Política recomendada para el piloto}
\textbf{Configuración activa orientada a calidad:} GPT-4.1 mini como principal,
DeepSeek como segundo verificador y respaldo remoto, y generador instruccional
local como último recurso. Para un piloto sin costo de API, Qwen local permanece
disponible como condición experimental, pero con un límite de tiempo estricto.
\end{block}
\end{frame}

\begin{frame}{Experimento de validación y métricas}
\small
\textbf{Diseño ejecutado:} 3 preguntas de validación $\times$ 4 arquitecturas,
misma recuperación PEP v3, $top\text{-}k=5$, 12 solicitudes, registro JSONL y
resumen reproducible.
\begin{columns}[T]
\column{0.48\textwidth}
\textbf{Métricas de generación}
\begin{itemize}
  \item latencia total y de generación;
  \item tasa de éxito y fallbacks;
  \item Token F1 frente a la respuesta esperada.
\end{itemize}
\column{0.48\textwidth}
\textbf{Métricas de retrieval}
\begin{itemize}
  \item Hit@5;
  \item recall de conceptos;
  \item recall de prerrequisitos.
\end{itemize}
\end{columns}
\vspace{3mm}
La recuperación obtuvo 1.00 en las tres métricas en esta muestra. Eso confirma
que la comparación cambia principalmente el generador, pero no prueba todavía
calidad pedagógica ni generalización.
\end{frame}

\begin{frame}{Resultados observados: calidad y latencia}
\scriptsize
\begin{tabular}{l r r r r r}
\toprule
Arquitectura & Éxito & Fallbacks & Latencia (s) & Gen. (s) & Token F1\\
\midrule
GPT-4.1 mini & 3/3 & 0 & 5.25 & 4.87 & 0.241\\
DeepSeek API & 3/3 & 0 & 4.50 & 4.15 & 0.224\\
Qwen3 1.7B local & 3/3 & 0 & 20.47 & 20.00 & 0.225\\
Phi-4-mini local & 3/3 & 1 & 13.34 & 12.89 & 0.216\\
\bottomrule
\end{tabular}
\vspace{3mm}

\begin{center}
\begin{tikzpicture}[x=0.45cm,y=0.35cm,font=\tiny]
\draw[->] (0,0)--(22,0) node[right]{segundos};
\foreach \x/\lab in {0/0,5/5,10/10,15/15,20/20} {\draw (\x,0.1)--(\x,-0.1) node[below]{\lab};}
\fill[patiBlue] (0,1) rectangle (5.25,1.8) node[midway,above=1mm]{GPT};
\fill[patiBlue] (0,2.5) rectangle (4.50,3.3) node[midway,above=1mm]{DeepSeek};
\fill[patiBlue] (0,4) rectangle (20.47,4.8) node[midway,above=1mm]{Qwen};
\fill[patiBlue] (0,5.5) rectangle (13.34,6.3) node[midway,above=1mm]{Phi};
\end{tikzpicture}
\end{center}
\footnotesize Ranking conversacional provisional: DeepSeek por latencia y fluidez
observada; GPT por estabilidad e instrucciones; Qwen por costo cero, con latencia
alta; Phi como alternativa local con un fallback. Token F1 no sustituye una rúbrica
humana ciega.
\end{frame}

\begin{frame}{Costos y decisión para el piloto}
\small
Para GPT-4.1 mini se usaron los precios documentados en el experimento:
USD 0.40/M tokens de entrada y USD 1.60/M de salida. Con 1.800 tokens de entrada
y 350 de salida:
\[
C=\frac{1800(0.40)+350(1.60)}{1\,000\,000}=\text{USD }0.00128\text{ por turno}
\]
\begin{tabular}{l r}
\toprule
Escenario & Costo GPT estimado\\
\midrule
100 turnos & USD 0.13\\
1.000 turnos & USD 1.28\\
10 estudiantes $\times$ 500 turnos & USD 6.40\\
10 estudiantes $\times$ 1.000 turnos & USD 12.80\\
\bottomrule
\end{tabular}
\vspace{2mm}

Qwen y Phi no tienen costo de API, pero consumen recursos locales. El criterio de
selección combina corrección, coherencia, latencia p95, fallbacks y costo. La
próxima ejecución debe repetir el banco con al menos 100 conversaciones y una
rúbrica humana de 1--5 para naturalidad, andamiaje y continuidad.
\end{frame}

\begin{frame}{Conclusiones y siguientes experimentos}
\small
\begin{itemize}
  \item PEP v3 mantiene la recuperación controlada y ofrece evidencia de conceptos y prerrequisitos.
  \item Los routers ML reducen la dependencia de coincidencias exactas para respuestas breves, pero necesitan datos anotados.
  \item En el smoke test, DeepSeek fue el más rápido y GPT mostró el mayor Token F1; la conclusión todavía es provisional.
  \item Qwen ofrece costo de API cero, pero su latencia local impide usarlo sin timeout y fallback.
\end{itemize}
\textbf{Siguiente experimento:} banco pareado de 100--120 conversaciones, tres repeticiones por proveedor,
evaluación humana ciega y análisis por tipo de turno. Reportar p50/p95, errores de
tema, retención del problema activo, corrección matemática y calidad pedagógica.
La suite automatizada actual reúne 131 pruebas pasando.
\vspace{2mm}

\textbf{Estrategia de publicación:} ITS/ICALT documentan plataforma y método de
evaluación; el artículo Scopus reservará la contribución completa de PEP v3,
la comparación controlada y la prueba con estudiantes.
\end{frame}

\begin{frame}{Propuesta de artículo para ITS 2027}
\small
\textbf{Título:} \textit{Prerequisite-Aware Conversational Tutoring for Precalculus: A Controlled Comparison of PEP-Plan-RAG and LLM Fallback Policies}
\vspace{3mm}

\textbf{Resumen propuesto:} Presentamos PATI como una plataforma reproducible
para estudiar tutores de Precálculo. Describimos su separación entre memoria,
routers ML, PEP-Plan-RAG v3 y generadores con fallback, y reportamos un benchmark
preliminar de latencia, disponibilidad y recuperación con el mismo corpus y prompt.
El trabajo de ITS se plantea como artículo de sistema y metodología inicial: no
presenta todavía los resultados decisivos del algoritmo ni la evaluación con
estudiantes, que se reservarán para el artículo doctoral de mayor alcance.
\vspace{3mm}

\footnotesize Convocatoria y fechas: consultar el sitio oficial de ITS 2027,
\url{https://its2027.iis-international.org/index.html}.
\end{frame}

\begin{frame}{Propuesta de artículo para IEEE ICALT 2027}
\small
\textbf{Título:} \textit{Adaptive Learning Routes for AI-Supported STEM Education: Student-State Routing and PEP-Plan-RAG in a Precalculus Tutor}
\vspace{3mm}

\textbf{Resumen propuesto:} Describimos una arquitectura desplegable para
aprendizaje adaptativo en STEM. PATI conserva un perfil de dominio por concepto,
actualiza el estado con respuestas y conversaciones, y registra evidencia,
latencias y fallbacks. El artículo se enfocaría en la infraestructura, la
trazabilidad y el diseño de evaluación, sin revelar la comparación completa de
PEP-Plan-RAG v3 ni los resultados de la intervención con estudiantes. Esos
resultados se reservarán para el artículo Scopus que consolidará la contribución
doctoral.
\vspace{3mm}

\footnotesize Encaja especialmente con las áreas APTeL, BDELA, TeSTEM y AISLE de
ICALT 2027. La convocatoria indica artículos completos de 5 páginas, cortos de 3
páginas y resumen de hasta 200 palabras; verificar la versión vigente en
\url{https://tc.computer.org/tclt/icalt-2027/}.
\end{frame}

\end{document}
