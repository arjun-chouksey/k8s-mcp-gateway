import pytest

from app.security.upstream_crypto import CredentialCipher


KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


def test_upstream_credentials_use_authenticated_encryption():
    cipher = CredentialCipher(KEY)
    plaintext = "upstream-bearer-secret"
    ciphertext = cipher.encrypt(plaintext)
    assert isinstance(ciphertext, bytes)
    assert plaintext.encode() not in ciphertext
    assert cipher.decrypt(ciphertext) == plaintext

    tampered = bytearray(ciphertext)
    tampered[len(tampered) // 2] ^= 1
    with pytest.raises(ValueError, match="cannot be decrypted"):
        cipher.decrypt(bytes(tampered))


def test_invalid_encryption_key_and_empty_credential_are_rejected():
    with pytest.raises(RuntimeError, match="valid Fernet key"):
        CredentialCipher("not-a-key")
    with pytest.raises(ValueError, match="between 1 and 4096"):
        CredentialCipher(KEY).encrypt("")
