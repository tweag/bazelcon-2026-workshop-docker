"""Task 2: open the layer tar and prove the prebuilt wheel is inside it.

Checks that cryptography's compiled `_rust.abi3.so` is packed and that no
source-build leftovers (`.rs`, `.c`, `Cargo.toml`) came along.
"""

import sys
import tarfile
import unittest

LAYER_TAR = sys.argv[1] if len(sys.argv) > 1 else None


def layer_members():
    with tarfile.open(LAYER_TAR) as tar:
        return tar.getnames()


class WheelIsInTheLayerTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.names = layer_members()

    def test_compiled_extension_is_packed(self):
        so = [n for n in self.names if n.endswith("cryptography/hazmat/bindings/_rust.abi3.so")]
        self.assertTrue(
            so,
            "cryptography's compiled extension is not in the layer.\n"
            "The image assembled, but the wheel never made it in — add\n"
            "requirement(\"cryptography\") to the py_binary's deps.",
        )

    def test_no_source_build_leftovers(self):
        # An sdist fallback would leave Rust/C sources in the layer.
        leftovers = [
            n
            for n in self.names
            if "/cryptography" in n and n.endswith(("Cargo.toml", "Cargo.lock", ".rs", ".c"))
        ]
        self.assertEqual(
            leftovers,
            [],
            "Found source-build leftovers in the layer: %s\n"
            "That means a source distribution was built against the host "
            "toolchain — the build-time trap this level is about." % leftovers,
        )


if __name__ == "__main__":
    unittest.main(argv=sys.argv[:1])
