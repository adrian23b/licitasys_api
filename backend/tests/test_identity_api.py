import os
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

os.environ["SCHEDULER_ENABLED"] = "false"

from eth_account import Account
from eth_account.messages import encode_defunct
from fastapi.testclient import TestClient

from app.api import identity as identity_api
from app.api.dependencies import get_identity_blockchain_service, get_session
from app.main import app
from app.services.identity import IdentityCryptoService


class FakeSession:
    async def commit(self) -> None:
        return None

    async def rollback(self) -> None:
        return None


class FakeBlockchain:
    async def anchor_identity(self, *, wallet_address: str, profile_hash: str) -> str:
        return "0x" + "a" * 64

    def build_explorer_url(self, tx_hash: str | None) -> str | None:
        if not tx_hash:
            return None
        return f"https://explorer.example/tx/{tx_hash}"


class FakeIdentityRepository:
    identity = SimpleNamespace(
        id=1,
        company_name="ACME SAC",
        ruc="20123456789",
        corporate_email="compras@acme.pe",
        wallet_address="",
        profile_hash=None,
        verification_status="pending",
        verification_tx_hash=None,
        created_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
        updated_at=datetime(2026, 6, 8, tzinfo=timezone.utc),
    )
    nonce = SimpleNamespace(nonce="nonce-value", consumed=False)

    def __init__(self, session: FakeSession) -> None:
        self.session = session

    async def create_identity(self, *, company_name: str, ruc: str, corporate_email: str, wallet_address: str):
        self.identity.company_name = company_name
        self.identity.ruc = ruc
        self.identity.corporate_email = corporate_email
        self.identity.wallet_address = wallet_address
        return self.identity

    async def get_identity_by_wallet(self, wallet_address: str):
        if self.identity.wallet_address == wallet_address:
            return self.identity
        return None

    async def add_nonce(self, *, identity, nonce: str, expires_at: datetime):
        self.nonce.nonce = nonce
        self.nonce.expires_at = expires_at
        return self.nonce

    async def get_active_nonce(self, *, wallet_address: str, nonce: str):
        if self.identity.wallet_address == wallet_address and self.nonce.nonce == nonce and not self.nonce.consumed:
            return self.nonce
        return None

    async def mark_nonce_consumed(self, identity_nonce) -> None:
        identity_nonce.consumed = True

    async def mark_verified(self, *, identity, profile_hash: str, tx_hash: str):
        identity.profile_hash = profile_hash
        identity.verification_tx_hash = tx_hash
        identity.verification_status = "verified"
        return identity

    async def create_token(self, *, identity, token_hash: str, expires_at: datetime):
        return SimpleNamespace(token_hash=token_hash, expires_at=expires_at)


async def override_session():
    yield FakeSession()


def override_blockchain() -> FakeBlockchain:
    return FakeBlockchain()


