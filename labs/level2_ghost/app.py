"""Level 2 payload: pytesseract is pure Python, but shells out to `tesseract`."""

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
