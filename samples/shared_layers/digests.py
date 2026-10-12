"""Prove which layers two images share (workshop Q5).

Diffs the layer-blob digests of the two images' manifests. The base image layers
and the common layer are byte-identical, so they share digests (and therefore
build once, cache once, and push once).

    bazel run //samples/shared_layers:digests

The manifests arrive as runfiles of this target, so `bazel run` builds both
images first, in the same invocation, and this runs on the pinned interpreter.
It used to be a shell script that started a second Bazel server and parsed the
JSON with the host's `python3`.
"""

import json
import sys


def layers(paths, name):
    """The layer digests in <name>_manifest.json, in manifest order."""
    manifest = next(p for p in paths if p.endswith("/%s_manifest.json" % name))
    with open(manifest) as f:
        return [layer["digest"] for layer in json.load(f)["layers"]]


def main(paths):
    a = layers(paths, "image_api")
    b = layers(paths, "image_worker")
    print("== image_api layers ==", *a, sep="\n")
    print("== image_worker layers ==", *b, sep="\n")
    print("== SHARED (built once, pushed once) ==", *sorted(set(a) & set(b)), sep="\n")


if __name__ == "__main__":
    main(sys.argv[1:])
