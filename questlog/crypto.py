import base64
import hashlib
import os

from cryptography.fernet import Fernet


def _key() -> bytes:
    configured = os.getenv("ENCRYPTION_KEY")
    if configured:
        return configured.encode()
    return base64.urlsafe_b64encode(hashlib.sha256(b"questlog-default-key").digest())


def encrypt_value(value: str) -> str:
    return Fernet(_key()).encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    return Fernet(_key()).decrypt(value.encode()).decode()
