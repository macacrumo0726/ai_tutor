# Despliegue de PATI en Azure Container Apps

La plantilla `main.bicep` crea una primera instalación cloud reproducible con:

- Container Apps separado para la API y el frontend.
- HTTPS administrado por Azure Container Apps.
- Log Analytics para logs del entorno.
- Azure Files para conservar SQLite, sesiones y conversaciones entre reinicios.
- `pep_plan_rag` como retrieval predeterminado, equivalente a PEP-Plan-RAG v3.
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
    geminiApiKey=<secret>
```

Para un entorno real, los parámetros sensibles deben venir de Azure Key Vault o
de secretos del pipeline, no de la shell history. Se recomienda asignar una
identidad administrada al pipeline y eliminar usuario/contraseña del registro.

## Limitación deliberada de esta primera versión

La plantilla mantiene una sola réplica de la API porque el repositorio actual
usa SQLite y Azure Files. Antes de aumentar `maxReplicas` o iniciar un piloto
grande, hay que migrar el repositorio a Azure Database for PostgreSQL y aplicar
migraciones transaccionales. Azure Files permite reinicios sin perder datos,
pero no convierte SQLite en una base distribuida.

Antes de recopilar datos reales también deben completarse la aprobación del
Comité de Ética, la revisión de privacidad, la política de retención y las
pruebas de carga.
