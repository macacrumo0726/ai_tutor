# Arquitectura para el piloto local (10 estudiantes)

## Decisión operativa

La condición principal es `Qwen3 1.7B + PEP-Plan-RAG v3`. El modelo corre en
Ollama en el PC; el retriever, el grafo, el perfil y la persistencia permanecen
locales. Qwen3 4B queda instalado como condición de mayor calidad para pruebas
controladas, no como modelo de servicio por defecto.

## Cadena de una pregunta

```text
HTTPS/túnel → FastAPI → autenticación/protocolo vigente
  → memoria + perfil → PEP-Plan-RAG v3
  → FAISS/BM25 + grafo + plan/prerrequisitos
  → Qwen3 1.7B (Ollama)
  → guardrails de idioma, tema y matemática
  → fallback offline instruccional si falla
  → PostgreSQL: turno, modelo, latencias, evidencia y perfil
```

El fallback offline está antes que Gemini para que una caída de red o una cuota
agotada no deje al estudiante esperando. Gemini permanece disponible como
fallback remoto explícito y todos los cambios de proveedor quedan registrados.

## Datos del piloto

Cada turno conserva el seudónimo, conversación, pregunta, respuesta, proveedor
efectivo, retriever, conceptos, prerrequisitos, latencias, evaluación automática
y señales del perfil. No se guardan PIN en texto ni claves de API. La base local
recomendada es PostgreSQL (`AI_TUTOR_DATABASE_URL`); SQLite queda como respaldo
de desarrollo.

## Capacidad y límites

El PC actual tiene 16 GB de memoria y 10 núcleos. Qwen3 1.7B reduce la latencia
y la presión de memoria para el piloto. Las respuestas largas siguen siendo
serializadas por Ollama si varios estudiantes preguntan al mismo tiempo; el
frontend muestra el estado de espera y el API conserva el turno cuando termina.
Antes de abrir el enlace se debe probar una carga de diez sesiones y definir un
límite de solicitudes por usuario.

## Exposición segura

El API no debe publicarse directamente con el puerto de desarrollo. Usar un
túnel HTTPS (Cloudflare Tunnel o ngrok), restringir CORS al dominio público,
mantener el panel de administración fuera del rol estudiante y hacer copias
de seguridad de PostgreSQL. El enlace público se puede cerrar sin perder los
datos locales.
