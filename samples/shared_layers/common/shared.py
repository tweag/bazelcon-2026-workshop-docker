"""Shared library — packaged once and reused by every service image.

Lives in the common layer at /opt/app/common; both the `api` and `worker`
images depend on it, so the layer blob is byte-identical and deduped.
"""

SETTINGS_PATH = "/opt/app/common/settings.yaml"


def banner(name: str) -> str:
    return f"[bwb] {name} starting — shared lib v1, config at {SETTINGS_PATH}"
