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
     SQLite local + núcleo ai_tutor existente
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
Los PIN se protegen con PBKDF2-HMAC-SHA256 y sal aleatoria. Los tokens actuales
son sesiones opacas en memoria: son apropiados para desarrollo con una instancia,
pero antes de escalar Azure se migrarán a Azure Entra External ID o a sesiones
persistentes con expiración. La migración de SQLite a Azure Database for
PostgreSQL también corresponde a la siguiente etapa de despliegue.

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

## Decisiones pendientes para Azure

1. Azure Container Apps frente a App Service, según carga y presupuesto.
2. Azure Database for PostgreSQL y migraciones versionadas.
3. Blob Storage para artefactos grandes e índices.
4. Entra External ID, consentimiento y política de retención para el piloto.
5. Key Vault, Application Insights y trazabilidad de versiones experimentales.
6. Servicio de inferencia open-source: endpoint administrado o servidor propio
   con límites de concurrencia y costo.

No se afirma todavía que esta rama esté lista para recopilar datos reales de
estudiantes: falta validar privacidad, consentimiento, retención y despliegue.
