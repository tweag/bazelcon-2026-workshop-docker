"""The API service — its own thin app layer atop the shared common layer."""

import sys

sys.path.insert(0, "/opt/app/common")

from shared import banner  # noqa: E402


def main() -> int:
    print(banner("api"))
    print("api: serving requests on :8080")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
