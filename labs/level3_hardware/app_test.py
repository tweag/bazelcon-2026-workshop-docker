"""Task 0: bindings + kernel are wired and the device probe runs cleanly."""

import unittest

import app


class HardwareWallTest(unittest.TestCase):
    def test_kernel_source(self):
        self.assertIn("__kernel", app.KERNEL)

    def test_device_probe_runs(self):
        # The answer depends on the environment; that's the hardware wall.
        self.assertIsInstance(app.has_opencl_device(), bool)


if __name__ == "__main__":
    unittest.main()
