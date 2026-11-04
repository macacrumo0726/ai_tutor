# Migraciones

La migración `001_protocol_acceptances.sql` agrega el registro de aceptación
del protocolo de datos a instalaciones SQLite existentes. El repositorio la
aplica de forma idempotente al inicializarse, por lo que no se requiere un
comando manual en el entorno local.

En la fase Azure, este SQL se convertirá en una migración versionada para
PostgreSQL antes de mover la base de datos.

La migración `002_sessions.sql` documenta las sesiones persistentes. Solo se
almacena el hash SHA-256 del código temporal, junto con su expiración y estado
de revocación. El repositorio aplica la misma operación idempotentemente al
inicializar SQLite.
