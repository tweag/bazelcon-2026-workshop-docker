"""Level 2 payload — the "ghost" runtime dependency.

`pip install pytesseract` gives you a pure-Python wrapper. It looks self-
contained, but every real call shells out to the `tesseract` binary. pip never
installed that binary — it's a ghost. We make it real (and hermetic) by adding
a pinned apt layer to the image, not by running `apt-get` in a Dockerfile.
"""

import sys

import pytesseract
from PIL import Image


def ocr(image_path: str) -> str:
    """Run OCR — this is the call that reaches for the ghost binary."""
    return pytesseract.image_to_string(Image.open(image_path)).strip()


def tesseract_version() -> str:
    return str(pytesseract.get_tesseract_version())


def main(argv=None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if argv and argv[0] == "--ocr":
        print(ocr(argv[1]))
    else:
        print("tesseract", tesseract_version())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
