#!/usr/bin/env bash
# Prove which layers two images share (workshop Q5).
# Builds both images and diffs their layer-blob digests — the base image
# layers and the common layer are byte-identical, so they share digests (and
# therefore build once, cache once, and push once).
#
#   bazel run //samples/shared_layers:digests
set -euo pipefail
cd "${BUILD_WORKSPACE_DIRECTORY}"
OB="${HOME}/.cache/bazel-shared-layers-ob"   # dedicated, warm, reuses --disk_cache

bazel --output_base="$OB" build \
  //samples/shared_layers:image_a //samples/shared_layers:image_b >/dev/null 2>&1
bb=$(bazel --output_base="$OB" info bazel-bin 2>/dev/null)

layers() {  # print this image's layer digests, one per line
  python3 - "$1" <<'PY'
import json, os, sys
d = sys.argv[1]
idx = json.load(open(os.path.join(d, "index.json")))
md = idx["manifests"][0]["digest"].split(":")[1]
man = json.load(open(os.path.join(d, "blobs", "sha256", md)))
for layer in man["layers"]:
    print(layer["digest"])
PY
}

a=$(layers "$bb/samples/shared_layers/image_a")
b=$(layers "$bb/samples/shared_layers/image_b")

echo "== image_a layers =="; echo "$a"
echo "== image_b layers =="; echo "$b"
echo "== SHARED (built once, pushed once) =="
comm -12 <(echo "$a" | sort) <(echo "$b" | sort)
