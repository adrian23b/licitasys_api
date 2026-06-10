# API de LicitaSys

La API está implementada con FastAPI y registra routers desde `backend/app/api/health.py`, `backend/app/api/identity.py` y `backend/app/api/opportunities.py`. Salvo `GET /health` y los endpoints iniciales de registro/verificación de identidad, las rutas de oportunidades, crawler y perfil actual requieren `Authorization: Bearer <access-token>`.

## Autenticación

- Esquema: `Authorization: Bearer <token>`.
- El token se emite en `POST /identity/verify` o `POST /identity/register-custodial`.
- El backend no guarda el token en claro: almacena un hash y valida que no esté revocado, que no haya expirado y que la identidad asociada esté `verified`.
- Respuestas comunes de autenticación:
  - `401 Missing bearer token` si falta el header.
  - `401 Invalid or expired bearer token` si el token no existe, expiró, fue revocado o la identidad no está verificada.

## `GET /health`

- **Archivo:** `backend/app/api/health.py`.
- **Autenticación:** no requiere.
- **Propósito:** health check básico para balanceadores, Docker/Fly y monitoreo.

### Respuesta `200 OK`

```json
{
  "status": "ok"
}
```

## Identidad corporativa

### `POST /identity/register`

- **Archivo:** `backend/app/api/identity.py`.
- **Autenticación:** no requiere.
- **Propósito:** crea una identidad corporativa asociada a una wallet EVM no custodial. La identidad inicia normalmente como `pending` hasta completar `nonce` + `verify`.
- **Status exitoso:** `201 Created`.

#### Payload

```json
{
  "company_name": "ACME SAC",
  "ruc": "20123456789",
  "corporate_email": "compras@acme.pe",
  "wallet_address": "0x0000000000000000000000000000000000000000"
}
```

Campos:

- `wallet_address` es obligatorio, debe ser una dirección EVM de 42 caracteres con prefijo `0x`.
- `company_name`, `ruc` y `corporate_email` son opcionales en el schema actual; si faltan, el backend genera valores temporales.
- `ruc`, si se envía, debe contener solo dígitos.

#### Respuesta principal

```json
{
  "id": 1,
  "company_name": "ACME SAC",
  "ruc": "20123456789",
  "corporate_email": "compras@acme.pe",
  "wallet_address": "0x0000000000000000000000000000000000000000",
  "profile_hash": null,
  "verification_status": "pending",
  "verification_tx_hash": null,
  "created_at": "2026-06-10T00:00:00Z",
  "updated_at": "2026-06-10T00:00:00Z"
}
```

#### Errores relevantes

- `409 Conflict` si ya existe una identidad con el mismo RUC, email corporativo o wallet.
- `422 Unprocessable Entity` si el payload no cumple validaciones.

### `POST /identity/register-custodial`

- **Archivo:** `backend/app/api/identity.py`.
- **Autenticación:** no requiere.
- **Propósito:** crea una identidad con wallet custodial generada por el backend, intenta anclar el perfil en blockchain y emite token bearer.
- **Status exitoso:** `201 Created`.

#### Payload

```json
{
  "company_name": "ACME SAC",
  "ruc": "20123456789",
  "corporate_email": "compras@acme.pe"
}
```

Todos los campos son opcionales en el schema actual; si faltan, el backend usa valores temporales.

#### Respuesta principal

```json
{
  "identity": {
    "id": 1,
    "company_name": "ACME SAC",
    "ruc": "20123456789",
    "corporate_email": "compras@acme.pe",
    "wallet_address": "0x1111111111111111111111111111111111111111",
    "profile_hash": "0x...",
    "verification_status": "verified",
    "verification_tx_hash": "0x...",
    "created_at": "2026-06-10T00:00:00Z",
    "updated_at": "2026-06-10T00:00:00Z"
  },
  "wallet_address": "0x1111111111111111111111111111111111111111",
  "wallet_type": "custodial",
  "access_token": "opaque-token",
  "token_type": "bearer",
  "expires_at": "2026-07-10T00:00:00Z",
  "anchoring_status": "anchored",
  "tx_hash": "0x...",
  "explorer_url": "https://explorer.zktanenbaum.io/tx/0x..."
}
```

