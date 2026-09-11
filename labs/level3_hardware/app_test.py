"""Surface: the bindings + kernel are wired and the device probe runs cleanly.
Whether a device actually exists depends on the *environment* (an ICD + driver)
— that's the hardware wall. We show it for real in the image (deep) and by
running the kernel on CPU via POCL (abyss; see HINT.md), not by assuming the
dev host has no GPU."""

import unittest

import app


class HardwareWallTest(unittest.TestCase):
    def test_kernel_source(self):
        self.assertIn("__kernel", app.KERNEL)

    def test_device_probe_runs(self):
        # Answers cleanly whether or not an ICD/device is present; the *answer*
        # is environment-dependent, which is the whole point of this level.
        self.assertIsInstance(app.has_opencl_device(), bool)


if __name__ == "__main__":
    unittest.main()
