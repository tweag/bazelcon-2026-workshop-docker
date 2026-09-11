#!/usr/bin/env bash
# A real remote-EXECUTION cluster on localhost (Buildfarm + Redis, 3 containers).
#
#   bazel run //tools:local_rbe             # start (idempotent)
#   bazel run //tools:local_rbe -- stop     # shut it down
#   bazel run //tools:local_rbe -- logs     # tail the cluster
#   bazel run //tools:local_rbe -- status   # what's up
#
# Non-hermetic by design: it needs a Docker daemon. Unlike //tools:local_cache
# (one static binary, no daemon), remote execution needs a worker whose OS can
# actually run your actions — so the worker IS a container image, and choosing
# it is part of the lesson. See labs/REMOTE.md.
set -euo pipefail

cd "${BUILD_WORKSPACE_DIRECTORY:?must be run via 'bazel run //tools:local_rbe'}/tools/rbe"

if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
  compose() { docker compose "$@"; }
elif command -v docker-compose >/dev/null 2>&1; then
  compose() { docker-compose "$@"; }
else
  cat >&2 <<'EOF'
ERROR: this lab needs Docker Compose, and it isn't on PATH.

Remote execution needs somewhere to execute. If you only want the caching and
"without the bytes" material, use the daemonless cache instead — it covers
everything except actually running actions off-box:

    bazel run //tools:local_cache
    bazel build --config=local-bwb //samples/...
EOF
  exit 1
fi

case "${1:-up}" in
  stop | down)
    compose down --remove-orphans
    echo "cluster stopped"
    ;;
  logs)
    compose logs -f --tail=100
    ;;
  status)
    compose ps
    ;;
  up)
    compose up -d
    echo "waiting for the scheduler on localhost:8980 ..."
    for _ in $(seq 1 120); do
      (exec 3<>/dev/tcp/127.0.0.1/8980) >/dev/null 2>&1 && break
      sleep 0.5
    done
    if ! (exec 3<>/dev/tcp/127.0.0.1/8980) >/dev/null 2>&1; then
      echo "scheduler never came up. bazel run //tools:local_rbe -- logs" >&2
      exit 1
    fi
    cat <<'EOF'
Buildfarm is up: scheduler on localhost:8980, one worker.

  bazel build --config=local-rbe //samples/python:image
  bazel test  --config=local-rbe //labs/...

Expect failures on your first try, and read them — an action that passes locally
and fails remotely is a hermeticity bug the local sandbox was hiding for you.
Two things here genuinely cannot run remotely, by design: //tools:render_graph
and //tools:local_registry shell out to the host.

  logs: bazel run //tools:local_rbe -- logs
  stop: bazel run //tools:local_rbe -- stop
EOF
    ;;
  *)
    echo "usage: bazel run //tools:local_rbe [-- up|stop|logs|status]" >&2
    exit 2
    ;;
esac