`anchoring_status` puede ser `anchored` si la transacción fue enviada o `skipped` si el backend no pudo anclar y marcó la identidad como verificada sin `tx_hash`.

#### Errores relevantes

- `409 Conflict` por RUC, email o wallet duplicados.
- `422 Unprocessable Entity` por validación del payload.

### `POST /identity/nonce`

- **Archivo:** `backend/app/api/identity.py`.
- **Autenticación:** no requiere.
- **Propósito:** emite un nonce temporal para que el titular de la wallet firme un mensaje de verificación.

#### Payload

```json
{
  "wallet_address": "0x0000000000000000000000000000000000000000"
}
```

#### Respuesta `200 OK`

```json
{
  "nonce": "random-url-safe-nonce",
  "message": "mensaje que debe firmar la wallet",
  "expires_at": "2026-06-10T00:10:00Z"
}
```

#### Errores relevantes

- `404 Not Found` si no existe identidad para la wallet.
- `422 Unprocessable Entity` si la wallet no tiene formato EVM válido.

### `POST /identity/verify`

- **Archivo:** `backend/app/api/identity.py`.
- **Autenticación:** no requiere bearer; requiere firma EVM válida.
- **Propósito:** valida el nonce firmado, ancla el perfil en `IdentityRegistry`, marca la identidad como `verified` y emite token bearer.

#### Payload

```json
{
  "wallet_address": "0x0000000000000000000000000000000000000000",
  "nonce": "random-url-safe-nonce",
  "signature": "0xsignature"
}
```

#### Respuesta `200 OK`

```json
{
  "identity": {
    "id": 1,
    "company_name": "ACME SAC",
    "ruc": "20123456789",
    "corporate_email": "compras@acme.pe",
    "wallet_address": "0x0000000000000000000000000000000000000000",
    "profile_hash": "0x...",
    "verification_status": "verified",
    "verification_tx_hash": "0x...",
    "created_at": "2026-06-10T00:00:00Z",
    "updated_at": "2026-06-10T00:00:00Z"
  },
  "access_token": "opaque-token",
  "token_type": "bearer",
  "expires_at": "2026-07-10T00:00:00Z",
  "anchoring_status": "anchored",
  "tx_hash": "0x...",
  "explorer_url": "https://explorer.zktanenbaum.io/tx/0x..."
}
```

#### Errores relevantes

- `404 Not Found` si no existe identidad para la wallet.
- `400 Bad Request` si el nonce no existe, expiró o ya fue consumido.
- `401 Unauthorized` si la firma no corresponde a la wallet.
- Errores `4xx/5xx` propagados por problemas de anclaje blockchain.

### `PUT /identity/me` / `PATCH /identity/me`

- **Archivo:** `backend/app/api/identity.py`.
- **Autenticación:** requiere bearer.
- **Propósito:** actualiza el perfil corporativo de la identidad autenticada.
- **Nota de implementación:** el código actual expone `PATCH /identity/me`; esta documentación lista también `PUT /identity/me` porque es la forma esperada en la especificación funcional. Si se requiere compatibilidad estricta con PUT, debe añadirse el alias correspondiente en el router.

#### Payload

```json
{
  "company_name": "ACME SAC",
  "ruc": "20123456789",
  "corporate_email": "compras@acme.pe"
}
```

Validaciones:

- `company_name`: 2 a 255 caracteres.
- `ruc`: exactamente 11 dígitos.
- `corporate_email`: email válido.

#### Respuesta `200 OK`

Devuelve `CorporateIdentityRead` con los datos actualizados.

### `GET /identity/me`

- **Archivo:** `backend/app/api/identity.py`.
- **Autenticación:** requiere bearer.
- **Propósito:** obtiene la identidad corporativa asociada al token actual.

#### Respuesta `200 OK`

```json
{
  "id": 1,
  "company_name": "ACME SAC",
  "ruc": "20123456789",
  "corporate_email": "compras@acme.pe",
  "wallet_address": "0x0000000000000000000000000000000000000000",
  "profile_hash": "0x...",
  "verification_status": "verified",
  "verification_tx_hash": "0x...",
  "created_at": "2026-06-10T00:00:00Z",
  "updated_at": "2026-06-10T00:00:00Z"
}
```

