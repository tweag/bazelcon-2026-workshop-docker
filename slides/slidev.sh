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

# Preflight: Slidev v52 (Vite/Rolldown) needs a modern Node. On an old Node the
# tooling dies deep inside ESM loading with a cryptic
# "SyntaxError: Unexpected token '.'" (unsupported optional chaining) — usually
# only after starting the PDF export. Check up front and fail with guidance.
req_major=20; req_minor=12
node_v="$(node -v 2>/dev/null || true)" # e.g. "v24.11.0"
if [ -z "$node_v" ]; then
  echo "error: 'node' not found on PATH — Slidev needs Node >= ${req_major}.${req_minor}." >&2
  exit 1
fi
v="${node_v#v}"; major="${v%%.*}"; rest="${v#*.}"; minor="${rest%%.*}"
if [ "$major" -lt "$req_major" ] || { [ "$major" -eq "$req_major" ] && [ "$minor" -lt "$req_minor" ]; }; then
  echo "error: Node ${node_v} is too old for Slidev; need >= ${req_major}.${req_minor}.0." >&2
  echo "       (An old Node otherwise fails later with a cryptic 'SyntaxError: Unexpected token .')" >&2
  echo "       Fix: 'nvm use' picks up slides/.nvmrc (Node 24, matching CI)." >&2
  exit 1
fi

[ -d node_modules ] || npm install
exec npx slidev "$@"
