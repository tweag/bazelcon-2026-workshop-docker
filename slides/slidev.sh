#!/usr/bin/env bash
# Wrapper so the Slidev deck is driven through Bazel targets.
#
# Pragmatic (non-hermetic): runs the locally-installed Slidev from
# slides/node_modules. Hermetic wrapping via aspect_rules_js is the spike
# tracked in TASK §3.8. Run targets, not build outputs:
#   bazel run //slides:present
#   bazel run //slides:export_pdf
set -euo pipefail
cd "${BUILD_WORKSPACE_DIRECTORY}/slides"
[ -d node_modules ] || npm install
exec npx slidev "$@"