def test_identity_register_nonce_and_verify(monkeypatch) -> None:
    account = Account.create()
    wallet_address = account.address.lower()
    FakeIdentityRepository.identity.wallet_address = wallet_address
    FakeIdentityRepository.identity.verification_status = "pending"
    FakeIdentityRepository.identity.profile_hash = None
    FakeIdentityRepository.identity.verification_tx_hash = None
    FakeIdentityRepository.nonce.consumed = False

    monkeypatch.setattr(identity_api, "IdentityRepository", FakeIdentityRepository)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_identity_blockchain_service] = override_blockchain

    try:
        with TestClient(app) as client:
            register_response = client.post(
                "/identity/register",
                json={
                    "company_name": "ACME SAC",
                    "ruc": "20123456789",
                    "corporate_email": "compras@acme.pe",
                    "wallet_address": wallet_address,
                },
            )
            nonce_response = client.post("/identity/nonce", json={"wallet_address": wallet_address})
            nonce_body = nonce_response.json()
            signature = Account.sign_message(
                encode_defunct(text=nonce_body["message"]),
                account.key,
            ).signature.hex()
            verify_response = client.post(
                "/identity/verify",
                json={
                    "wallet_address": wallet_address,
                    "nonce": nonce_body["nonce"],
                    "signature": signature,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert register_response.status_code == 201
    assert nonce_response.status_code == 200
    assert verify_response.status_code == 200
    assert verify_response.json()["identity"]["verification_status"] == "verified"
    assert verify_response.json()["access_token"]


def test_custodial_register_creates_wallet_and_access_token(monkeypatch) -> None:
    FakeIdentityRepository.identity.wallet_address = ""
    FakeIdentityRepository.identity.verification_status = "pending"
    FakeIdentityRepository.identity.profile_hash = None
    FakeIdentityRepository.identity.verification_tx_hash = None

    monkeypatch.setattr(identity_api, "IdentityRepository", FakeIdentityRepository)
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/identity/register-custodial",
                json={
                    "company_name": "ACME SAC",
                    "ruc": "20123456789",
                    "corporate_email": "compras@acme.pe",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["wallet_address"].startswith("0x")
    assert body["access_token"]
    assert body["wallet_type"] == "custodial"


def test_custodial_register_returns_anchor_metadata(monkeypatch) -> None:
    FakeIdentityRepository.identity.wallet_address = ""
    FakeIdentityRepository.identity.verification_status = "pending"
    FakeIdentityRepository.identity.profile_hash = None
    FakeIdentityRepository.identity.verification_tx_hash = None

    monkeypatch.setattr(identity_api, "IdentityRepository", FakeIdentityRepository)
    app.dependency_overrides[get_session] = override_session
    app.dependency_overrides[get_identity_blockchain_service] = override_blockchain

    try:
        with TestClient(app) as client:
            response = client.post(
                "/identity/register-custodial",
                json={
                    "company_name": "ACME SAC",
                    "ruc": "20123456789",
                    "corporate_email": "compras@acme.pe",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["anchoring_status"] in {"anchored", "skipped"}
    assert body["explorer_url"] is None or body["explorer_url"].startswith("http")


def test_wallet_register_accepts_minimal_payload(monkeypatch) -> None:
    account = Account.create()
    wallet_address = account.address.lower()
    FakeIdentityRepository.identity.wallet_address = wallet_address
    FakeIdentityRepository.identity.verification_status = "pending"
    FakeIdentityRepository.identity.profile_hash = None
    FakeIdentityRepository.identity.verification_tx_hash = None

    monkeypatch.setattr(identity_api, "IdentityRepository", FakeIdentityRepository)
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/identity/register",
                json={
                    "wallet_address": wallet_address,
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["wallet_address"] == wallet_address


def test_custodial_register_accepts_email_only_payload(monkeypatch) -> None:
    FakeIdentityRepository.identity.wallet_address = ""
    FakeIdentityRepository.identity.verification_status = "pending"
    FakeIdentityRepository.identity.profile_hash = None
    FakeIdentityRepository.identity.verification_tx_hash = None

    monkeypatch.setattr(identity_api, "IdentityRepository", FakeIdentityRepository)
    app.dependency_overrides[get_session] = override_session

    try:
        with TestClient(app) as client:
            response = client.post(
                "/identity/register-custodial",
                json={
                    "corporate_email": "compras@acme.pe",
                },
            )
    finally:
        app.dependency_overrides.clear()

    assert response.status_code == 201
    body = response.json()
    assert body["wallet_address"].startswith("0x")
    assert body["access_token"]


def test_crypto_rejects_invalid_signature() -> None:
    settings = SimpleNamespace(
        identity_token_secret="test-secret",
        identity_token_ttl_seconds=60,
        identity_nonce_ttl_seconds=60,
        zktanenbaum_chain_id=57057,
    )
    crypto = IdentityCryptoService(settings)
    account = Account.create()
    other = Account.create()
    message = crypto.build_nonce_message(wallet_address=account.address, nonce="nonce")
    signature = Account.sign_message(encode_defunct(text=message), other.key).signature.hex()

    assert crypto.verify_signature(message=message, signature=signature, wallet_address=account.address) is False


def test_identity_nonce_expiration_helper() -> None:
    settings = SimpleNamespace(
        identity_token_secret="test-secret",
        identity_token_ttl_seconds=60,
        identity_nonce_ttl_seconds=60,
        zktanenbaum_chain_id=57057,
    )
    crypto = IdentityCryptoService(settings)

    assert crypto.nonce_expires_at() > datetime.now(timezone.utc) + timedelta(seconds=30)
