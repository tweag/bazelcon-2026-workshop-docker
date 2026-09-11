#!/usr/bin/env bash
# `crane`, the go-containerregistry CLI, as a runnable Bazel target.
#
#   bazel run //tools:crane_cli -- manifest localhost:5000/bwb/python-graphviz:latest
#   bazel run //tools:crane_cli -- config   localhost:5000/bwb/python-graphviz:latest
#   bazel run //tools:crane_cli -- export   localhost:5000/bwb/python-graphviz:latest - | tar tvf -
#
# //tools:crane is an alias onto a filegroup, so it cannot be `bazel run`. This
# wrapper gives the same pinned static binary an executable target, which is how
# the appendix slide inspects an image from outside Bazel with nothing installed.
# --- begin runfiles.bash initialization v3 (Bazel's canonical snippet) -------
set -uo pipefail
set +e
f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090,SC1091
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
  source "$0.runfiles/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  { echo >&2 "ERROR: cannot find $f"; exit 1; }
set -e
# --- end runfiles.bash initialization v3 -------------------------------------

set -euo pipefail

crane="$(rlocation "$1")"
shift
exec "$crane" "$@"
