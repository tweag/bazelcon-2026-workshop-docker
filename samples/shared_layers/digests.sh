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

# --symlink_prefix=/: leave the workspace's bazel-bin alone. Otherwise it points
# into $OB afterwards, and the next `tar tf bazel-bin/...` finds nothing.
bazel --output_base="$OB" build --symlink_prefix=/ \
  //samples/shared_layers:image_api //samples/shared_layers:image_worker >/dev/null 2>&1
bb=$(bazel --output_base="$OB" info bazel-bin 2>/dev/null)

layers() {  # rules_img writes <name>_manifest.json; print its layer digests
  python3 - "$1" <<'PY'
import json, sys
man = json.load(open(sys.argv[1]))
for layer in man["layers"]:
    print(layer["digest"])
PY
}

a=$(layers "$bb/samples/shared_layers/image_api_manifest.json")
b=$(layers "$bb/samples/shared_layers/image_worker_manifest.json")

echo "== image_api layers =="; echo "$a"
echo "== image_worker layers =="; echo "$b"
echo "== SHARED (built once, pushed once) =="
comm -12 <(echo "$a" | sort) <(echo "$b" | sort)
