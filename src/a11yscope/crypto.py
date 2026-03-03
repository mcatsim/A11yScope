"""
Symmetric encryption for sensitive fields (Canvas API tokens).

Uses Fernet (AES-128-CBC + HMAC-SHA256) with HKDF key derivation
so the encryption key is separated from the application SECRET_KEY.
"""

import base64

from cryptography.fernet import Fernet, InvalidToken
from cryptography.hazmat.primitives.kdf.hkdf import HKDF
from cryptography.hazmat.primitives import hashes


_INFO = b"a11yscope-token-encryption"


def _derive_key(secret: str) -> bytes:
    """Derive a Fernet-compatible key from the application secret."""
    hkdf = HKDF(
        algorithm=hashes.SHA256(),
        length=32,
        salt=None,  # deterministic derivation
        info=_INFO,
    )
    raw = hkdf.derive(secret.encode())
    return base64.urlsafe_b64encode(raw)


def encrypt_token(plaintext: str, secret: str) -> bytes:
    """Encrypt a plaintext token. Returns Fernet ciphertext bytes."""
    f = Fernet(_derive_key(secret))
    return f.encrypt(plaintext.encode())


def decrypt_token(ciphertext: bytes, secret: str) -> str:
    """Decrypt a Fernet ciphertext. Raises on tamper or wrong key."""
    f = Fernet(_derive_key(secret))
    try:
        return f.decrypt(ciphertext).decode()
    except InvalidToken:
        raise ValueError("Cannot decrypt token — wrong key or tampered ciphertext")


def mask_token(token: str) -> str:
    """Return a masked version showing only the last 4 characters."""
    if len(token) <= 4:
        return token
    return "*" * (len(token) - 4) + token[-4:]
