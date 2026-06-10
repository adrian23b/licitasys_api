# Modelo de datos

LicitaSys usa SQLAlchemy sobre PostgreSQL. Los modelos comparten `TimestampMixin`, que agrega `created_at` y `updated_at` con zona horaria y valor por defecto en base de datos. Las migraciones Alembic referenciadas son:

- `backend/alembic/versions/0001_create_opportunities.py`: crea la tabla `opportunities` y sus índices.
- `backend/alembic/versions/0002_create_identity_tables.py`: crea `corporate_identities`, `identity_nonces` e `identity_tokens`.

## Tabla `opportunities`

- **Modelo:** `backend/app/models/opportunity.py`.
- **Migración:** `backend/alembic/versions/0001_create_opportunities.py`.
- **Propósito:** almacena oportunidades obtenidas desde SEACE, junto con campos normalizados y el JSON crudo original.

### Campos clave

| Campo | Tipo lógico | Nulable | Descripción |
| --- | --- | --- | --- |
| `id` | `Integer` | No | PK autoincremental interna. |
| `seace_id` | `Integer` | No | Identificador de oportunidad en SEACE. Es único e indexado. |
| `entity_name` | `String(512)` | Sí | Entidad convocante; indexado para búsqueda/filtros. |
| `process_type` | `String(255)` | Sí | Tipo de proceso; indexado. |
| `nomenclature` | `String(255)` | Sí | Nomenclatura del proceso; indexada. |
| `object_type` | `String(100)` | Sí | Objeto de contratación; indexado. |
| `item_description` | `Text` | Sí | Descripción del ítem. |
| `cubso_code` | `String(64)` | Sí | Código CUBSO; indexado. |
| `cubso_description` | `Text` | Sí | Descripción CUBSO. |
| `process_summary` | `Text` | Sí | Resumen normalizado del proceso. |
| `publish_date` | `DateTime(timezone=True)` | Sí | Fecha de publicación; indexada. |
| `end_date` | `DateTime(timezone=True)` | Sí | Fecha de cierre o fin; indexada. |
| `keyword` | `String(255)` | No | Keyword usada para descubrir la oportunidad; indexada. |
| `raw_json` | `JSONB` | No | Payload original normalizado desde SEACE. |
| `created_at` | `DateTime(timezone=True)` | No | Timestamp de creación. |
| `updated_at` | `DateTime(timezone=True)` | No | Timestamp de última actualización. |

### Restricciones e índices

- Primary key: `id`.
- Restricción única: `seace_id` para evitar duplicados de SEACE.
- Índices simples generados por columnas con `index=True`:
  - `ix_opportunities_seace_id`
  - `ix_opportunities_entity_name`
  - `ix_opportunities_process_type`
  - `ix_opportunities_nomenclature`
  - `ix_opportunities_object_type`
  - `ix_opportunities_cubso_code`
  - `ix_opportunities_publish_date`
  - `ix_opportunities_end_date`
  - `ix_opportunities_keyword`
- Índices compuestos:
  - `ix_opportunities_keyword_end_date` sobre `(keyword, end_date)`.
  - `ix_opportunities_entity_keyword` sobre `(entity_name, keyword)`.
  - `ix_opportunities_process_type_end_date` sobre `(process_type, end_date)`.

### Relaciones

`opportunities` no tiene foreign keys ni relaciones ORM con otros modelos. Es una tabla independiente de consulta y deduplicación.

## Tabla `corporate_identities`

- **Modelo:** `backend/app/models/identity.py` (`CorporateIdentity`).
- **Migración:** `backend/alembic/versions/0002_create_identity_tables.py`.
- **Propósito:** representa la identidad corporativa asociada a una wallet EVM y su estado de verificación.

### Campos clave

| Campo | Tipo lógico | Nulable | Descripción |
| --- | --- | --- | --- |
| `id` | `Integer` | No | PK autoincremental. |
| `company_name` | `String(255)` | No | Razón social o nombre comercial. |
| `ruc` | `String(11)` | No | RUC peruano; único e indexado. |
| `corporate_email` | `String(255)` | No | Email corporativo; único e indexado. |
| `wallet_address` | `String(42)` | No | Dirección EVM normalizada; única e indexada. |
| `profile_hash` | `String(66)` | Sí | Hash del perfil anclado en blockchain; indexado. |
| `verification_status` | `String(32)` | No | Estado: `pending`, `verified` o `revoked`; indexado. |
| `verification_tx_hash` | `String(66)` | Sí | Hash de transacción de anclaje en zkTanenbaum. |
| `created_at` | `DateTime(timezone=True)` | No | Timestamp de creación. |
| `updated_at` | `DateTime(timezone=True)` | No | Timestamp de actualización. |