## Oportunidades y crawler

### `GET /opportunities`

- **Archivo:** `backend/app/api/opportunities.py`.
- **Autenticación:** requiere bearer.
- **Propósito:** lista oportunidades almacenadas con filtros y paginación.

#### Query parameters

| Parámetro | Tipo | Descripción |
| --- | --- | --- |
| `keyword` | `string` opcional | Filtro parcial por keyword almacenada. |
| `entity` | `string` opcional | Filtro parcial por entidad convocante. |
| `process_type` | `string` opcional | Filtro parcial por tipo de proceso. |
| `date_from` | `datetime` opcional | Fecha mínima de publicación. |
| `date_to` | `datetime` opcional | Fecha máxima de publicación. |
| `limit` | `int` opcional | Tamaño de página; mínimo 1, default 50 y máximo efectivo `api_max_page_size` (`200`). |
| `offset` | `int` opcional | Desplazamiento; mínimo 0. |

#### Respuesta `200 OK`

```json
{
  "items": [
    {
      "id": 1,
      "seace_id": 123456,
      "entity_name": "ENTIDAD",
      "process_type": "Adjudicación Simplificada",
      "nomenclature": "AS-SM-1-2026",
      "object_type": "Servicio",
      "item_description": "Servicio de software",
      "cubso_code": "43231500",
      "cubso_description": "Software",
      "process_summary": "Resumen del proceso",
      "publish_date": "2026-06-10T00:00:00Z",
      "end_date": "2026-06-20T00:00:00Z",
      "keyword": "software",
      "raw_json": {},
      "created_at": "2026-06-10T00:00:00Z",
      "updated_at": "2026-06-10T00:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

### `GET /opportunities/{opportunity_id}`

- **Archivo:** `backend/app/api/opportunities.py`.
- **Autenticación:** requiere bearer.
- **Propósito:** obtiene una oportunidad por identificador interno.

#### Path parameters

- `opportunity_id`: entero `id` de la tabla `opportunities`.

#### Respuesta `200 OK`

Devuelve un objeto `OpportunityRead` como los elementos de `GET /opportunities`.

#### Errores relevantes

- `404 Not Found` con `Opportunity not found` si no existe el registro.

### `POST /crawl`

- **Archivo:** `backend/app/api/opportunities.py`.
- **Autenticación:** requiere bearer.
- **Propósito:** ejecuta crawling de una palabra clave contra SEACE y persiste oportunidades nuevas.
- **Status exitoso:** `202 Accepted`.

#### Payload

```json
{
  "keyword": "software",
  "cod_objeto": 0,
  "cod_departamento": 0,
  "cod_tipo_proceso": 0
}
```

Campos:

- `keyword`: obligatorio, 1 a 255 caracteres.
- `cod_objeto`, `cod_departamento`, `cod_tipo_proceso`: enteros opcionales; default `0`.

#### Respuesta `202 Accepted`

```json
{
  "keyword": "software",
  "fetched": 10,
  "inserted": 8,
  "duplicates": 2,
  "failed": 0,
  "duration_seconds": 1.25
}
```

### `POST /crawl/bulk`

- **Archivo:** `backend/app/api/opportunities.py`.
- **Autenticación:** requiere bearer.
- **Propósito:** ejecuta crawling para varias keywords en una sola solicitud.
- **Status exitoso:** `202 Accepted`.

#### Payload

```json
{
  "keywords": ["software", "cloud", "firewall"],
  "cod_objeto": 0,
  "cod_departamento": 0,
  "cod_tipo_proceso": 0
}
```

Campos:

- `keywords`: lista obligatoria de 1 a 100 strings.
- `cod_objeto`, `cod_departamento`, `cod_tipo_proceso`: enteros opcionales; default `0`.

#### Respuesta `202 Accepted`

```json
{
  "results": [
    {
      "keyword": "software",
      "fetched": 10,
      "inserted": 8,
      "duplicates": 2,
      "failed": 0,
      "duration_seconds": 1.25
    }
  ],
  "fetched": 10,
  "inserted": 8,
  "duplicates": 2,
  "failed": 0,
  "duration_seconds": 1.25
}
```
