import os

from cryptography.fernet import Fernet

_generated_key: bytes | None = None


def _key() -> bytes:
    global _generated_key
    configured = os.getenv("ENCRYPTION_KEY")
    if configured:
        return configured.encode()
    if _generated_key is None:
        _generated_key = Fernet.generate_key()
    return _generated_key


def encrypt_value(value: str) -> str:
    return Fernet(_key()).encrypt(value.encode()).decode()


def decrypt_value(value: str) -> str:
    return Fernet(_key()).decrypt(value.encode()).decode()