### Restricciones e índices

- Primary key: `id`.
- Restricciones únicas: `ruc`, `corporate_email`, `wallet_address`.
- Índices:
  - `ix_corporate_identities_ruc`
  - `ix_corporate_identities_corporate_email`
  - `ix_corporate_identities_wallet_address`
  - `ix_corporate_identities_profile_hash`
  - `ix_corporate_identities_verification_status`

### Relaciones

- `nonces`: relación uno-a-muchos con `IdentityNonce`, usando `IdentityNonce.identity_id`.
- `tokens`: relación uno-a-muchos con `IdentityToken`, usando `IdentityToken.identity_id`.

## Tabla `identity_nonces`

- **Modelo:** `backend/app/models/identity.py` (`IdentityNonce`).
- **Migración:** `backend/alembic/versions/0002_create_identity_tables.py`.
- **Propósito:** almacena nonces de corta duración para verificar control de una wallet mediante firma EVM.

### Campos clave

| Campo | Tipo lógico | Nulable | Descripción |
| --- | --- | --- | --- |
| `id` | `Integer` | No | PK autoincremental. |
| `identity_id` | `Integer` | No | FK a `corporate_identities.id` con `ON DELETE CASCADE`; indexada. |
| `wallet_address` | `String(42)` | No | Wallet asociada al nonce; indexada. |
| `nonce` | `Text` | No | Valor aleatorio emitido; único. |
| `expires_at` | `DateTime(timezone=True)` | No | Expiración del nonce; indexada. |
| `consumed` | `Boolean` | No | Indica si el nonce ya fue usado; indexado. |
| `created_at` | `DateTime(timezone=True)` | No | Timestamp de creación. |
| `updated_at` | `DateTime(timezone=True)` | No | Timestamp de actualización. |

### Restricciones e índices

- Primary key: `id`.
- Foreign key: `identity_id` → `corporate_identities.id` con borrado en cascada.
- Restricción única: `nonce`.
- Índices:
  - `ix_identity_nonces_identity_id`
  - `ix_identity_nonces_wallet_address`
  - `ix_identity_nonces_expires_at`
  - `ix_identity_nonces_consumed`

### Relaciones

- `identity`: relación muchos-a-uno con `CorporateIdentity`.

## Tabla `identity_tokens`

- **Modelo:** `backend/app/models/identity.py` (`IdentityToken`).
- **Migración:** `backend/alembic/versions/0002_create_identity_tables.py`.
- **Propósito:** almacena hashes de tokens bearer opacos para autenticar identidades verificadas.

### Campos clave

| Campo | Tipo lógico | Nulable | Descripción |
| --- | --- | --- | --- |
| `id` | `Integer` | No | PK autoincremental. |
| `identity_id` | `Integer` | No | FK a `corporate_identities.id` con `ON DELETE CASCADE`; indexada. |
| `token_hash` | `String(64)` | No | Hash HMAC/derivado del token bearer; único e indexado. |
| `expires_at` | `DateTime(timezone=True)` | No | Expiración del token; indexada. |
| `revoked` | `Boolean` | No | Bandera de revocación; indexada. |
| `last_used_at` | `DateTime(timezone=True)` | Sí | Última vez que el token fue usado correctamente. |
| `created_at` | `DateTime(timezone=True)` | No | Timestamp de creación. |
| `updated_at` | `DateTime(timezone=True)` | No | Timestamp de actualización. |

### Restricciones e índices

- Primary key: `id`.
- Foreign key: `identity_id` → `corporate_identities.id` con borrado en cascada.
- Restricción única: `token_hash`.
- Índices:
  - `ix_identity_tokens_token_hash`
  - `ix_identity_tokens_identity_id`
  - `ix_identity_tokens_expires_at`
  - `ix_identity_tokens_revoked`
  - `ix_identity_tokens_active` sobre `(token_hash, expires_at, revoked)` para validar tokens activos de forma eficiente.

### Relaciones

- `identity`: relación muchos-a-uno con `CorporateIdentity`.

## Estados de verificación

El enum lógico `VerificationStatus` define:

- `pending`: identidad creada pero no verificada/anclada.
- `verified`: identidad validada y apta para usar tokens bearer.
- `revoked`: identidad revocada o no válida para autenticación.
