"""Task 1: the worker image must reuse the api image's layers.

Reads both image manifests (no daemon, no registry) and compares their layer
digests. Two services built from the same interpreter and the same wheel should
differ by exactly one layer each: their own app code.
"""

import json
import sys
import unittest

MAX_EXTRA_BYTES = 1_000_000  # app code is a few KB; the interpreter alone is ~36 MB


def layers(path):
    with open(path) as f:
        return json.load(f)["layers"]


def mb(layer_list):
    return "\n".join("  %s  %6.1f MB" % (l["digest"][:19], l["size"] / 1e6) for l in layer_list)


class WorkerReusesApiLayersTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.api, cls.worker = layers(sys.argv[1]), layers(sys.argv[2])
        have = {l["digest"] for l in cls.api}
        cls.extra = [l for l in cls.worker if l["digest"] not in have]
        cls.api_only = [l for l in cls.api if l["digest"] not in {l["digest"] for l in cls.worker}]

    def test_worker_adds_only_its_app_code(self):
        extra_bytes = sum(l["size"] for l in self.extra)
        self.assertLessEqual(
            extra_bytes,
            MAX_EXTRA_BYTES,
            "\nThe worker image adds %.1f MB on top of the api image, in %d layer(s):\n%s\n"
            "Both services run the same interpreter and the same cryptography wheel,\n"
            "but each pkg_tar packs them into one tar together with its own .py file,\n"
            "so no layer digest matches and every byte is stored and pushed twice.\n"
            "Task 1: build each layer with layer_from_binary(binary = \":api_layered\", ...)\n"
            "instead of pkg_tar + layer_from_tar (see README.md)."
            % (extra_bytes / 1e6, len(self.extra), mb(self.extra)),
        )

    def test_each_service_has_its_own_app_layer(self):
        # Reusing the api's layers wholesale also adds 0 bytes, but the worker
        # would then run the api's code. And a worker that drops the shared
        # layers leaves the api's interpreter and wheel unshared.
        own = (len(self.api_only), len(self.extra))
        small = all(l["size"] <= MAX_EXTRA_BYTES for l in self.api_only + self.extra)
        self.assertTrue(
            own == (1, 1) and small,
            "\nEach image should have exactly one small layer the other lacks (its app code).\n"
            "Only in the api: %d layer(s)\n%s\nOnly in the worker: %d layer(s)\n%s\n"
            "Give each image_manifest its own service's layers: :api_layers and :worker_layers."
            % (len(self.api_only), mb(self.api_only), len(self.extra), mb(self.extra)),
        )


if __name__ == "__main__":
    unittest.main(argv=sys.argv[:1])
