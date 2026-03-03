# tests/test_crypto.py
import pytest
from a11yscope.crypto import encrypt_token, decrypt_token, mask_token

def test_encrypt_decrypt_roundtrip():
    """Encrypted token must decrypt to original value."""
    secret = "test-secret-key-at-least-32-chars-long"
    token = "canvas_api_token_abc123xyz"
    encrypted = encrypt_token(token, secret)
    assert isinstance(encrypted, bytes)
    assert token.encode() not in encrypted  # must not contain plaintext
    decrypted = decrypt_token(encrypted, secret)
    assert decrypted == token

def test_different_secrets_fail():
    """Decrypting with wrong secret must raise."""
    encrypted = encrypt_token("my-token", "secret-one-at-least-32-characters")
    with pytest.raises(Exception):
        decrypt_token(encrypted, "secret-two-at-least-32-characters")

def test_mask_token():
    """mask_token shows only last 4 characters."""
    assert mask_token("abcdefghijklmnop") == "************mnop"
    assert mask_token("ab") == "ab"  # short tokens returned as-is

def test_tampered_ciphertext_rejected():
    """Modified ciphertext must be rejected (Fernet HMAC)."""
    secret = "test-secret-key-at-least-32-chars-long"
    encrypted = encrypt_token("my-token", secret)
    tampered = encrypted[:-4] + b"XXXX"
    with pytest.raises(Exception):
        decrypt_token(tampered, secret)
