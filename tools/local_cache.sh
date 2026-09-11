#!/usr/bin/env bash
# A real REAPI remote cache on localhost, in one pinned static binary.
#
#   bazel run //tools:local_cache            # start (idempotent)
#   bazel run //tools:local_cache -- stop    # shut it down
#   bazel run //tools:local_cache -- purge   # stop and delete the store
#
# This is what makes the Module 4 material runnable without an account: a shared
# cache, `--remote_download_minimal` ("without the bytes"), and rules_img's lazy
# push strategy all speak the same REAPI gRPC that bazel-remote serves.
# See labs/REMOTE.md.
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

# The rule passes the pinned bazel-remote binary in as argv[1].
BAZEL_REMOTE="$(rlocation "$1")"
shift

GRPC_PORT=9092
HTTP_PORT=9090
STORE="${HOME}/.cache/bwb-remote-cache"
PIDFILE="${HOME}/.cache/bwb-remote-cache.pid"
LOG="${HOME}/.cache/bwb-remote-cache.log"

port_busy() { (exec 3<>"/dev/tcp/127.0.0.1/$GRPC_PORT") >/dev/null 2>&1; }

stop_cache() {
  if [[ -f "$PIDFILE" ]] && kill "$(cat "$PIDFILE")" 2>/dev/null; then
    echo "stopped remote cache (pid $(cat "$PIDFILE"))"
  else
    echo "nothing to stop on localhost:$GRPC_PORT"
  fi
  rm -f "$PIDFILE"
}

case "${1:-}" in
  stop)
    stop_cache
    exit 0
    ;;
  purge)
    stop_cache
    rm -rf "$STORE"
    echo "purged $STORE  (next build is a cold cache)"
    exit 0
    ;;
  "") ;;
  *)
    echo "usage: bazel run //tools:local_cache [-- stop|purge]" >&2
    exit 2
    ;;
esac

if [[ -f "$PIDFILE" ]] && kill -0 "$(cat "$PIDFILE")" 2>/dev/null; then
  echo "remote cache already running on localhost:$GRPC_PORT"
  exit 0
fi

if port_busy; then
  echo "ERROR: something is already listening on localhost:$GRPC_PORT (ss -ltnp | grep :$GRPC_PORT)" >&2
  exit 1
fi

mkdir -p "$STORE"
nohup "$BAZEL_REMOTE" \
  --dir "$STORE" \
  --max_size 5 \
  --grpc_port "$GRPC_PORT" \
  --port "$HTTP_PORT" \
  >"$LOG" 2>&1 &
pid=$!
echo "$pid" >"$PIDFILE"

for _ in $(seq 1 100); do
  # A live process of OURS *and* a live port — checking only the port turns a
  # failed bind into a false "started".
  kill -0 "$pid" 2>/dev/null && port_busy && break
  sleep 0.1
done
if ! kill -0 "$pid" 2>/dev/null || ! port_busy; then
  rm -f "$PIDFILE"
  echo "remote cache failed to start:" >&2
  sed 's/^/  /' "$LOG" >&2
  exit 1
fi

cat <<EOF
started bazel-remote on localhost:$GRPC_PORT (gRPC) / localhost:$HTTP_PORT (HTTP)
  store: $STORE  (5 GiB cap)

  bazel build --config=local-cache //samples/...   # use it
  bazel build --config=local-bwb   //samples/...   # ...and don't download the bytes

  stop:  bazel run //tools:local_cache -- stop
  purge: bazel run //tools:local_cache -- purge    # forces a cold cache
EOF
