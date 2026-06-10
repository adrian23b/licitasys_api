from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.identity import CorporateIdentity, IdentityNonce, IdentityToken, VerificationStatus


class IdentityRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def create_identity(
        self,
        *,
        company_name: str,
        ruc: str,
        corporate_email: str,
        wallet_address: str,
    ) -> CorporateIdentity:
        identity = CorporateIdentity(
            company_name=company_name,
            ruc=ruc,
            corporate_email=corporate_email.lower(),
            wallet_address=wallet_address.lower(),
            verification_status=VerificationStatus.PENDING.value,
        )
        self.session.add(identity)
        await self.session.flush()
        await self.session.refresh(identity)
        return identity

    async def get_identity_by_wallet(self, wallet_address: str) -> CorporateIdentity | None:
        result = await self.session.execute(
            select(CorporateIdentity).where(CorporateIdentity.wallet_address == wallet_address.lower())
        )
        return result.scalar_one_or_none()

    async def add_nonce(
        self,
        *,
        identity: CorporateIdentity,
        nonce: str,
        expires_at: datetime,
    ) -> IdentityNonce:
        identity_nonce = IdentityNonce(
            identity_id=identity.id,
            wallet_address=identity.wallet_address,
            nonce=nonce,
            expires_at=expires_at,
            consumed=False,
        )
        self.session.add(identity_nonce)
        await self.session.flush()
        await self.session.refresh(identity_nonce)
        return identity_nonce

    async def get_active_nonce(self, *, wallet_address: str, nonce: str) -> IdentityNonce | None:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(IdentityNonce).where(
                IdentityNonce.wallet_address == wallet_address.lower(),
                IdentityNonce.nonce == nonce,
                IdentityNonce.consumed.is_(False),
                IdentityNonce.expires_at > now,
            )
        )
        return result.scalar_one_or_none()

    async def mark_nonce_consumed(self, identity_nonce: IdentityNonce) -> None:
        identity_nonce.consumed = True
        await self.session.flush()

    async def mark_verified(
        self,
        *,
        identity: CorporateIdentity,
        profile_hash: str,
        tx_hash: str | None,
    ) -> CorporateIdentity:
        identity.profile_hash = profile_hash
        identity.verification_tx_hash = tx_hash
        identity.verification_status = VerificationStatus.VERIFIED.value
        await self.session.flush()
        await self.session.refresh(identity)
        return identity

    async def update_identity(
        self,
        *,
        identity: CorporateIdentity,
        company_name: str,
        ruc: str,
        corporate_email: str,
    ) -> CorporateIdentity:
        identity.company_name = company_name
        identity.ruc = ruc
        identity.corporate_email = corporate_email.lower()
        await self.session.flush()
        await self.session.refresh(identity)
        return identity

    async def create_token(
        self,
        *,
        identity: CorporateIdentity,
        token_hash: str,
        expires_at: datetime,
    ) -> IdentityToken:
        token = IdentityToken(
            identity_id=identity.id,
            token_hash=token_hash,
            expires_at=expires_at,
            revoked=False,
        )
        self.session.add(token)
        await self.session.flush()
        await self.session.refresh(token)
        return token

    async def get_valid_token(self, token_hash: str) -> IdentityToken | None:
        now = datetime.now(timezone.utc)
        result = await self.session.execute(
            select(IdentityToken)
            .options(selectinload(IdentityToken.identity))
            .join(IdentityToken.identity)
            .where(
                IdentityToken.token_hash == token_hash,
                IdentityToken.revoked.is_(False),
                IdentityToken.expires_at > now,
                CorporateIdentity.verification_status == VerificationStatus.VERIFIED.value,
            )
        )
        return result.scalar_one_or_none()

    async def touch_token(self, token: IdentityToken) -> None:
        token.last_used_at = datetime.now(timezone.utc)
        await self.session.flush()
