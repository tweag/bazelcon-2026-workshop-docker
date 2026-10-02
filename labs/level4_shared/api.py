"""The API: signs a job ticket for the worker."""

import base64

from cryptography.fernet import Fernet

KEY = base64.urlsafe_b64encode(b"bwb-workshop-shared-key-32bytes!")


def ticket(job: str) -> bytes:
    return Fernet(KEY).encrypt(job.encode())


if __name__ == "__main__":
    print("api: signed ticket", ticket("render supply_chain.png")[:24].decode(), "...")
