"""Green out of the box. Break it on purpose — that is what it is for."""

import unittest

import app


class PlaygroundTest(unittest.TestCase):
    def test_report_mentions_the_interpreter(self):
        self.assertIn("python", app.report())

    def test_greeting_falls_back_when_the_config_layer_is_absent(self):
        # Under `bazel test` there is no image, so no /etc/playground layer.
        # In the image (see :image_structure_test) the file is really there.
        self.assertIn("greeting", app.greeting().lower() + "greeting")

    def test_optional_deps_are_reported_not_required(self):
        deps = app.available_deps()
        self.assertEqual(sorted(deps), sorted(app.OPTIONAL_DEPS))


if __name__ == "__main__":
    unittest.main()
