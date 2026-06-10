# Configuración y despliegue

Esta guía consolida variables de entorno declaradas en `backend/app/core/config.py` y descritas en `backend/README.md`, además de ejecución local con Docker Compose y despliegue en Fly.io.

## Carga de configuración

El backend usa Pydantic Settings. Antes de instanciar `Settings`, intenta cargar variables desde estos archivos si existen:

1. `.env` en la raíz del repositorio.
2. `backend/.env`.
3. `contracts/.env`.

En producción (`ENVIRONMENT=prod` o `ENVIRONMENT=production`), el `env_file` de Pydantic queda deshabilitado para evitar depender de archivos locales. Por eso, en Fly.io y otros entornos productivos, las variables deben inyectarse como secrets o variables del entorno de ejecución.

## Variables de entorno

| Variable | Default | Descripción |
| --- | --- | --- |
| `DATABASE_URL` | `postgresql+asyncpg://seace:seace@postgres:5432/seace` | URL async de PostgreSQL usada por SQLAlchemy. |
| `SEACE_BASE_URL` | `https://prod4.seace.gob.pe:8086` | Host base de la API JSON de SEACE. |
| `CRAWLER_INTERVAL` | `3600` | Intervalo del crawler periódico en segundos. Debe ser al menos `60`. |
| `CRAWLER_KEYWORDS` | `software,cloud,firewall,ciberseguridad` | Keywords separadas por coma para crawling programado. |
| `SCHEDULER_ENABLED` | `true` | Habilita o deshabilita APScheduler al iniciar FastAPI. |
| `LOG_LEVEL` | `INFO` | Nivel de logging. |
| `SEACE_TIMEOUT_SECONDS` | `20.0` | Timeout HTTP para llamadas a SEACE. |
| `SEACE_MAX_RETRIES` | `3` | Reintentos del cliente SEACE. |
| `api_default_page_size` | `50` | Tamaño de página default interno para listados. No tiene alias de entorno explícito. |
| `api_max_page_size` | `200` | Tamaño máximo efectivo de página. No tiene alias de entorno explícito. |
| `ZKTANENBAUM_RPC_URL` | `https://rpc-zk.tanenbaum.io` | RPC JSON-RPC EVM para anclar identidades. |
| `ZKTANENBAUM_CHAIN_ID` | `57057` | Chain ID esperado de zkTanenbaum. |
| `IDENTITY_CONTRACT_ADDRESS` | sin valor | Dirección desplegada de `IdentityRegistry`. |
| `IDENTITY_ANCHOR_PRIVATE_KEY` | sin valor | Llave privada de la cuenta backend autorizada para anclar identidades. |
| `IDENTITY_EXPLORER_BASE_URL` | `https://explorer.zktanenbaum.io/tx` | Base para construir URLs de explorador con hashes de transacción. |
| `IDENTITY_TOKEN_SECRET` | `change-me-in-production` | Secreto para derivar/validar hashes de tokens bearer opacos. |
| `IDENTITY_TOKEN_TTL_SECONDS` | `2592000` | Vida útil de tokens bearer, por defecto 30 días. |
| `IDENTITY_NONCE_TTL_SECONDS` | `600` | Vida útil de nonces de firma, por defecto 10 minutos. |
| `ENVIRONMENT` | `production` | Controla modo de entorno y carga de `.env`. |

## Ejecución local con Docker Compose

El archivo `backend/docker-compose.yml` define dos servicios:

- `postgres`: PostgreSQL 16 Alpine, base `seace`, usuario `seace`, password `seace`, puerto `5432` y volumen `postgres_data`.
- `api`: construye el backend desde `backend/`, expone `8000`, depende del healthcheck de PostgreSQL y define variables básicas (`DATABASE_URL`, `SEACE_BASE_URL`, `CRAWLER_INTERVAL`, `CRAWLER_KEYWORDS`, `LOG_LEVEL`).

