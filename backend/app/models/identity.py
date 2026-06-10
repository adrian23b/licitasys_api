from datetime import datetime
from enum import Enum

from sqlalchemy import Boolean, DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class VerificationStatus(str, Enum):
    PENDING = "pending"
    VERIFIED = "verified"
    REVOKED = "revoked"


class CorporateIdentity(TimestampMixin, Base):
    __tablename__ = "corporate_identities"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    ruc: Mapped[str] = mapped_column(String(11), nullable=False, unique=True, index=True)
    corporate_email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, unique=True, index=True)
    profile_hash: Mapped[str | None] = mapped_column(String(66), nullable=True, index=True)
    verification_status: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default=VerificationStatus.PENDING.value,
        index=True,
    )
    verification_tx_hash: Mapped[str | None] = mapped_column(String(66), nullable=True)

    nonces: Mapped[list["IdentityNonce"]] = relationship(back_populates="identity")
    tokens: Mapped[list["IdentityToken"]] = relationship(back_populates="identity")


class IdentityNonce(TimestampMixin, Base):
    __tablename__ = "identity_nonces"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_id: Mapped[int] = mapped_column(
        ForeignKey("corporate_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    wallet_address: Mapped[str] = mapped_column(String(42), nullable=False, index=True)
    nonce: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    consumed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)

    identity: Mapped[CorporateIdentity] = relationship(back_populates="nonces")


class IdentityToken(TimestampMixin, Base):
    __tablename__ = "identity_tokens"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    identity_id: Mapped[int] = mapped_column(
        ForeignKey("corporate_identities.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    token_hash: Mapped[str] = mapped_column(String(64), nullable=False, unique=True, index=True)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False, index=True)
    revoked: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False, index=True)
    last_used_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    identity: Mapped[CorporateIdentity] = relationship(back_populates="tokens")


Index("ix_identity_tokens_active", IdentityToken.token_hash, IdentityToken.expires_at, IdentityToken.revoked)
