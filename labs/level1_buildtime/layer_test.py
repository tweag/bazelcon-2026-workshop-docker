"""DEEP rung — look inside the layer and prove the *prebuilt* wheel rode along.

`build_test` can only tell you the image assembled; it cannot tell you what is
in it. This test opens the layer tarball and asserts two things:

  1. cryptography's compiled Rust extension (`_rust.abi3.so`) is in the layer —
     so the wheel really was packed, not just declared.
  2. no build-time leftovers (`.c`, `.rs`, `Cargo.toml`, `setup.py` for
     cryptography) came along — i.e. Bazel *consumed* a prebuilt manylinux
     wheel; no compiler ran and no sdist was unpacked.

Reading a layer like this is the daemonless way to answer "what is actually in
my image?" — the same question `container_structure_test` answers in Levels 2
and 3, done by hand so you can see there is no magic.
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
        # If pip had fallen back to the sdist, the layer would carry Rust/C
        # sources instead of (or next to) a ready-made .so.
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
