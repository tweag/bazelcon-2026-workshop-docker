#!/usr/bin/env bash
# Bazel workspace status: key/value pairs that stamped targets can read.
# Wired up in .bazelrc via --workspace_status_command.
#
# STABLE_BWB_ID  a short, stable per-laptop ID (hash of user@host). The ttl.sh
#                push targets put it in the repository name, so a room full of
#                attendees each pushes to their own ttl.sh/bwb-<id>/graphviz
#                instead of overwriting one shared tag. It is a hash, so no
#                username or hostname ends up on a public registry. It stays the
#                same across runs, so the second push still finds its blobs.
#
# Only targets with `stamp = "force"` (or a build with --stamp) read this, so
# every other action keeps its cache key.
set -euo pipefail

if command -v sha256sum >/dev/null 2>&1; then
  sha() { sha256sum; }
else
  sha() { shasum -a 256; } # macOS
fi

# The deck transcludes the region below (`<<< ../tools/workspace_status.sh#bwb_id`).
#region bwb_id
bwb_id=$(printf '%s@%s' "${USER:-$(id -un)}" "$(hostname)" |
  sha | cut -c1-8)
echo "STABLE_BWB_ID ${bwb_id}"
#endregion
