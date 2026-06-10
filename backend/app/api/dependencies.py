from collections.abc import AsyncGenerator

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.ext.asyncio import AsyncSession

from app.clients.seace import SeaceClient
from app.core.config import Settings, get_settings
from app.db.session import get_db_session
from app.models.identity import CorporateIdentity
from app.repositories.identity import IdentityRepository
from app.services.identity import IdentityBlockchainService, IdentityCryptoService


bearer_scheme = HTTPBearer(auto_error=False)


def get_seace_client() -> SeaceClient:
    return SeaceClient(get_settings())


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async for session in get_db_session():
        yield session


def get_app_settings() -> Settings:
    return get_settings()


def get_identity_crypto_service(
    settings: Settings = Depends(get_app_settings),
) -> IdentityCryptoService:
    return IdentityCryptoService(settings)


def get_identity_blockchain_service(
    settings: Settings = Depends(get_app_settings),
) -> IdentityBlockchainService:
    return IdentityBlockchainService(settings)


async def get_current_identity(
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme),
    session: AsyncSession = Depends(get_session),
    crypto: IdentityCryptoService = Depends(get_identity_crypto_service),
) -> CorporateIdentity:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    repository = IdentityRepository(session)
    token = await repository.get_valid_token(crypto.hash_token(credentials.credentials))
    if token is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired bearer token",
            headers={"WWW-Authenticate": "Bearer"},
        )

    await repository.touch_token(token)
    await session.commit()
    return token.identity
