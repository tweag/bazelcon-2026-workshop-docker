"""Proves the ghost in pure Python: the wrapper imports fine, but with no
`tesseract` binary on PATH the engine call fails loudly. The image (structure
test) is where we make the binary real.

Note the empty PATH below. The point of this level is that `pip install
pytesseract` does not install an engine — so the test has to guarantee the
engine is absent rather than *assume* it. Without that, this test would quietly
pass or fail depending on whether the machine running it happens to have
`tesseract` installed: exactly the kind of host leakage the workshop is about.
"""

import os
import unittest
from unittest import mock

import pytesseract

import app


class GhostDependencyTest(unittest.TestCase):
    def test_wrapper_imports(self):
        self.assertTrue(hasattr(app, "ocr"))

    def test_engine_is_a_ghost_without_the_binary(self):
        # Empty PATH == "nothing pip installed put an engine anywhere".
        with mock.patch.dict(os.environ, {"PATH": ""}):
            with self.assertRaises(pytesseract.TesseractNotFoundError):
                pytesseract.get_tesseract_version()


if __name__ == "__main__":
    unittest.main()
