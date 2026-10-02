#!/usr/bin/env bash
# Start a local OCI registry on localhost:5000 for the push lab.
#
#   bazel run //tools:local_registry              # start (idempotent)
#   bazel run //tools:local_registry -- stop      # shut it down
#   bazel run //tools:local_registry -- --hermetic  # force the no-daemon backend
#
# Two backends, same endpoint:
#   docker    registry:2 in a container (what the deck shows). Used when a
#             Docker daemon is reachable.
#   hermetic  `crane registry serve`, a full OCI registry in one pinned static
#             binary fetched by Bazel. No daemon, no network, no root.
#
# Either way `bazel run //samples/python:push` works unchanged: rules_img (via
# go-containerregistry) already treats localhost:PORT as plain HTTP, so no
# --insecure flag is needed.
# --- begin runfiles.bash initialization v3 (Bazel's canonical snippet) -------
set -uo pipefail
set +e
f=bazel_tools/tools/bash/runfiles/runfiles.bash
# shellcheck disable=SC1090,SC1091
source "${RUNFILES_DIR:-/dev/null}/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "${RUNFILES_MANIFEST_FILE:-/dev/null}" | cut -f2- -d' ')" 2>/dev/null ||
  source "$0.runfiles/$f" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  source "$(grep -sm1 "^$f " "$0.exe.runfiles_manifest" | cut -f2- -d' ')" 2>/dev/null ||
  {
    echo >&2 "ERROR: cannot find $f"
    exit 1
  }
f=
set -e
# --- end runfiles.bash initialization v3 ------------------------------------

# The rule passes the pinned crane binary in as argv[1] ($(rlocationpath :crane)).
CRANE="$(rlocation "$1")"
shift

PORT="${BWB_REGISTRY_PORT:-5000}"
CONTAINER=bwb-registry
STORE="${HOME}/.cache/bwb-registry"
PIDFILE="${HOME}/.cache/bwb-registry.pid"
LOG="${HOME}/.cache/bwb-registry.log"

mode=auto
case "${1:-}" in
  stop) mode=stop ;;
  --hermetic) mode=hermetic ;;
  --docker) mode=docker ;;
  "") ;;
  *) echo "usage: bazel run //tools:local_registry [-- stop|--hermetic|--docker]" >&2; exit 2 ;;
esac

have_docker() { command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; }
port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$PORT") >/dev/null 2>&1; }

stop_all() {
  local stopped=0
  if command -v docker >/dev/null 2>&1 && docker rm -f "$CONTAINER" >/dev/null 2>&1; then
    echo "stopped registry:2 container $CONTAINER"
    stopped=1
  fi
  if [[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "stopped hermetic crane registry (pid $(cat "$PIDFILE"))"
    stopped=1
  fi
  rm -f "$PIDFILE"
  [[ "$stopped" == 1 ]] || echo "nothing to stop on localhost:$PORT"
}

start_docker() {
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
    echo "registry already running on localhost:$PORT  (registry:2)"
    return
  fi
  docker rm -f "$CONTAINER" >/dev/null 2>&1 || true
  docker run -d -p "$PORT:5000" --name "$CONTAINER" registry:2 >/dev/null
  echo "started registry:2 on localhost:$PORT"
  echo "  stop: bazel run //tools:local_registry -- stop"
}

start_hermetic() {
  if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "registry already running on localhost:$PORT  (hermetic crane)"
    return
  fi
  # Our own registry:2 from an earlier plain run (the deck does exactly that) is
  # just as good a registry; reuse it rather than calling it a stranger.
  if command -v docker >/dev/null 2>&1 &&
     docker ps --format '{{.Names}}' 2>/dev/null | grep -qx "$CONTAINER"; then
    echo "registry already running on localhost:$PORT  (registry:2; '-- stop' first to switch to crane)"
    return
  fi
  # Somebody else's process on the port is the common workshop failure. Say so
  # instead of starting a server that silently loses the bind race.
  if port_busy; then
    cat >&2 <<EOF
ERROR: something is already listening on localhost:$PORT, and it isn't ours.

    ss -ltnp | grep :$PORT

Stop it, or pick another port:

    BWB_REGISTRY_PORT=5001 bazel run //tools:local_registry -- --hermetic
    bazel run //samples/python:push -- --registry localhost:5001
EOF
    exit 1
  fi
  mkdir -p "$STORE"
  # --disk, not the default in-memory store: blobs must survive a restart or the
  # "push again, only the changed blob uploads" demo can't be repeated.
  nohup "$CRANE" registry serve --address ":$PORT" --disk "$STORE" \
    >"$LOG" 2>&1 &
  local pid=$!
  echo "$pid" >"$PIDFILE"
  for _ in $(seq 1 50); do
    # Both conditions: a live process of OURS, and a port that answers. Checking
    # only the port makes an "address already in use" crash look like success.
    kill -0 "$pid" 2>/dev/null && port_busy && break
    sleep 0.1
  done
  if ! kill -0 "$pid" 2>/dev/null || ! port_busy; then
    rm -f "$PIDFILE"
    echo "registry failed to start:" >&2
    sed 's/^/  /' "$LOG" >&2
    exit 1
  fi
  echo "started hermetic crane registry on localhost:$PORT  (blobs in $STORE)"
  echo "  no daemon, no root — the binary is pinned in MODULE.bazel"
  echo "  stop: bazel run //tools:local_registry -- stop"
}

case "$mode" in
  stop) stop_all ;;
  docker) start_docker ;;
  hermetic) start_hermetic ;;
  auto)
    if have_docker; then start_docker; else
      echo "no Docker daemon — using the hermetic backend"
      start_hermetic
    fi
    ;;
esac
