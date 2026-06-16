#!/usr/bin/env bash
# Start a local OCI registry (registry:2) on localhost:5000 for the push lab.
# Idempotent: re-running just reports it's already up.
#   bazel run //tools:local_registry
set -euo pipefail
name=bwb-registry
if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$name"; then
  echo "registry already running on localhost:5000"
else
  docker rm -f "$name" >/dev/null 2>&1 || true
  docker run -d -p 5000:5000 --name "$name" registry:2 >/dev/null
  echo "started registry:2 on localhost:5000  (stop: docker rm -f $name)"
fi
