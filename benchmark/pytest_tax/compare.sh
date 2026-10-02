#!/usr/bin/env bash
# The "docker tax" — measure the per-edit iteration cost of "just put the test
# in a container to make it hermetic" vs. running it under Bazel.
#
# Non-hermetic utility (bazel run): shells out to bazel + docker, times them.
# A dedicated --output_base keeps the nested bazel warm without deadlocking on
# the outer `bazel run` server lock; it still reuses the repo's --disk_cache.
# --symlink_prefix=/ keeps it from repointing the workspace's bazel-bin into $OB.
set -euo pipefail
cd "${BUILD_WORKSPACE_DIRECTORY}/benchmark/pytest_tax"

OB="${HOME}/.cache/bazel-pytest-tax-ob"
TARGET="//benchmark/pytest_tax:tests"
TAG="pytest-tax-bench"

restore() { printf '0\n' > marker.txt; }
trap restore EXIT

have_docker=1
command -v docker >/dev/null 2>&1 || have_docker=0

ms() { date +%s%3N; }
timeit() { local s e; s=$(ms); "$@" >/dev/null 2>&1 || true; e=$(ms); echo $((e - s)); }

echo "== pytest 'docker tax' benchmark =="
echo "(real wall-clock on this machine; absolute numbers vary, the ratio is the point)"

# Warm both caches.
printf '0\n' > marker.txt
bazel --output_base="$OB" test --symlink_prefix=/ "$TARGET" >/dev/null 2>&1 || true
[ "$have_docker" = 1 ] && docker build -q -t "$TAG" . >/dev/null 2>&1 || true

# Incremental: simulate a one-line code change, time each tool to re-validate.
printf 'iter-1\n' > marker.txt
bazel_warm=$(timeit bazel --output_base="$OB" test --symlink_prefix=/ "$TARGET")

docker_warm=-1
if [ "$have_docker" = 1 ]; then
  printf 'iter-2\n' > marker.txt
  docker_warm=$(timeit docker build -q -t "$TAG" .)
fi

# Cold docker: the upfront "make it hermetic with a container" cost.
docker_cold=-1
[ "$have_docker" = 1 ] && docker_cold=$(timeit docker build --no-cache -q -t "$TAG" .)

printf '\n%-34s %10s\n' "scenario" "ms"
printf '%-34s %10s\n' "bazel test  (warm, after edit)" "$bazel_warm"
printf '%-34s %10s\n' "docker build (warm, after edit)" "$docker_warm"
printf '%-34s %10s\n' "docker build (cold, --no-cache)" "$docker_cold"

if [ "$docker_warm" -ge 0 ] && [ "$bazel_warm" -gt 0 ]; then
  printf '\nper-edit docker tax: ~%sx slower than bazel\n' "$(( docker_warm / bazel_warm ))"
fi
