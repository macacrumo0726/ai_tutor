# Migraciones

La migración `001_protocol_acceptances.sql` agrega el registro de aceptación
del protocolo de datos a instalaciones SQLite existentes. El repositorio la
aplica de forma idempotente al inicializarse, por lo que no se requiere un
comando manual en el entorno local.

En la fase Azure, este SQL se convertirá en una migración versionada para
PostgreSQL antes de mover la base de datos.
