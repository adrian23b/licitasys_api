# Especificaciones de LicitaSys

## Propósito

LicitaSys es una plataforma para descubrir, almacenar y consultar oportunidades de contratación pública publicadas en SEACE. El sistema combina una API backend, un registro de identidad corporativa anclado en blockchain y una interfaz web estática para que empresas verificadas puedan consultar oportunidades, ejecutar crawls bajo demanda y mantener un perfil corporativo asociado a una wallet EVM.

## Módulos principales

### `backend/`

API FastAPI responsable de:

- Consultar y almacenar oportunidades SEACE desde una API JSON externa.
- Exponer endpoints de salud, identidad corporativa, consulta de oportunidades y crawler.
- Administrar autenticación con tokens bearer opacos asociados a identidades verificadas.
- Registrar identidades corporativas con wallet EVM, nonces de firma y anclaje opcional en zkTanenbaum.
- Persistir datos en PostgreSQL mediante SQLAlchemy async y migraciones Alembic.
- Ejecutar crawling periódico con APScheduler cuando `SCHEDULER_ENABLED` está habilitado.

### `contracts/`

Contiene el contrato Solidity `contracts/contracts/IdentityRegistry.sol`. Este contrato mantiene registros de identidad por wallet con:

- `profileHash`: hash del perfil corporativo calculado por el backend.
- `verified`: indicador de identidad verificada.
- `revoked`: indicador de revocación.
- `updatedAt`: timestamp del último cambio.

El owner del contrato puede anclar identidades (`anchorIdentity`) y revocarlas (`revokeIdentity`). El método `isVerified` permite validar que una wallet sigue verificada para un hash de perfil específico.

### `frontend/`

Interfaz estática compuesta por:

- `frontend/index.html`: estructura HTML de la aplicación.
- `frontend/app.js`: lógica cliente para interactuar con la API, wallet y formularios.
- `frontend/styles.css`: estilos visuales.

El frontend puede ejecutarse como sitio estático y consumir el backend por HTTP. Para flujos no custodiales, se integra con una wallet EVM compatible, por ejemplo MetaMask.

## Arquitectura de alto nivel

```text
┌────────────────────────────┐
│ Frontend estático           │
│ index.html/app.js/styles.css│
└──────────────┬─────────────┘
               │ HTTP + Bearer token
               ▼
┌────────────────────────────┐      ┌────────────────────────────┐
│ Backend FastAPI             │◄────►│ PostgreSQL                 │
│ salud, identidad, crawler,  │      │ opportunities, identities, │
│ oportunidades               │      │ nonces, tokens             │
└───────┬─────────────┬──────┘      └────────────────────────────┘
        │             │
        │ JSON API     │ JSON-RPC / transacción EVM
        ▼             ▼
┌──────────────┐   ┌────────────────────────────┐
│ SEACE JSON   │   │ zkTanenbaum RPC + contrato │
│ API externa  │   │ IdentityRegistry           │
└──────────────┘   └────────────────────────────┘
```

## Flujo de datos

### Descubrimiento y consulta de oportunidades

1. Un usuario autenticado llama `POST /crawl` o `POST /crawl/bulk` con una o varias palabras clave.
2. El backend construye la consulta hacia la API JSON de SEACE usando filtros como keyword, objeto, departamento y tipo de proceso.
3. El cliente SEACE recupera filas crudas, que el crawler normaliza en campos de dominio: entidad, tipo de proceso, nomenclatura, fechas, CUBSO, resumen y JSON original.
4. El repositorio inserta oportunidades en PostgreSQL ignorando duplicados por `seace_id`.
5. Los usuarios autenticados consultan los registros persistidos con `GET /opportunities` o `GET /opportunities/{opportunity_id}`.

### Identidad corporativa y tokens bearer

1. La empresa registra una identidad con `POST /identity/register` aportando wallet EVM y opcionalmente datos corporativos; o usa `POST /identity/register-custodial`, donde el backend genera una wallet custodial.
2. En el flujo no custodial, el backend emite un nonce con `POST /identity/nonce`.
3. El usuario firma el mensaje del nonce con su wallet EVM/MetaMask.
4. `POST /identity/verify` valida la firma, calcula el `profile_hash`, ancla la identidad en `IdentityRegistry` mediante zkTanenbaum RPC y crea un token bearer opaco.
5. En el flujo custodial, la identidad se crea, se intenta anclar y se devuelve directamente un token bearer.
6. Los endpoints protegidos resuelven `Authorization: Bearer <token>`, validan el hash del token, verifican vigencia y exigen que la identidad esté en estado `verified`.

## Dependencias externas

- **SEACE JSON API**: fuente externa de oportunidades públicas de contratación. Se configura con `SEACE_BASE_URL`.
- **PostgreSQL**: base de datos principal para oportunidades, identidades corporativas, nonces y tokens.
- **zkTanenbaum RPC**: endpoint JSON-RPC EVM usado para enviar transacciones al contrato `IdentityRegistry`. Se configura con `ZKTANENBAUM_RPC_URL`, `ZKTANENBAUM_CHAIN_ID`, `IDENTITY_CONTRACT_ADDRESS` e `IDENTITY_ANCHOR_PRIVATE_KEY`.
- **Wallet EVM/MetaMask**: usada por empresas no custodiales para demostrar control de la dirección mediante firma de nonce.
