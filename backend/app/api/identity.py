import hashlib
import secrets
from sqlalchemy.exc import IntegrityError
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import (
    get_current_identity,
    get_identity_blockchain_service,
    get_identity_crypto_service,
    get_session,
)
from app.models.identity import CorporateIdentity
from app.repositories.identity import IdentityRepository
from app.schemas.identity import (
    CorporateIdentityCustodialRegisterRequest,
    CorporateIdentityCustodialRegisterResponse,
    CorporateIdentityRead,
    CorporateIdentityRegisterRequest,
    CorporateIdentityUpdateRequest,
    IdentityNonceRequest,
    IdentityNonceResponse,
    IdentityVerifyRequest,
    IdentityVerifyResponse,
)
from app.services.identity import IdentityBlockchainService, IdentityCryptoService

router = APIRouter(prefix="/identity", tags=["identity"])


def _build_placeholder_ruc(seed: str) -> str:
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    value = int(digest[:8], 16) % (10**11)
    return f"{value:011d}"


def _build_profile_defaults(*, company_name: str | None, ruc: str | None, corporate_email: str | None, wallet_address: str | None) -> tuple[str, str, str]:
    final_company_name = company_name or "Empresa por completar"
    final_ruc = ruc or _build_placeholder_ruc(wallet_address or corporate_email or "default")
    final_email = corporate_email or f"pending-{wallet_address or 'email'}@example.local"
    return final_company_name, final_ruc, final_email


@router.post("/register", response_model=CorporateIdentityRead, status_code=status.HTTP_201_CREATED)
async def register_identity(
    request: CorporateIdentityRegisterRequest,
    session: AsyncSession = Depends(get_session),
    crypto: IdentityCryptoService = Depends(get_identity_crypto_service),
) -> CorporateIdentityRead:
    repository = IdentityRepository(session)
    wallet_address = crypto.normalize_wallet(request.wallet_address)
    company_name, ruc, corporate_email = _build_profile_defaults(
        company_name=request.company_name,
        ruc=request.ruc,
        corporate_email=str(request.corporate_email) if request.corporate_email else None,
        wallet_address=wallet_address,
    )
    try:
        identity = await repository.create_identity(
            company_name=company_name,
            ruc=ruc,
            corporate_email=corporate_email,
            wallet_address=wallet_address,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Corporate identity already exists for this RUC, email, or wallet",
        ) from exc
    return CorporateIdentityRead.model_validate(identity)


@router.post(
    "/register-custodial",
    response_model=CorporateIdentityCustodialRegisterResponse,
    status_code=status.HTTP_201_CREATED,
)
async def register_identity_custodial(
    request: CorporateIdentityCustodialRegisterRequest,
    session: AsyncSession = Depends(get_session),
    crypto: IdentityCryptoService = Depends(get_identity_crypto_service),
    blockchain: IdentityBlockchainService = Depends(get_identity_blockchain_service),
) -> CorporateIdentityCustodialRegisterResponse:
    repository = IdentityRepository(session)
    wallet_address, _ = crypto.create_custodial_wallet()
    company_name, ruc, corporate_email = _build_profile_defaults(
        company_name=request.company_name,
        ruc=request.ruc,
        corporate_email=str(request.corporate_email) if request.corporate_email else None,
        wallet_address=wallet_address,
    )
    try:
        identity = await repository.create_identity(
            company_name=company_name,
            ruc=ruc,
            corporate_email=corporate_email,
            wallet_address=wallet_address,
        )
        await session.commit()
    except IntegrityError as exc:
        await session.rollback()
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Corporate identity already exists for this RUC, email, or wallet",
        ) from exc

    profile_hash = crypto.profile_hash(identity)
    tx_hash: str | None = None
    explorer_url: str | None = None
    anchoring_status = "skipped"

    try:
        tx_hash = await blockchain.anchor_identity(wallet_address=wallet_address, profile_hash=profile_hash)
        explorer_url = blockchain.build_explorer_url(tx_hash)
        identity = await repository.mark_verified(identity=identity, profile_hash=profile_hash, tx_hash=tx_hash)
        anchoring_status = "anchored"
    except HTTPException:
        identity = await repository.mark_verified(identity=identity, profile_hash=profile_hash, tx_hash=None)
        anchoring_status = "skipped"

    plain_token = crypto.issue_plain_token()
    expires_at = crypto.token_expires_at()
    await repository.create_token(
        identity=identity,
        token_hash=crypto.hash_token(plain_token),
        expires_at=expires_at,
    )
    await session.commit()

    return CorporateIdentityCustodialRegisterResponse(
        identity=CorporateIdentityRead.model_validate(identity),
        wallet_address=wallet_address,
        wallet_type="custodial",
        access_token=plain_token,
        expires_at=expires_at,
        anchoring_status=anchoring_status,
        tx_hash=tx_hash,
        explorer_url=explorer_url,
    )


