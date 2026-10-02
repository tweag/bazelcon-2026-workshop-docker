"""Level 1 payload: prove the prebuilt cryptography (Rust + OpenSSL) wheel works."""

from cryptography.fernet import Fernet


def roundtrip(message: bytes) -> bytes:
    """Encrypt then decrypt — exercises the compiled extension end to end."""
    key = Fernet.generate_key()
    f = Fernet(key)
    return f.decrypt(f.encrypt(message))


def main() -> int:
    secret = b"hermetic-or-bust"
    assert roundtrip(secret) == secret
    print("cryptography wheel OK:", secret.decode())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
