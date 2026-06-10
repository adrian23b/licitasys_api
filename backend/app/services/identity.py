import hashlib
import hmac
import json
import secrets
from datetime import datetime, timedelta, timezone

from eth_account import Account
from eth_account.messages import encode_defunct
from eth_utils import is_address, to_checksum_address
from fastapi import HTTPException, status
from web3 import Web3

from app.core.config import Settings
from app.models.identity import CorporateIdentity


IDENTITY_REGISTRY_ABI = [
    {
        "inputs": [
            {"internalType": "address", "name": "wallet", "type": "address"},
            {"internalType": "bytes32", "name": "profileHash", "type": "bytes32"},
        ],
        "name": "anchorIdentity",
        "outputs": [],
        "stateMutability": "nonpayable",
        "type": "function",
    },
    {
        "inputs": [
            {"internalType": "address", "name": "wallet", "type": "address"},
            {"internalType": "bytes32", "name": "profileHash", "type": "bytes32"},
        ],
        "name": "isVerified",
        "outputs": [{"internalType": "bool", "name": "", "type": "bool"}],
        "stateMutability": "view",
        "type": "function",
    },
]


class IdentityCryptoService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def normalize_wallet(self, wallet_address: str) -> str:
        if not is_address(wallet_address):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="Invalid EVM wallet address",
            )
        return to_checksum_address(wallet_address).lower()

    def build_nonce_message(self, *, wallet_address: str, nonce: str) -> str:
        return (
            "SEACE corporate identity verification\n"
            f"Wallet: {wallet_address.lower()}\n"
            f"Nonce: {nonce}\n"
            f"Chain ID: {self.settings.zktanenbaum_chain_id}"
        )

    def verify_signature(self, *, message: str, signature: str, wallet_address: str) -> bool:
        try:
            recovered = Account.recover_message(encode_defunct(text=message), signature=signature)
        except Exception:
            return False
        return recovered.lower() == wallet_address.lower()

    def profile_hash(self, identity: CorporateIdentity) -> str:
        payload = {
            "company_name": identity.company_name.strip(),
            "corporate_email": identity.corporate_email.lower(),
            "ruc": identity.ruc,
            "wallet_address": identity.wallet_address.lower(),
        }
        encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
        return "0x" + hashlib.sha256(encoded).hexdigest()

    def create_custodial_wallet(self) -> tuple[str, str]:
        account = Account.create()
        private_key = "0x" + account.key.hex()
        return account.address.lower(), private_key

    def issue_plain_token(self) -> str:
        return secrets.token_urlsafe(32)

    def hash_token(self, plain_token: str) -> str:
        return hmac.new(
            self.settings.identity_token_secret.encode("utf-8"),
            plain_token.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def token_expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=self.settings.identity_token_ttl_seconds)

    def nonce_expires_at(self) -> datetime:
        return datetime.now(timezone.utc) + timedelta(seconds=self.settings.identity_nonce_ttl_seconds)


class IdentityBlockchainService:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def build_explorer_url(self, tx_hash: str | None) -> str | None:
        if not tx_hash:
            return None
        base = str(self.settings.identity_explorer_base_url or "").strip().rstrip("/")
        if not base:
            return None
        if base.endswith("/tx"):
            return f"{base}/{tx_hash}"
        return f"{base}/tx/{tx_hash}"

    async def anchor_identity(self, *, wallet_address: str, profile_hash: str) -> str:
        if not self.settings.identity_contract_address or not self.settings.identity_anchor_private_key:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Identity blockchain anchoring is not configured",
            )

        web3 = Web3(Web3.HTTPProvider(str(self.settings.zktanenbaum_rpc_url)))
        if not web3.is_connected():
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Could not connect to zkTanenbaum RPC",
            )

        account = Account.from_key(self.settings.identity_anchor_private_key)
        contract = web3.eth.contract(
            address=to_checksum_address(self.settings.identity_contract_address),
            abi=IDENTITY_REGISTRY_ABI,
        )
        nonce = web3.eth.get_transaction_count(account.address)
        transaction = contract.functions.anchorIdentity(
            to_checksum_address(wallet_address),
            bytes.fromhex(profile_hash.removeprefix("0x")),
        ).build_transaction(
            {
                "from": account.address,
                "nonce": nonce,
                "chainId": self.settings.zktanenbaum_chain_id,
                "gas": 150_000,
                "gasPrice": web3.eth.gas_price,
            }
        )
        signed = account.sign_transaction(transaction)
        tx_hash = web3.eth.send_raw_transaction(signed.raw_transaction)
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)
        if receipt.status != 1:
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail="Identity anchoring transaction failed",
            )
        return web3.to_hex(tx_hash)
