# Código Beamer — Avances del seminario

El siguiente archivo contiene una presentación breve, en azul, centrada en la
conversión del prototipo en una aplicación web investigable y preparada para un
despliegue posterior en Azure.

```latex
\documentclass[aspectratio=169,10pt]{beamer}

\usetheme{Madrid}
\usecolortheme{default}
\definecolor{patiBlue}{HTML}{123B70}
\definecolor{patiLight}{HTML}{EAF2FB}
\definecolor{patiCyan}{HTML}{0E7490}
\setbeamercolor{structure}{fg=patiBlue}
\setbeamercolor{frametitle}{bg=patiBlue,fg=white}
\setbeamercolor{title}{fg=patiBlue}
\setbeamercolor{block title}{bg=patiBlue,fg=white}
\setbeamercolor{block body}{bg=patiLight,fg=black}
\setbeamertemplate{navigation symbols}{}

\usepackage[utf8]{inputenc}
\usepackage[T1]{fontenc}
\usepackage[spanish,es-nodecimaldot]{babel}
\usepackage{amsmath}
\usepackage{booktabs}
\usepackage{graphicx}
\usepackage{tikz}
\usetikzlibrary{arrows.meta,positioning,shapes.geometric,fit}

\title[PATI: tutor web]{PATI: de prototipo experimental a aplicación web investigable}
\subtitle{Avances en autenticación, consentimiento, memoria y control de acceso}
\author{M. Cruz}
\institute{Investigación doctoral sobre tutores LLM de Precálculo}
\date{Seminario de avances}

\begin{document}

\begin{frame}[plain]
  \vspace*{12mm}
  {\color{patiBlue}\Huge\bfseries PATI\par}
  \vspace{3mm}
  {\color{patiBlue}\LARGE\bfseries De prototipo experimental a aplicación web investigable\par}
  \vspace{5mm}
  {\large Avances en autenticación, consentimiento, memoria y control de acceso\par}
  \vspace{8mm}
  \begin{beamercolorbox}[sep=7pt,wd=\textwidth]{block body}
  \textbf{PATI} significa \textit{Prerequisite-aware Adaptive Tutoring Intelligence}:
  una tutora inteligente que considera prerrequisitos, adapta el apoyo al estudiante
  y conserva trazabilidad de cada interacción.
  \end{beamercolorbox}
  \vfill
  \textbf{M. Cruz}\\
  Investigación doctoral sobre tutores LLM de Precálculo\\
  Seminario de avances
\end{frame}

\begin{frame}{1. Problema de ingeniería y de investigación}
\begin{columns}[T]
\column{0.48\textwidth}
\textbf{Situación inicial}
\begin{itemize}
  \item El sistema funcionaba principalmente en notebooks y scripts experimentales.
  \item La comparación RAG, Graph-RAG y PEP-Plan-RAG necesitaba una interfaz común.
  \item No era suficiente recuperar evidencia: había que preservar contexto, usuario y trazabilidad.
\end{itemize}

\column{0.48\textwidth}
\textbf{Objetivo de esta etapa}
\begin{itemize}
  \item Construir una aplicación web que pueda probarse con estudiantes.
  \item Separar la experiencia del estudiante de la vista de investigación.
  \item Mantener registro reproducible de conversaciones, perfiles y decisiones del sistema.
\end{itemize}
\end{columns}

\vfill
\begin{block}{Resultado de la etapa}
PATI ya tiene una base web funcional con autenticación, persistencia, consentimiento versionado, tutor conversacional y panel administrativo.
\end{block}
\end{frame}

\begin{frame}{2. Arquitectura de la aplicación}
\centering
\begin{tikzpicture}[
  node distance=7mm and 9mm,
  box/.style={draw=patiBlue,fill=patiLight,rounded corners,align=center,minimum width=3.1cm,minimum height=0.9cm,font=\small},
  arrow/.style={-{Latex[length=2mm]},thick,color=patiCyan}
]
\node[box] (web) {Frontend Next.js\\Estudiante / Admin};
\node[box,right=of web] (api) {Backend FastAPI\\Auth + tutor + API};
\node[box,right=of api] (core) {Núcleo PATI\\RAG / Graph / PEP-Plan v3};
\node[box,below=of api] (db) {SQLite\\usuarios + memoria + perfiles};
\node[box,below=of core] (models) {Gemini / OpenAI / DeepSeek\\modelos locales + fallback};
\draw[arrow] (web)--(api);
\draw[arrow] (api)--(core);
\draw[arrow] (api)--(db);
\draw[arrow] (core)--(models);
\end{tikzpicture}

\vfill
\begin{itemize}
  \item \textbf{Presentación:} Next.js gestiona login, chat, historial, perfil y vista admin.
  \item \textbf{Aplicación:} FastAPI valida sesión, rol, protocolo y conecta cada solicitud con PATI.
  \item \textbf{Datos:} SQLite conserva usuarios seudónimos, conversaciones, evidencias y dominio.
  \item \textbf{Investigación:} el núcleo común permite ejecutar el mismo retrieval desde UI y scripts.
\end{itemize}
\end{frame}

\begin{frame}{3. Autenticación y roles}
\begin{columns}[T]
\column{0.52\textwidth}
\textbf{Inicio de sesión}
\begin{itemize}
  \item Cada cuenta usa un seudónimo y un PIN.
  \item El PIN no se guarda como texto. La aplicación lo transforma en una huella protegida mediante PBKDF2-HMAC-SHA256.
  \item Después de iniciar sesión, la API entrega un código temporal que identifica la sesión.
  \item Ese código se envía en cada solicitud y deja de funcionar al cerrar la sesión.
\end{itemize}

\column{0.43\textwidth}
\scriptsize
\begin{tabular}{p{1.8cm}p{4.4cm}}
\toprule
\textbf{Rol} & \textbf{Permisos}\\
\midrule
student & tutor, conversaciones, perfil y actividades\\
admin & todo lo anterior, usuarios, historiales y métricas\\
\bottomrule
\end{tabular}
\end{columns}

\vfill
\begin{block}{Control probado}
\small
Un estudiante que solicita \texttt{/api/admin/overview} recibe HTTP 403. Un administrador recibe HTTP 200. La protección existe en el backend, aunque el usuario conozca la URL de administración.
\end{block}
\end{frame}

\begin{frame}{4. Consentimiento y protocolo de datos}
\centering
\begin{tikzpicture}[
  node distance=3mm,
  step/.style={draw=patiBlue,fill=patiLight,rounded corners,align=center,minimum width=2.85cm,minimum height=0.75cm,font=\small},
  arrow/.style={-{Latex[length=2mm]},thick,color=patiCyan}
]
\node[step] (login) {Login / registro};
\node[step,right=of login] (read) {Resumen + PDF completo};
\node[step,right=of read] (check) {Casilla de aceptación};
\node[step,right=of check] (chat) {Acceso al tutor};
\draw[arrow] (login)--(read);
\draw[arrow] (read)--(check);
\draw[arrow] (check)--(chat);
\end{tikzpicture}

\vspace{3mm}
\small
\begin{itemize}
  \item El botón ``Aceptar y continuar'' permanece deshabilitado hasta marcar la casilla.
  \item La base registra usuario seudónimo, versión, aceptación y fecha/hora UTC.
  \item La versión activa se calcula con el hash del PDF:
  \[
    v = \texttt{2026-10-15-} + \operatorname{SHA256}(\text{PDF})[0:12]
  \]
  \item Si cambia el PDF, la versión cambia y el backend vuelve a bloquear el acceso.
\end{itemize}
\begin{block}{Contenido del protocolo}
\scriptsize
Describe los datos recogidos, consentimiento informado, almacenamiento institucional, control de acceso, retención, eliminación segura y mitigación de riesgos.
\end{block}
\end{frame}

\begin{frame}{5. Vistas, base de datos y permisos}
\begin{columns}[T]
\column{0.31\textwidth}
\textbf{Vista del estudiante}
\scriptsize
\begin{itemize}
  \item Login y protocolo.
  \item Chat y conversaciones.
  \item Historial y avatar.
  \item Perfil de aprendizaje.
\end{itemize}

\column{0.31\textwidth}
\textbf{Vista del administrador}
\scriptsize
\begin{itemize}
  \item Lista de usuarios seudónimos.
  \item Estado del protocolo.
  \item Conversaciones autorizadas.
  \item Evidencias y dominio por concepto.
\end{itemize}

\column{0.31\textwidth}
\textbf{Base de datos}
\scriptsize
\begin{itemize}
  \item Usuarios y roles.
  \item Aceptaciones del protocolo.
  \item Conversaciones y mensajes.
  \item Evidencias, dominio y feedback.
\end{itemize}
\end{columns}

\vfill
\begin{block}{Regla central}
\small
El estudiante solo consulta sus propios datos. El administrador puede revisar la información necesaria para la investigación. Si no existe una aceptación vigente, el backend responde HTTP 428 y no ejecuta el tutor.
\end{block}

\scriptsize
La tabla \texttt{protocol\_acceptances} registra usuario, versión, aceptación y fecha UTC. La migración está en \texttt{migrations/001\_protocol\_acceptances.sql}.
\end{frame}

\begin{frame}{6. Memoria conversacional y perfil del estudiante}
\begin{columns}[T]
\column{0.5\textwidth}
\textbf{Qué conserva PATI}
\begin{itemize}
  \item Mensajes de usuario y tutor.
  \item Problema activo y resumen de conversación.
  \item Evidencias de comprensión y micro-checks.
  \item Dominio estimado por concepto y confianza.
\end{itemize}

\column{0.45\textwidth}
\textbf{Ecuación de actualización}
\[
 m_{t+1}=m_t+\alpha(y_t-m_t)
\]
\begin{itemize}
  \item $m_t$: dominio estimado.
  \item $y_t$: evidencia observada.
  \item $\alpha$: peso de la nueva evidencia.
\end{itemize}
\end{columns}

\vfill
El perfil alimenta PEP-Plan-RAG v3 antes del retrieval: el planificador puede priorizar conceptos con mayor brecha o prerrequisitos pendientes.
\end{frame}

\begin{frame}{7. Corrección de calidad en conversaciones largas}
\textbf{Problema observado}
\begin{itemize}
  \item Ante respuestas cortas como ``4 y 6'' o ``¿eso?'', el retrieval recibía demasiado historial.
  \item El fallback podía extraer la pregunta junto con instrucciones internas del prompt.
  \item En algunos casos aparecía evidencia de otro tema, por ejemplo sistemas lineales en una conversación de factorización.
\end{itemize}

\vspace{3mm}
\textbf{Cambio implementado}
\begin{enumerate}
  \item Se conserva un \textbf{ancla}: una frase breve que identifica el ejercicio activo.\\
  \scriptsize Ejemplo: ``Ayúdame a factorizar $x^2-5x+6$''.
  \normalsize
  \item ``4 y 6'' se recupera contra esa frase, no contra todo el transcript.
  \item El generador offline separa estrictamente pregunta, contexto, evidencia y traza.
\end{enumerate}

\begin{block}{Resultado esperado}
El estudiante recibe una respuesta natural y contextualizada; las instrucciones internas permanecen fuera de la interfaz.
\end{block}
\end{frame}

\begin{frame}{8. Modelos y disponibilidad del servicio}
\begin{columns}[T]
\column{0.48\textwidth}
\textbf{Separación experimental}
\begin{itemize}
  \item El modelo generador se selecciona de forma independiente del retrieval.
  \item Se pueden comparar Gemini, OpenAI, DeepSeek y modelos locales.
  \item RAG, Graph-RAG y PEP-Plan-RAG reciben el mismo prompt pedagógico.
\end{itemize}

\column{0.47\textwidth}
\textbf{Continuidad de servicio}
\begin{itemize}
  \item Gemini es el proveedor principal configurado.
  \item Un fallback instruccional offline mantiene disponible la aplicación.
  \item La respuesta registra proveedor solicitado, proveedor efectivo y error original.
\end{itemize}
\end{columns}

\vfill
\begin{block}{Estado de despliegue}
La aplicación está separada en frontend y API, puede ejecutarse localmente con Docker o procesos independientes y queda preparada para migrar sesiones, base de datos y secretos a servicios administrados de Azure.
\end{block}
\end{frame}

\begin{frame}{9. Validación del avance}
\begin{center}
\small
\begin{tabular}{lr}
\toprule
\textbf{Validación} & \textbf{Resultado}\\
\midrule
Pruebas automatizadas backend & 73 pasaron\\
TypeScript del frontend & OK\\
Lint del frontend & OK\\
Build del frontend & OK\\
Estudiante contra endpoint admin & HTTP 403\\
Administrador contra endpoint admin & HTTP 200\\
PDF del protocolo & HTTP 200\\
\bottomrule
\end{tabular}
\end{center}

\vfill
\small
Las pruebas cubren autenticación, consentimiento, permisos, persistencia, memoria, retrieval y compilación del frontend. Verifican infraestructura y seguridad; todavía no demuestran superioridad pedagógica entre los métodos.
\end{frame}

\begin{frame}{10. Próximos pasos}
\small
\begin{enumerate}
  \item Migrar sesiones a un mecanismo persistente y seguro para múltiples instancias.
  \item Sustituir SQLite por Azure Database for PostgreSQL y mover artefactos grandes a Blob Storage.
  \item Almacenar claves en Azure Key Vault y habilitar Application Insights.
  \item Esperar la aprobación del Comité de Ética; el protocolo ya fue enviado.
  \item Ejecutar un piloto con estudiantes después de la aprobación y el consentimiento informado.
  \item Comparar RAG, Graph-RAG y PEP-Plan-RAG v3 con métricas de recuperación y orientación pedagógica.
  \item Analizar calidad de respuesta, memoria, comprensión y latencia por separado.
\end{enumerate}

\vfill
\begin{block}{Conclusión}
El avance principal es una plataforma funcional y auditable que permite investigar el tutor con usuarios reales sin perder control sobre identidad seudónima, consentimiento, memoria, permisos y configuración experimental.
\end{block}
\end{frame}

\end{document}
```
