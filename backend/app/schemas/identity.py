from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator


class CorporateIdentityRegisterRequest(BaseModel):
    company_name: str | None = None
    ruc: str | None = None
    corporate_email: EmailStr | None = None
    wallet_address: str = Field(min_length=42, max_length=42)

    @field_validator("ruc")
    @classmethod
    def validate_ruc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.isdigit():
            raise ValueError("RUC must contain only digits")
        return value

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, value: str) -> str:
        if not value.startswith("0x") or len(value) != 42:
            raise ValueError("wallet_address must be an EVM address")
        return value.lower()


class CorporateIdentityRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    company_name: str
    ruc: str
    corporate_email: str
    wallet_address: str
    profile_hash: str | None
    verification_status: str
    verification_tx_hash: str | None
    created_at: datetime
    updated_at: datetime


class CorporateIdentityCustodialRegisterRequest(BaseModel):
    company_name: str | None = None
    ruc: str | None = None
    corporate_email: EmailStr | None = None

    @field_validator("ruc")
    @classmethod
    def validate_ruc(cls, value: str | None) -> str | None:
        if value is None:
            return None
        if not value.isdigit():
            raise ValueError("RUC must contain only digits")
        return value


class CorporateIdentityCustodialRegisterResponse(BaseModel):
    identity: CorporateIdentityRead
    wallet_address: str
    wallet_type: str = "custodial"
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    anchoring_status: str
    tx_hash: str | None = None
    explorer_url: str | None = None


class CorporateIdentityUpdateRequest(BaseModel):
    company_name: str = Field(min_length=2, max_length=255)
    ruc: str = Field(min_length=11, max_length=11)
    corporate_email: EmailStr

    @field_validator("ruc")
    @classmethod
    def validate_ruc(cls, value: str) -> str:
        if not value.isdigit():
            raise ValueError("RUC must contain only digits")
        return value


class IdentityNonceRequest(BaseModel):
    wallet_address: str = Field(min_length=42, max_length=42)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, value: str) -> str:
        if not value.startswith("0x") or len(value) != 42:
            raise ValueError("wallet_address must be an EVM address")
        return value.lower()


class IdentityNonceResponse(BaseModel):
    nonce: str
    message: str
    expires_at: datetime


class IdentityVerifyRequest(BaseModel):
    wallet_address: str = Field(min_length=42, max_length=42)
    nonce: str = Field(min_length=16)
    signature: str = Field(min_length=2)

    @field_validator("wallet_address")
    @classmethod
    def validate_wallet_address(cls, value: str) -> str:
        if not value.startswith("0x") or len(value) != 42:
            raise ValueError("wallet_address must be an EVM address")
        return value.lower()


class IdentityVerifyResponse(BaseModel):
    identity: CorporateIdentityRead
    access_token: str
    token_type: str = "bearer"
    expires_at: datetime
    anchoring_status: str | None = None
    tx_hash: str | None = None
    explorer_url: str | None = None
