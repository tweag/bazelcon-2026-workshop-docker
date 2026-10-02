"""Task 0: the wrapper imports, but with no `tesseract` on PATH the engine fails.

PATH is emptied so the result can't depend on whether the host has tesseract.
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
