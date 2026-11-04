# Aplicación web del tutor

## Alcance de esta iteración

Esta rama introduce una aplicación web desacoplada del prototipo Gradio. La
experiencia del estudiante no expone nombres de modelos, métodos de retrieval,
chunks ni controles experimentales. Esos datos quedan reservados para la vista
de investigación.

```text
Next.js (estudiante / investigación)
                  |
              HTTPS + SSE
                  |
FastAPI (auth, tutor, memoria, perfiles, feedback)
                  |
     SQLite persistente (una réplica) + núcleo ai_tutor existente
                  |
 Gemini → fallback instruccional reproducible
```

### Experiencia del estudiante

- Registro e inicio de sesión seudónimo.
- Historial aislado por usuario y conversaciones archivables.
- Respuesta progresiva mediante Server-Sent Events.
- Continuidad conversacional y perfil longitudinal recuperados antes de cada
  consulta.
- Avatar configurable sin fotografías ni datos biométricos.
- Auto-reporte de comprensión separado de la evaluación heurística.
- Pantalla obligatoria de protocolo antes del tutor: resumen, PDF completo,
  casilla explícita y aceptación versionada.

### Protocolo de datos y control de acceso

El original DOCX se conserva en `data/protocol/Proyecto_doctoral_manejo_etico_de_datos.docx`
y su copia PDF integrada en
`data/protocol/Proyecto_doctoral_manejo_etico_de_datos.pdf`. La versión activa
se calcula como `2026-10-15-<sha256-del-PDF>`. La tabla
`protocol_acceptances` (creada también por `migrations/001_protocol_acceptances.sql`)
registra `user_id`, versión, aceptación y `accepted_at_utc`.

El frontend redirige a `/protocol` después del login o registro. El backend
aplica la misma regla con una dependencia de autorización: `/api/me/avatar`,
`/api/me/progress`, conversaciones, feedback y chat devuelven HTTP 428 si la
aceptación de la versión activa no existe. `/api/protocol` y el PDF son públicos
para poder leerlos antes de aceptar; `/api/me/protocol` permite revisar el
estado después de aceptar. La vista `/admin` puede consultar el estado de
aceptación de cada usuario sin modificarlo.

### Experiencia de investigación

La ruta `/admin` requiere el rol `admin`. Presenta estado del servicio,
usuarios seudónimos, conversaciones y perfil de dominio. El rol se asigna antes
del registro mediante `AI_TUTOR_ADMIN_IDS`; el cliente no puede elevar sus
propios permisos.

### Persistencia y seguridad

La ejecución local conserva SQLite para no romper los experimentos existentes.
Los PIN se convierten en una huella protegida mediante PBKDF2-HMAC-SHA256. Las
sesiones tienen expiración configurable, almacenan únicamente el hash del código
de sesión y sobreviven al reinicio de una instancia. La configuración limita el
TTL a un máximo de siete días y revoca el código al cerrar sesión.

La imagen de API ejecuta `scripts/prepare_runtime_artifacts.py`: utiliza los
índices entregados por el build cuando existen y, si el checkout cloud no los
incluye, genera un corpus, índice y grafo deterministas a partir de la base
instruccional rastreada. Así el primer mensaje no falla por falta de artefactos.
El endpoint `/api/ready` verifica PDF, chunks, conceptos, grafo e índices antes
de declarar lista la instancia. El endpoint `/api/health` se mantiene liviano
para liveness probes.

La API agrega cabeceras de seguridad, CORS con orígenes explícitos, límites
básicos para login/registro y errores genéricos en SSE. En producción se ocultan
los endpoints de documentación automática. Las claves nunca viajan al navegador.

Nunca se envían claves al navegador. Las credenciales de proveedores sólo viven
en variables del proceso FastAPI y, en Azure, deberán almacenarse en Key Vault.

## Ejecución local

Terminal 1:

```bash
source .venv/bin/activate
pip install -e '.[web]'
python scripts/run_api.py
```

Terminal 2:

```bash
cd web
npm install
npm run dev
```

Abrir `http://localhost:3000`. La documentación interactiva de la API queda en
`http://localhost:8000/docs`.

## Despliegue inicial en Azure

La plantilla [`infra/azure/main.bicep`](../infra/azure/main.bicep) crea dos
Container Apps, Log Analytics y Azure Files para conservar la base local entre
reinicios. El API se despliega con `AI_TUTOR_DEFAULT_RETRIEVAL=pep_plan_rag`,
es decir, PEP-Plan-RAG v3. La guía de imágenes, secretos y comandos está en
[`infra/azure/README.md`](../infra/azure/README.md).

Esta primera plantilla fija una réplica de API porque SQLite no es una base
distribuida. Antes de aumentar réplicas o iniciar un piloto grande, debe
migrarse el repositorio a PostgreSQL.

## Decisiones pendientes para Azure

1. Azure Database for PostgreSQL y migraciones versionadas antes de escalar.
3. Blob Storage para artefactos grandes e índices.
4. Entra External ID, consentimiento y política de retención para el piloto.
5. Key Vault, Application Insights y trazabilidad de versiones experimentales.
6. Servicio de inferencia open-source: endpoint administrado o servidor propio
   con límites de concurrencia y costo.

La imagen y la plantilla dejan el sistema preparado para un despliegue de
prueba. La recopilación de datos reales requiere todavía aprobación del Comité
de Ética, revisión de privacidad, validación de retención, pruebas de carga y
un piloto controlado.
