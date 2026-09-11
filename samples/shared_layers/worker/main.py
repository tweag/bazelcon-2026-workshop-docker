"""The worker service — a different app layer, the same shared common layer."""

import sys

sys.path.insert(0, "/opt/app/common")

from shared import banner  # noqa: E402


def main() -> int:
    print(banner("worker"))
    print("worker: draining the job queue")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
