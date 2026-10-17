from __future__ import annotations

from cryptography.fernet import Fernet, InvalidToken


class CredentialCipher:
    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode())
        except (TypeError, ValueError) as error:
            raise RuntimeError("UPSTREAM_CREDENTIAL_KEY must be a valid Fernet key") from error

    def encrypt(self, plaintext: str) -> bytes:
        if not plaintext or len(plaintext) > 4096:
            raise ValueError("credential must be between 1 and 4096 characters")
        return self._fernet.encrypt(plaintext.encode())

    def decrypt(self, ciphertext: bytes) -> str:
        try:
            return self._fernet.decrypt(ciphertext).decode()
        except (InvalidToken, UnicodeDecodeError) as error:
            raise ValueError("stored upstream credential cannot be decrypted") from error
