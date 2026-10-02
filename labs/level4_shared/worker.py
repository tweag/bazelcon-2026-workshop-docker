"""The worker: checks a ticket before running the job."""

import base64

from cryptography.fernet import Fernet

KEY = base64.urlsafe_b64encode(b"bwb-workshop-shared-key-32bytes!")

if __name__ == "__main__":
    f = Fernet(KEY)
    job = f.decrypt(f.encrypt(b"render supply_chain.png")).decode()
    print("worker: ticket OK, running", job)
