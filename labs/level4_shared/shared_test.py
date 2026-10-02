"""Task 1: the worker image must reuse the api image's layers.

Reads both image manifests (no daemon, no registry) and adds up the bytes the
worker image needs that the api image doesn't already have. Two services built
from the same interpreter and the same wheel should differ only by their app code.
"""

import json
import sys
import unittest

MAX_EXTRA_BYTES = 1_000_000  # app code is a few KB; the interpreter alone is ~36 MB


def layers(path):
    with open(path) as f:
        return json.load(f)["layers"]


class WorkerReusesApiLayersTest(unittest.TestCase):
    def test_worker_adds_only_its_app_code(self):
        api, worker = layers(sys.argv[1]), layers(sys.argv[2])
        have = {l["digest"] for l in api}
        extra = [l for l in worker if l["digest"] not in have]
        extra_bytes = sum(l["size"] for l in extra)
        self.assertLessEqual(
            extra_bytes,
            MAX_EXTRA_BYTES,
            "\nThe worker image adds %.1f MB on top of the api image, in %d layer(s):\n%s\n"
            "Both services run the same interpreter and the same cryptography wheel,\n"
            "but each pkg_tar packs them into one tar together with its own .py file,\n"
            "so no layer digest matches and every byte is stored and pushed twice.\n"
            "Task 1: build each layer with layer_from_binary(binary = \":api_layered\", ...)\n"
            "instead of pkg_tar + layer_from_tar (see README.md)."
            % (
                extra_bytes / 1e6,
                len(extra),
                "\n".join("  %s  %6.1f MB" % (l["digest"][:19], l["size"] / 1e6) for l in extra),
            ),
        )


if __name__ == "__main__":
    unittest.main(argv=sys.argv[:1])
