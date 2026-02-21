"""Thin async wrapper around the CryptoPay API (pay.crypt.bot)."""
import hashlib
import hmac
import json
import httpx
from config import config

_BASE = "https://pay.crypt.bot/api"


async def create_invoice(
    asset: str,
    amount: float,
    description: str,
    payload: str = "",
    expires_in: int = 3600,
) -> dict:
    """
    Create a CryptoPay invoice.
    Returns the full invoice object dict.
    asset: 'USDT' | 'TON'
    """
    async with httpx.AsyncClient() as client:
        resp = await client.post(
            f"{_BASE}/createInvoice",
            headers={"Crypto-Pay-API-Token": config.crypto_bot_token},
            json={
                "asset": asset,
                "amount": str(round(amount, 2)),
                "description": description,
                "payload": payload,
                "expires_in": expires_in,
            },
        )
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"CryptoPay createInvoice error: {data}")
    return data["result"]


async def get_invoice(invoice_id: int) -> dict:
    """Fetch a single invoice by its id."""
    async with httpx.AsyncClient() as client:
        resp = await client.get(
            f"{_BASE}/getInvoices",
            headers={"Crypto-Pay-API-Token": config.crypto_bot_token},
            params={"invoice_ids": str(invoice_id)},
        )
        data = resp.json()
    if not data.get("ok"):
        raise RuntimeError(f"CryptoPay getInvoices error: {data}")
    items = data["result"].get("items", [])
    if not items:
        raise RuntimeError(f"Invoice {invoice_id} not found")
    return items[0]


def verify_webhook(body: bytes, secret_token: str, check_hash: str) -> bool:
    """
    Verify CryptoPay webhook signature.
    check_hash comes from the 'crypto-pay-api-signature' HTTP header.
    """
    secret = hashlib.sha256(secret_token.encode()).digest()
    sig = hmac.new(secret, body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, check_hash)
