"""Playground payload: a container that reports on itself. See README.md."""

import os
import platform
import sys

CONFIG_PATH = os.environ.get("PLAYGROUND_CONFIG", "/etc/playground/greeting.txt")

# Pinned in //labs:requirements_lock.txt; add one to deps to see it appear.
OPTIONAL_DEPS = ["cryptography", "PIL", "pytesseract", "numpy", "pyopencl"]


def greeting() -> str:
    """Read the config file that ships as its own layer."""
    try:
        with open(CONFIG_PATH) as handle:
            return handle.read().strip()
    except FileNotFoundError:
        return "(no config layer — %s is missing)" % CONFIG_PATH


def available_deps() -> dict:
    """Which optional libraries the *build graph* actually put in the runfiles."""
    found = {}
    for name in OPTIONAL_DEPS:
        try:
            module = __import__(name)
        except ImportError:
            found[name] = None
        else:
            found[name] = getattr(module, "__version__", "unknown")
    return found


def report() -> str:
    lines = [
        greeting(),
        "",
        "python   %s" % sys.version.split()[0],
        "platform %s/%s" % (platform.system().lower(), platform.machine()),
        "",
        "declared dependencies:",
    ]
    for name, version in sorted(available_deps().items()):
        lines.append("  %-12s %s" % (name, version or "— not a dep of //labs/playground:app"))
    return "\n".join(lines)


def main() -> int:
    print(report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
