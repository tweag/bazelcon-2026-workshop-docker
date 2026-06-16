"""The same suite, run two ways.

Written as unittest.TestCase so it runs under Bazel's `py_test` (stdlib, no
extra deps) *and* under `pytest` in the Docker baseline (pytest discovers
unittest cases) — genuinely the same suite, two harnesses.

`marker.txt` is a data input so the benchmark can force a one-line "code change"
that invalidates both the Bazel action and the Docker COPY layer.
"""

import os
import unittest

import calc


def _marker() -> str:
    here = os.path.dirname(os.path.abspath(__file__))
    with open(os.path.join(here, "marker.txt")) as fh:
        return fh.read().strip()


class CalcTest(unittest.TestCase):
    def test_add(self):
        self.assertEqual(calc.add(2, 3), 5)

    def test_mul(self):
        self.assertEqual(calc.mul(4, 5), 20)

    def test_marker_is_readable(self):
        # presence forces a rebuild when the harness rewrites marker.txt
        self.assertIsNotNone(_marker())


if __name__ == "__main__":
    unittest.main()