### Pasos

```bash
cd backend
docker compose up --build
```

La API queda disponible en:

```text
http://localhost:8000
```

Health check:

```bash
curl http://localhost:8000/health
```

Documentación interactiva de FastAPI:

```text
http://localhost:8000/docs
```

Para desarrollo iterativo con PostgreSQL en Docker y API local:

```bash
cd backend
python3.12 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
docker compose up -d postgres
alembic upgrade head
uvicorn app.main:app --reload
```

## Migraciones

Desde `backend/`:

```bash
alembic upgrade head
```

Crear una migración después de cambiar modelos:

```bash
alembic revision --autogenerate -m "describe change"
```

Rollback de una migración:

```bash
alembic downgrade -1
```

## Despliegue en Fly.io

El archivo `backend/fly.toml` define:

- App: `backend-tender-wind-6571`.
- Región primaria: `gru`.
- Servicio HTTP en puerto interno `8000`.
- HTTPS forzado.
- Auto start/stop de Machines.
- VM compartida de 1 GB y 1 CPU.

### Pasos recomendados

Ejecutar desde `backend/`:

```bash
fly postgres create
fly postgres attach --app <api-app> <postgres-app>
fly secrets list --app <api-app>
fly deploy --app <api-app>
```

`fly postgres attach` inyecta `DATABASE_URL` como secret de la aplicación. El contenedor debe operar con `ENVIRONMENT=production`, de modo que no dependa de `.env` local.

### Secrets mínimos de producción

```bash
fly secrets set \
  IDENTITY_TOKEN_SECRET='<valor-largo-aleatorio>' \
  IDENTITY_ANCHOR_PRIVATE_KEY='<private-key-sin-exponer>' \
  IDENTITY_CONTRACT_ADDRESS='0x...' \
  ZKTANENBAUM_RPC_URL='https://...' \
  ZKTANENBAUM_CHAIN_ID='57057' \
  --app <api-app>
```

Si Fly no inyectó `DATABASE_URL` mediante `postgres attach`, configurarlo también como secret.

## Notas de seguridad

### `IDENTITY_TOKEN_SECRET`

- Reemplazar siempre `change-me-in-production` antes de exponer la API.
- Usar un valor largo, aleatorio y de alta entropía.
- Rotarlo con un plan operativo: al cambiarlo, los tokens existentes dejarán de validar si el hash depende únicamente del secreto nuevo.
- No versionarlo en Git ni imprimirlo en logs.

### `IDENTITY_ANCHOR_PRIVATE_KEY`

- Tratarlo como secreto crítico: permite enviar transacciones de anclaje desde el backend.
- Usar una cuenta con permisos mínimos y fondos acotados para gas.
- Preferir secrets del proveedor (Fly secrets, vault corporativo, KMS) en lugar de `.env` en producción.
- Nunca exponerlo al frontend ni incluirlo en builds estáticos.

### `DATABASE_URL`

- Debe apuntar a una base privada con TLS si el proveedor lo soporta.
- Evitar credenciales compartidas entre ambientes.
- Restringir conectividad de red a la API y tareas administrativas.
- En producción, usar backups, monitoreo de almacenamiento y rotación de credenciales.

### Configuración de producción

- Usar `ENVIRONMENT=production` para evitar carga accidental de `.env` local.
- Revisar CORS antes de abrir el frontend público; el código permite localhost para desarrollo.
- Mantener `SCHEDULER_ENABLED` conscientemente habilitado o deshabilitado según la topología: si hay múltiples réplicas, podrían ejecutarse crawlers duplicados.
- Ajustar `SEACE_TIMEOUT_SECONDS` y `SEACE_MAX_RETRIES` para evitar saturar la API externa.
- Validar que `IDENTITY_CONTRACT_ADDRESS`, `ZKTANENBAUM_RPC_URL` y `ZKTANENBAUM_CHAIN_ID` correspondan a la misma red.