@router.post("/nonce", response_model=IdentityNonceResponse)
async def issue_nonce(
    request: IdentityNonceRequest,
    session: AsyncSession = Depends(get_session),
    crypto: IdentityCryptoService = Depends(get_identity_crypto_service),
) -> IdentityNonceResponse:
    repository = IdentityRepository(session)
    wallet_address = crypto.normalize_wallet(request.wallet_address)
    identity = await repository.get_identity_by_wallet(wallet_address)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    nonce = secrets.token_urlsafe(24)
    expires_at = crypto.nonce_expires_at()
    message = crypto.build_nonce_message(wallet_address=wallet_address, nonce=nonce)
    await repository.add_nonce(identity=identity, nonce=nonce, expires_at=expires_at)
    await session.commit()
    return IdentityNonceResponse(nonce=nonce, message=message, expires_at=expires_at)


@router.post("/verify", response_model=IdentityVerifyResponse)
async def verify_identity(
    request: IdentityVerifyRequest,
    session: AsyncSession = Depends(get_session),
    crypto: IdentityCryptoService = Depends(get_identity_crypto_service),
    blockchain: IdentityBlockchainService = Depends(get_identity_blockchain_service),
) -> IdentityVerifyResponse:
    repository = IdentityRepository(session)
    wallet_address = crypto.normalize_wallet(request.wallet_address)
    identity = await repository.get_identity_by_wallet(wallet_address)
    if identity is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Identity not found")

    identity_nonce = await repository.get_active_nonce(wallet_address=wallet_address, nonce=request.nonce)
    if identity_nonce is None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Nonce is invalid or expired")

    message = crypto.build_nonce_message(wallet_address=wallet_address, nonce=request.nonce)
    if not crypto.verify_signature(message=message, signature=request.signature, wallet_address=wallet_address):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid wallet signature")

    profile_hash = crypto.profile_hash(identity)
    tx_hash = await blockchain.anchor_identity(wallet_address=wallet_address, profile_hash=profile_hash)
    await repository.mark_nonce_consumed(identity_nonce)
    identity = await repository.mark_verified(identity=identity, profile_hash=profile_hash, tx_hash=tx_hash)

    plain_token = crypto.issue_plain_token()
    expires_at = crypto.token_expires_at()
    await repository.create_token(
        identity=identity,
        token_hash=crypto.hash_token(plain_token),
        expires_at=expires_at,
    )
    await session.commit()
    return IdentityVerifyResponse(
        identity=CorporateIdentityRead.model_validate(identity),
        access_token=plain_token,
        expires_at=expires_at,
        anchoring_status="anchored",
        tx_hash=tx_hash,
        explorer_url=blockchain.build_explorer_url(tx_hash),
    )


@router.patch("/me", response_model=CorporateIdentityRead)
async def update_me(
    request: CorporateIdentityUpdateRequest,
    identity: CorporateIdentity = Depends(get_current_identity),
    session: AsyncSession = Depends(get_session),
) -> CorporateIdentityRead:
    repository = IdentityRepository(session)
    identity = await repository.update_identity(
        identity=identity,
        company_name=request.company_name,
        ruc=request.ruc,
        corporate_email=str(request.corporate_email),
    )
    await session.commit()
    return CorporateIdentityRead.model_validate(identity)


@router.get("/me", response_model=CorporateIdentityRead)
async def get_me(
    identity: CorporateIdentity = Depends(get_current_identity),
) -> CorporateIdentityRead:
    return CorporateIdentityRead.model_validate(identity)
