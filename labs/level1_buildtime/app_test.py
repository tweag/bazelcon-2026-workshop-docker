import unittest

import app


class CryptographyWheelTest(unittest.TestCase):
    def test_roundtrip(self):
        self.assertEqual(app.roundtrip(b"bazelcon"), b"bazelcon")

    def test_main_succeeds(self):
        self.assertEqual(app.main(), 0)


if __name__ == "__main__":
    unittest.main()
