# Despliegue de PATI en Azure Container Apps

La plantilla `main.bicep` crea una primera instalación cloud reproducible con:

- Container Apps separado para la API y el frontend.
- HTTPS administrado por Azure Container Apps.
- Log Analytics para logs del entorno.
- Azure Files para conservar SQLite, sesiones y conversaciones entre reinicios.
- `pep_plan_rag` como retrieval predeterminado, equivalente a PEP-Plan-RAG v3.
- PostgreSQL opcional mediante `databaseUrl`, recomendado para producción.
- CORS restringido al dominio público del frontend.
- La clave del proveedor se entrega como secreto de Container Apps, nunca al navegador.

## Preparación de imágenes

Construir y publicar las imágenes en un registro privado, por ejemplo Azure
Container Registry. La imagen web debe construirse con la URL pública de la API:

```bash
docker build -f Dockerfile.api -t <registry>/pati-api:latest .
docker build --build-arg NEXT_PUBLIC_API_URL=https://<api-fqdn> \
  -t <registry>/pati-web:latest web
docker push <registry>/pati-api:latest
docker push <registry>/pati-web:latest
```

La URL de la API se conoce después de crear la primera revisión. Para evitar el
ciclo, se puede usar un dominio estable o desplegar primero la API, obtener su
FQDN y después reconstruir la imagen web.

## Despliegue

```bash
az deployment group create \
  --resource-group <resource-group> \
  --template-file infra/azure/main.bicep \
  --parameters \
    apiImage=<registry>/pati-api:latest \
    webImage=<registry>/pati-web:latest \
    webOrigin=https://<web-fqdn> \
    registryServer=<registry>.azurecr.io \
    registryUsername=<acr-user> \
    registryPassword=<acr-password> \
    adminIds=admin_pati \
    geminiApiKey=<secret> \
    databaseUrl='postgresql://pati_user:<password>@<server>.postgres.database.azure.com:5432/pati?sslmode=require'
```

Para un entorno real, los parámetros sensibles deben venir de Azure Key Vault o
de secretos del pipeline, no de la shell history. Se recomienda asignar una
identidad administrada al pipeline y eliminar usuario/contraseña del registro.

## Migración de SQLite a PostgreSQL

Para conservar usuarios, conversaciones, perfiles y evidencias del entorno
local, ejecuta antes de cambiar `AI_TUTOR_DATABASE_URL`:

```bash
python scripts/migrate_sqlite_to_postgres.py \
  --sqlite data/app/ai_tutor.sqlite3 \
  --postgres-url 'postgresql://pati_user:<password>@<server>:5432/pati?sslmode=require'
```

El script crea las tablas si no existen, copia las filas en orden seguro y se
puede repetir porque conserva los registros existentes en PostgreSQL.

## Limitación deliberada de esta primera versión

La plantilla conserva una réplica de API por defecto para permitir una
instalación SQLite de transición. Cuando `databaseUrl` apunte a PostgreSQL, se
puede aumentar `maxReplicas` después de una prueba de carga y de revisar las
políticas de conexiones. Azure Files permite reinicios sin perder datos, pero
no sustituye una base de datos distribuida.

Antes de recopilar datos reales también deben completarse la aprobación del
Comité de Ética, la revisión de privacidad, la política de retención y las
pruebas de carga.
