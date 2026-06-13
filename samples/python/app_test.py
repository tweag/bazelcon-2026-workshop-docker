"""Unit tests for the Graphviz sample app (TASK §2.7).

Verifies the thing being containerized independently of any image, using only
pure-Python behavior (no `dot` binary required).
"""

import unittest

import app


class BuildGraphTest(unittest.TestCase):
    def test_emits_dot_source(self):
        src = app.build_graph().source
        self.assertIn("digraph", src)
        self.assertIn("supply_chain", src)

    def test_contains_supply_chain_nodes(self):
        src = app.build_graph().source
        for label in ("oci_image", "system layer", "slides deck"):
            self.assertIn(label, src)

    def test_dogfooding_edge_present(self):
        # the source -> slides "transclude" edge encodes the dogfooding thesis
        self.assertIn("transclude", app.build_graph().source)

    def test_main_prints_dot_without_dot_binary(self):
        # default mode must succeed even where `dot` is absent
        self.assertEqual(app.main([]), 0)


if __name__ == "__main__":
    unittest.main()
