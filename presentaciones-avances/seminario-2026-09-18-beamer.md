# Presentación Beamer — Seminario doctoral

Copie el contenido del siguiente bloque en `main.tex` dentro de Overleaf. La presentación utiliza el tema **Madrid**, conserva las 11 diapositivas del seminario y emplea tamaños y distribuciones ajustados para evitar sobreposición.

```latex
\documentclass[10pt]{beamer}

\usetheme{Madrid}
\usecolortheme{default}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-nodecimaldot]{babel}
\usepackage{graphicx}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{tabularx}
\usepackage{array}
\usepackage{xcolor}
\usepackage{tikz}
\usetikzlibrary{arrows.meta, positioning, shapes.geometric, calc}

\title[Retrieval adaptativo]{De un perfil declarado a un retrieval adaptativo verificable}
\subtitle{Avances en memoria del estudiante, evaluación conversacional y validación de PEP-Plan v3}
\author{M. Cruz, F. Lozano, A. Gonzalez}
\institute{Universidad de Los Andes, Colombia}
\date{18 de septiembre de 2026}

% ------------------------------------------------------------
% Ajustes de legibilidad y espacio
% ------------------------------------------------------------
\definecolor{TutorBlue}{HTML}{2457A6}
\definecolor{TutorGreen}{HTML}{218C74}
\definecolor{TutorOrange}{HTML}{C96A14}
\definecolor{TutorPurple}{HTML}{7253B8}
\definecolor{TutorGray}{HTML}{F2F4F7}

\setbeamercolor{structure}{fg=TutorBlue}
\setbeamercolor{alerted text}{fg=TutorOrange}
\setbeamersize{text margin left=5mm,text margin right=5mm}
\setbeamertemplate{navigation symbols}{}
\setbeamertemplate{itemize item}{\small$\blacktriangleright$}
\setbeamertemplate{itemize subitem}{\scriptsize$\bullet$}
\setlength{\tabcolsep}{4pt}
\renewcommand{\arraystretch}{1.12}

\newcommand{\kicker}[1]{%
  \vspace{-1mm}\textcolor{TutorBlue}{\scriptsize\bfseries #1}\par\vspace{1mm}}
\newcommand{\formula}[1]{%
  \begin{center}
  \colorbox{TutorGray}{\parbox{0.94\linewidth}{\centering\vspace{1mm}%
  $\displaystyle #1$\vspace{1mm}}}
  \end{center}}
\newcommand{\concept}[1]{\textcolor{TutorBlue}{\textbf{#1}}}
\newcommand{\gain}[1]{\textcolor{TutorGreen}{\textbf{#1}}}

\begin{document}

% ============================================================
% 1. PORTADA
% ============================================================
\begin{frame}[plain]
\centering
{\scriptsize\bfseries\color{TutorBlue} SEMINARIO DOCTORAL · 18 DE SEPTIEMBRE DE 2026\par}
\vspace{4mm}
{\LARGE\bfseries De un perfil declarado a un retrieval adaptativo verificable\par}
\vspace{2mm}
{\normalsize Avances en memoria del estudiante, evaluación conversacional y validación de PEP-Plan v3\par}
\vspace{3mm}
{\small M. Cruz, F. Lozano, A. Gonzalez\par}
{\small Universidad de Los Andes, Colombia\par}
\vspace{4mm}
\begin{block}{Pregunta del periodo}
\centering
¿Cómo asegurar que la personalización de PEP-Plan v3 use señales válidas y produzca cambios observables en la evidencia recuperada?
\end{block}
\vspace{2mm}
{\scriptsize
Modelo disponible y trazable
$\longrightarrow$ Perfil basado en evidencia
$\longrightarrow$ Retrieval sensible al perfil
$\longrightarrow$ Validación experimental\par}
\vspace{3mm}
\begin{block}{Hilo conductor}
\scriptsize Primero corregimos cómo se recopila la evidencia del estudiante; después comprobamos si esa evidencia puede modificar el retrieval en la dirección pedagógica esperada.
\end{block}
\end{frame}

% ============================================================
% 2. PROBLEMA Y OBJETIVO
% ============================================================
\begin{frame}[t]{Perfil del estudiante basado en evidencia}
\kicker{AVANCE 1 · PROBLEMA Y OBJETIVO}
\small

\begin{columns}[T,onlytextwidth]
\column{0.32\textwidth}
\begin{alertblock}{Problema}
Los botones ``Lo entendí'' y ``Necesito ayuda'' modificaban directamente el dominio. El sistema confundía percepción subjetiva con desempeño observado.
\end{alertblock}

\column{0.32\textwidth}
\begin{block}{Objetivo}
Separar las fuentes para estudiar cuándo coinciden, cuándo se contradicen y cuánto peso merece cada una.
\end{block}

\column{0.32\textwidth}
\begin{exampleblock}{Criterio científico}
Cada señal conserva origen, score, confianza y concepto asociado. Ninguna fuente se convierte silenciosamente en verdad.
\end{exampleblock}
\end{columns}

\formula{\text{Auto-reporte}\neq\text{evaluación conversacional}\neq\text{evidencia verificable}}

\begin{block}{Decisión de diseño}
Los botones registran percepción y experiencia, pero ya no modifican por sí solos el dominio estimado.
\end{block}
\end{frame}

% ============================================================
% 3. REPRESENTACIÓN DEL PERFIL: DEFINICIONES
% ============================================================
\begin{frame}[t]{Representación del conocimiento del estudiante}
\kicker{AVANCE 1 · CAMBIO DE ARQUITECTURA · PARTE 1}
\small

\begin{columns}[T,onlytextwidth]
\column{0.49\textwidth}
\begin{block}{Mastery o dominio estimado}
Valor entre 0 y 1 para cada concepto. Cero representa una brecha fuerte y uno, dominio consistente. Es una estimación dinámica, no una nota definitiva.
\end{block}

\column{0.49\textwidth}
\begin{block}{Información complementaria}
\concept{Confianza}: qué tan respaldada está la estimación.\\
\concept{Evidence count}: cuántas observaciones existen.
\end{block}
\end{columns}

\vspace{4mm}
\begin{block}{Por qué se necesitan tres valores}
Dos estudiantes pueden tener dominio 0,70, pero distinta certeza. El primero puede haber producido una sola señal ambigua; el segundo, varias respuestas consistentes. El número de evidencias y la confianza permiten distinguir estos casos.
\end{block}

\begin{exampleblock}{Interpretación}
El perfil contiene un estado separado para cada concepto. Un estudiante puede mostrar dominio en ecuaciones lineales y, al mismo tiempo, una brecha todavía incierta en factorización.
\end{exampleblock}
\end{frame}

% ============================================================
% 4. REPRESENTACIÓN DEL PERFIL: ACTUALIZACIÓN
% ============================================================
\begin{frame}[t]{Actualización gradual del dominio estimado}
\kicker{AVANCE 1 · CAMBIO DE ARQUITECTURA · PARTE 2}
\small

\formula{m_{nuevo}=m_{anterior}+\alpha\,w\,(r-m_{anterior})}

\begin{tabularx}{\textwidth}{>{\bfseries}p{0.14\textwidth}X}
\toprule
$r$, resultado & Señal observada entre 0 y 1. Ejemplo: 0,15 ante confusión explícita o 1,0 en un micro-check correcto.\\
$w$, peso & Confiabilidad de la fuente. Una inferencia conversacional pesa menos que una respuesta verificable.\\
$\alpha$, tasa & Disminuye cuando se acumula evidencia para evitar cambios bruscos.\\
\bottomrule
\end{tabularx}

\vspace{2mm}
\begin{exampleblock}{Ejemplo: factorización}
$m_0=0{,}50$, $r=0{,}15$ y confianza del evaluador $0{,}85$. Por ser una inferencia conversacional, $w=0{,}85\times0{,}50=0{,}425$. En la primera observación, $\alpha_{efectiva}=0{,}50\times0{,}425=0{,}2125$:
\[
m_1=0{,}50+0{,}2125(0{,}15-0{,}50)=0{,}4256\approx0{,}43.
\]
La confianza acumulada pasa de 0 a aproximadamente 0,21. El sistema detecta una posible brecha, pero espera más evidencia antes de afirmarla con seguridad.
\end{exampleblock}
\end{frame}

% ============================================================
% 5. EVALUADOR CONVERSACIONAL
% ============================================================
\begin{frame}[t]{Evaluación transparente de una explicación elaborada}
\kicker{AVANCE 1 · HEURÍSTICA CONVERSACIONAL}
\scriptsize

La respuesta se normaliza en minúsculas, se homologan las tildes y se corrigen espacios. Las reglas de confusión e incertidumbre se evalúan primero.

\begin{columns}[T,onlytextwidth]
\column{0.49\textwidth}
\begin{exampleblock}{Marcadores de razonamiento}
Se buscan \emph{porque, entonces, por lo tanto, primero, después} y \emph{significa}. Cada marcador distinto suma una vez.
\[
M=\#\{\text{marcadores distintos}\}
\]
\end{exampleblock}

\column{0.49\textwidth}
\begin{block}{Solapamiento conceptual}
Se extraen palabras de más de cuatro letras del concepto recuperado. Cada término distinto usado por el estudiante suma una vez.
\[
O=\#\{\text{términos coincidentes}\}
\]
\end{block}
\end{columns}

\formula{\text{elaborada}\iff \text{longitud}\geq35\ \land\ (M\geq1\ \lor\ O\geq1)}
\vspace{-2mm}
\formula{score=\min\bigl(0{,}90,\;0{,}60+0{,}08M+0{,}05O\bigr)}

\begin{exampleblock}{Ejemplo calculado}
``Primero igualo el denominador a cero porque esos valores se excluyen del dominio.''
$M=2$, $O=1$ y $score=0{,}60+0{,}16+0{,}05=0{,}81$. Se clasifica como \texttt{understood}, con confianza de regla 0,60.
\end{exampleblock}

\textbf{Clasificación:} score $\geq0{,}75$ produce \texttt{understood}; entre 0,60 y 0,75 produce \texttt{partial}. Sin gold, una respuesta corta queda \texttt{unscored}.\\[1mm]
\textbf{Alcance:} la heurística mide estructura explicativa y uso conceptual; no garantiza corrección matemática. Se escogió por ser transparente y reproducible, pero deberá calibrarse con evaluadores humanos.
\end{frame}

% ============================================================
% 5. DISPONIBILIDAD
% ============================================================
\begin{frame}[t]{Disponibilidad y trazabilidad del tutor}
\kicker{AVANCE 2 · MODELO DE RESPALDO}
\small

\begin{columns}[T,onlytextwidth]
\column{0.32\textwidth}
\begin{alertblock}{Necesidad}
Un proveedor puede saturarse temporalmente. El estudiante no debería perder la conversación por un error de disponibilidad.
\end{alertblock}

\column{0.32\textwidth}
\begin{block}{Implementación}
Si el modelo principal falla, el tutor intenta un modelo alternativo y después un generador local.
\end{block}

\column{0.32\textwidth}
\begin{exampleblock}{Trazabilidad}
La interfaz registra cuál modelo produjo realmente cada respuesta.
\end{exampleblock}
\end{columns}

\vspace{5mm}
\begin{center}
\begin{tikzpicture}[
  node distance=1.15cm,
  box/.style={draw,rounded corners,minimum width=3.05cm,minimum height=0.9cm,
              align=center,font=\small,fill=TutorGray},
  flow/.style={-{Latex[length=2mm]},thick,TutorOrange}]
  \node[box] (principal) {Modelo principal};
  \node[box,right=of principal] (alternativo) {Modelo alternativo};
  \node[box,right=of alternativo] (local) {Respaldo local};
  \draw[flow] (principal) -- node[above,font=\scriptsize]{no disponible} (alternativo);
  \draw[flow] (alternativo) -- node[above,font=\scriptsize]{no disponible} (local);
\end{tikzpicture}
\end{center}

\begin{block}{Control experimental}
El respaldo mantiene disponible el chat. Durante los experimentos se desactiva para evitar que modelos generativos diferentes alteren la comparación.
\end{block}
\end{frame}

% ============================================================
% 6. CONDICIONES SIMULADAS
% ============================================================
\begin{frame}[t]{Tres condiciones simuladas del mismo estudiante}
\kicker{AVANCE 3 · DISEÑO DEL EXPERIMENTO}
\scriptsize

No representan tres estudiantes reales ni tres perfiles generales permanentes. Para cada una de las 105 preguntas se reconstruyen tres versiones del estado del mismo estudiante hipotético usando los conceptos de esa pregunta.

\begin{tabularx}{\textwidth}{>{\bfseries}p{0.18\textwidth}p{0.24\textwidth}X}
\toprule
Condición & Valores asignados & Pregunta experimental\\
\midrule
Unknown & Dominio 0,50; sin evidencia & ¿Qué recupera el método cuando aún no conocemos al estudiante?\\
Dominio alto & 0,90 en objetivo y prerrequisitos gold & ¿Qué recupera si domina el conocimiento necesario?\\
Brecha & 0,10 en prerrequisitos; 0,55 en objetivo & ¿Qué recupera si le falta conocimiento previo mientras aprende el objetivo?\\
\bottomrule
\end{tabularx}

\vspace{2mm}
\begin{columns}[T,onlytextwidth]
\column{0.32\textwidth}
\begin{block}{Preguntas}
105 preguntas de validación con prerrequisitos anotados. Cada pregunta se ejecuta nueve veces: 3 métodos por 3 perfiles.
\end{block}
\column{0.32\textwidth}
\begin{block}{Métodos}
RAG, Graph-RAG y PEP-Plan v3, todos con $top\_k=5$.
\end{block}
\column{0.32\textwidth}
\begin{exampleblock}{Ejemplo}
En ecuaciones cuadráticas, factorización vale 0,90 en dominio alto y 0,10 en brecha.
\end{exampleblock}
\end{columns}

\formula{105\ \text{preguntas}\times3\ \text{métodos}\times3\ \text{condiciones}=945\ \text{retrievals}}

\textbf{Pregunta científica:} ¿PEP-Plan cambia la evidencia cuando el mismo estudiante hipotético pasa de dominar a no dominar los prerrequisitos?
\end{frame}

% ============================================================
% 8. DISEÑO CONTRAFACTUAL: CONCEPTO
% ============================================================
\begin{frame}[t]{Diseño contrafactual pareado}
\kicker{AVANCE 3 · CONTROL DE VARIABLES · PARTE 1}
\small

\begin{columns}[T,onlytextwidth]
\column{0.49\textwidth}
\begin{block}{Contrafactual}
Pregunta qué habría recuperado el mismo algoritmo si el estudiante tuviera otro nivel de dominio.
\end{block}
\column{0.49\textwidth}
\begin{block}{Pareado}
Cada pregunta se compara consigo misma. Tema, redacción y dificultad permanecen iguales.
\end{block}
\end{columns}

\vspace{3mm}
\begin{tabularx}{\textwidth}{>{\bfseries}p{0.21\textwidth}XX}
\toprule
Elemento & Condición A & Condición B\\
\midrule
Pregunta y método & \multicolumn{2}{c}{Exactamente los mismos}\\
Perfil & Prerrequisitos dominados: 0,90 & Brecha de prerrequisitos: 0,10\\
Resultado & Top-5 de chunks & Top-5 de chunks\\
\bottomrule
\end{tabularx}

\vspace{3mm}
\begin{exampleblock}{Ejemplo de una pareja contrafactual}
Para una misma pregunta sobre ecuaciones cuadráticas, PEP-Plan se ejecuta primero con factorización = 0,90 y después con factorización = 0,10. Cualquier cambio en el top-5 puede atribuirse al perfil, porque la pregunta y el método permanecen iguales.
\end{exampleblock}
\end{frame}

% ============================================================
% 9. DISEÑO CONTRAFACTUAL: CÁLCULO Y CONTROLES
% ============================================================
\begin{frame}[t]{Cálculo pareado y variables controladas}
\kicker{AVANCE 3 · CONTROL DE VARIABLES · PARTE 2}
\small

Para cada pregunta $i$, se calcula la diferencia entre los resultados obtenidos bajo los dos estados simulados:

\formula{\Delta_i=y_i(\text{brecha})-y_i(\text{dominio alto})}

\begin{block}{Interpretación de $\Delta_i$}
\begin{itemize}
\item $\Delta_i>0$: la métrica mejora cuando el perfil contiene una brecha.
\item $\Delta_i=0$: el perfil no cambia esa métrica para la pregunta.
\item $\Delta_i<0$: la adaptación reduce el resultado medido.
\end{itemize}
\end{block}

\begin{itemize}
\item \textbf{Selección:} 105 preguntas del split de validación. El test retenido permaneció separado.
\item \textbf{Variables controladas:} corpus, embeddings, índices, grafo, pregunta y $top\_k=5$.
\item \textbf{Variable manipulada:} únicamente el perfil de dominio.
\end{itemize}

\begin{alertblock}{Alcance}
El diseño verifica el mecanismo con prerrequisitos gold. Todavía no evalúa la precisión de un perfil inferido automáticamente desde una conversación real.
\end{alertblock}
\end{frame}

% ============================================================
% 10. MÉTRICAS
% ============================================================
\begin{frame}[t]{Métricas específicas de adaptación}
\kicker{AVANCE 3 · NUEVAS MÉTRICAS}
\scriptsize

Hit@5 y Recall@5 miden recuperación del gold, pero no indican si el contexto cambió por la necesidad del estudiante.

\begin{columns}[T,onlytextwidth]
\column{0.49\textwidth}
\begin{block}{1. Distancia de Jaccard}
\[
J_d=1-\frac{|C_{alto}\cap C_{brecha}|}{|C_{alto}\cup C_{brecha}|}
\]
Mide cuánto cambia el top-5. Cero indica exactamente los mismos chunks.
\end{block}

\begin{exampleblock}{2. Lift de Prerequisite Recall}
\[
L_{pre}=R_{pre}(brecha)-R_{pre}(alto)
\]
Comprueba si el cambio aumenta la cobertura de prerrequisitos gold.
\end{exampleblock}

\column{0.49\textwidth}
\begin{block}{3. Lift del contexto de prerrequisitos}
\[
S_{pre}=\frac{\#\text{chunks top-5 asociados al prerrequisito}}{5}
\]
\[
L_{ctx}=S_{pre}(brecha)-S_{pre}(alto)
\]
Mide cuánto espacio del contexto final se dedica al conocimiento previo. Pasar de $1/5$ a $2/5$ produce $+0{,}20$.
\end{block}

\begin{alertblock}{4. Costo del concepto objetivo}
\[
C=R_{concepto}(alto)-R_{concepto}(brecha)
\]
$C=0$: conserva el objetivo. $C>0$: el apoyo desplaza el objetivo. $C<0$: también mejora su recuperación.
\end{alertblock}
\end{columns}

\textbf{Orden de lectura:} ¿cambió el contexto?, ¿aumentó el prerrequisito?, ¿llegó al LLM?, ¿se conservó el concepto central?
\end{frame}

% ============================================================
% 9. RESULTADOS ABSOLUTOS
% ============================================================
\begin{frame}[t]{Calidad absoluta bajo la condición de brecha}
\kicker{AVANCE 3 · RESULTADOS CONTRA EL GOLD}
\small

\begin{columns}[T,onlytextwidth]
\column{0.49\textwidth}
\begin{alertblock}{Condición de brecha}
El dominio de cada prerrequisito gold se fija en 0,10. Representa un estudiante que aún no maneja el conocimiento previo requerido.
\end{alertblock}
\column{0.49\textwidth}
\begin{block}{Dos comparaciones}
\textbf{Calidad absoluta}: método contra el gold.\\
\textbf{Adaptación}: mismo método con brecha 0,10 frente a dominio alto 0,90.
\end{block}
\end{columns}

\begin{center}
\begin{tabular}{lcc}
\toprule
\textbf{Método} & \textbf{Hit@5} & \textbf{Prerequisite Recall}\\
\midrule
RAG & 32,4\% & 50,5\%\\
Graph-RAG & \textbf{57,1\%} & \textbf{74,3\%}\\
PEP-Plan v3 & 47,6\% & 71,4\%\\
\bottomrule
\end{tabular}
\end{center}

\begin{center}
\begin{tikzpicture}[x=0.09cm,y=0.38cm]
  \node[anchor=east,font=\tiny] at (0,5) {Hit@5 · RAG};
  \fill[TutorBlue!65] (0,4.68) rectangle (32.4,5.32);
  \node[anchor=west,font=\tiny] at (33.5,5) {32,4\%};

  \node[anchor=east,font=\tiny] at (0,4) {Hit@5 · Graph};
  \fill[TutorGreen!75] (0,3.68) rectangle (57.1,4.32);
  \node[anchor=west,font=\tiny] at (58.2,4) {57,1\%};

  \node[anchor=east,font=\tiny] at (0,3) {Hit@5 · v3};
  \fill[TutorPurple!75] (0,2.68) rectangle (47.6,3.32);
  \node[anchor=west,font=\tiny] at (48.7,3) {47,6\%};

  \node[anchor=east,font=\tiny] at (0,2) {Pre. Recall · RAG};
  \fill[TutorBlue!65] (0,1.68) rectangle (50.5,2.32);
  \node[anchor=west,font=\tiny] at (51.6,2) {50,5\%};

  \node[anchor=east,font=\tiny] at (0,1) {Pre. Recall · Graph};
  \fill[TutorGreen!75] (0,0.68) rectangle (74.3,1.32);
  \node[anchor=west,font=\tiny] at (75.4,1) {74,3\%};

  \node[anchor=east,font=\tiny] at (0,0) {Pre. Recall · v3};
  \fill[TutorPurple!75] (0,-0.32) rectangle (71.4,0.32);
  \node[anchor=west,font=\tiny] at (72.5,0) {71,4\%};
\end{tikzpicture}
\end{center}

\begin{block}{Lectura}
Graph-RAG sigue recuperando mejor en términos absolutos. V3 queda 9,5 puntos por debajo en Hit@5, pero sólo 2,9 puntos por debajo en Prerequisite Recall. La ventaja específica de v3 se evalúa en la comparación pareada de la siguiente diapositiva.
\end{block}
\end{frame}

% ============================================================
% 10. RESULTADOS PAREADOS
% ============================================================
\begin{frame}[t]{Efecto del perfil sobre PEP-Plan v3}
\kicker{AVANCE 3 · RESULTADOS PAREADOS}
\scriptsize

\begin{tabularx}{\textwidth}{>{\bfseries}p{0.20\textwidth}p{0.25\textwidth}X}
\toprule
Resultado & Cambio observado & Qué indica\\
\midrule
Sensibilidad del contexto & Jaccard = 0,159; 47/105 cambiaron & El perfil sí participa en el ranking: aproximadamente 45\% tuvo al menos un chunk diferente.\\
Prerequisite Recall & 68,6\% a 71,4\%: \gain{+2,9 puntos} & Con una brecha conocida, v3 recuperó una proporción ligeramente mayor de prerrequisitos gold.\\
Contexto de prerrequisitos & 21,3\% a 22,9\%: \gain{+1,5 puntos} & Una fracción algo mayor del top-5 quedó disponible para que el LLM active conocimientos previos.\\
Concept Recall & 47,6\% a 51,4\%: \gain{+3,8 puntos} & El apoyo adicional no desplazó el objetivo; en promedio también mejoró su recuperación.\\
\bottomrule
\end{tabularx}

\vspace{2mm}
\begin{columns}[T,onlytextwidth]
\column{0.32\textwidth}
\begin{block}{47 de 105}
preguntas cambiaron el contexto.
\end{block}
\column{0.32\textwidth}
\begin{exampleblock}{3 mejoraron, 0 empeoraron}
en recuperación de prerrequisitos.
\end{exampleblock}
\column{0.32\textwidth}
\begin{block}{4 mejoraron, 0 empeoraron}
en recuperación del objetivo.
\end{block}
\end{columns}

\begin{alertblock}{Interpretación prudente}
Los datos muestran una mejora potencial de 2,9 puntos en cobertura de prerrequisitos bajo un perfil simulado ideal. El efecto es prometedor, pero aún no prueba significancia estadística ni aprendizaje real.
\end{alertblock}
\end{frame}

% ============================================================
% 11. CONCLUSIONES
% ============================================================
\begin{frame}[t]{Conclusiones y siguiente nivel de evidencia}
\kicker{SEMINARIO DOCTORAL · 18 DE SEPTIEMBRE DE 2026}
\scriptsize

\begin{columns}[T,onlytextwidth]
\column{0.49\textwidth}
\begin{exampleblock}{Conclusiones respaldadas}
\begin{itemize}
\item V3 respondió al perfil en 47 de 105 preguntas.
\item La brecha produjo +2,9 puntos de Prerequisite Recall.
\item Concept Recall aumentó +3,8 puntos, sin deterioros observados.
\item RAG y Graph-RAG permanecieron invariantes, como exigía el control.
\end{itemize}
\end{exampleblock}

\column{0.49\textwidth}
\begin{alertblock}{Límites actuales}
\begin{itemize}
\item Graph-RAG supera a v3 por 9,5 puntos en Hit@5.
\item Los perfiles usan gold y representan una condición oracle.
\item Falta calcular significancia pareada.
\item Mejor retrieval no implica automáticamente mayor aprendizaje.
\end{itemize}
\end{alertblock}
\end{columns}

\formula{\text{el mecanismo personaliza}\Longrightarrow\text{la personalización mejora la respuesta}\Longrightarrow\text{mejora el aprendizaje}}

\begin{block}{Siguiente experimento}
Inferir el perfil desde pretest, conversación y micro-checks; validar la inferencia con evaluadores humanos; generar respuestas con el mismo LLM; medir calidad pedagógica, postest y retención.
\end{block}

\textbf{Resultado central del periodo:} se pasó de una personalización teórica a una personalización observable y cuantificable, aunque todavía pequeña y evaluada bajo perfiles simulados.
\end{frame}

\end{document}
```

## Compilación

En Overleaf, seleccione **pdfLaTeX** como compilador. En un entorno local:

```bash
pdflatex main.tex
pdflatex main.tex
```

La segunda compilación actualiza las referencias internas y el contador total de diapositivas.
