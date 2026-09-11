"""Level 1 payload — prove a Rust + OpenSSL extension wheel actually works.

`cryptography` ships prebuilt manylinux wheels, so no compiler runs at build
time *if* a wheel exists for the target platform. When one doesn't, pip falls
back to building the Rust extension from source against the host's OpenSSL —
the non-hermetic "build-time trap" this level is about.
"""

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
