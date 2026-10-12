# Remote lab — cache, registry, remote execution, "without the bytes"

**Goal:** run the delivery half of the deck on your own machine: a shared remote
cache, an OCI registry, lazy push, Build without the Bytes, and a remote
execution cluster. You don't need an account or an API key, and the cache and
registry don't need Docker either.

**Deck concepts:** daemonless push · only missing blobs move · eager vs. lazy
push · Building Without Bytes · remote cache + RBE · reading an image with no
daemon (`crane`, OCI layouts).

## Start

```bash
bazel run //tools:local_cache       # REAPI cache      -> localhost:9092
bazel run //tools:local_registry    # OCI registry     -> localhost:5000
bazel run //tools:local_rbe         # remote execution -> localhost:8980 (needs Docker)
```

Each one takes `-- stop`. The cache also takes `-- purge`, which deletes the
store so your next build is genuinely cold.

## Tasks

| # | Run | Done when |
|---|---|---|
| 1 | `bazel build --config=local-cache //samples/...` twice, with `bazel clean` in between | the second build reports ~260 remote cache hits (§1) |
| 2 | `bazel build --config=local-bwb //samples/python:image.tar` | the output on disk is KB instead of MB (§2) |
| ★ | delete one blob from the cache, then rebuild | you've seen `Lost inputs` and recovered from it three ways (§2 ★) |
| 3 | `bazel run //samples/python:push`, edit `app.py`, push again | the second push uploads only the changed blobs (§3) |
| 4 | `bazel run --config=local-bwb ... //samples/python:push_lazy` | 0 blobs come from disk (§3) |
| 5 | `bazel run //tools:crane_cli -- manifest localhost:5000/bwb/python-graphviz:latest` | you've read a pushed image with no daemon (§3) |
| 6 | `bazel test --config=local-rbe //samples/python/... //labs/playground/...` | tests run on the local Buildfarm, and you know why `//...` doesn't (§4) |

Every number below was measured against this repo. Where something does not
work, it says so.

---

## 0 · Why these are Bazel targets

`bazel-remote` and `crane` are pinned static binaries fetched by `MODULE.bazel`
with sha256s — the same way the workshop pins its base image and its `.deb`s. So
the infrastructure the lab talks about is itself hermetic, and the whole lab
works on a plane.

Remote *execution* is the exception: it needs a worker whose OS can run your
actions, so it is three containers and it needs Docker. Choosing that worker
image turns out to be the entire lesson — see §4.

---

## 1 · A shared cache

```bash
bazel run //tools:local_cache
bazel clean
bazel build --config=local-cache //samples/...      # cold: uploads
bazel clean
bazel build --config=local-cache //samples/...      # warm: downloads
```

The second run:

```
INFO: 380 processes: 260 remote cache hit, 120 internal.
```

A `bazel clean` threw away every local output and the build still did almost no
work. That is the "shared pantry" slide, for real — and on a team, those 260 hits
are someone else's build, not yours.

> **`--disk_cache=` is doing real work here.** `.bazelrc` turns on a disk cache
> for every build, and a disk hit is served *before* Bazel asks the remote. The
> `local-cache` config clears it, or the demo would look like the remote cache
> does nothing.

---

## 2 · Building without the bytes

```bash
bazel build --config=local-bwb //samples/python:image.tar
```

`local-bwb` adds `--remote_download_minimal`: outputs stay in the remote CAS and
are never materialised locally unless something actually asks for them.

| `//samples/python:image.tar` | on disk afterwards |
|---|---|
| normal build | **82 MB** |
| `--config=local-bwb` | **742 KB** |

Same build, same graph, same result — 110× less local I/O. For container images
this is the whole game: an image is a set of blobs, and the machine that
*assembles* it rarely needs to hold them.

### ★ Stretch — when the cache forgets

There's a price for that. Bazel now *remembers* outputs it never downloaded, and
it trusts the cache to keep them. Real caches evict: by size, by age
(`--experimental_remote_cache_ttl` defaults to 3h), or because someone purged
them. If a blob goes missing between the build that skipped it and the action
that needs it, you get this:

```
ERROR: .../samples/python/BUILD.bazel:136:11: PushMetadata samples/python/push_lazy.layer_path_hints
failed: Lost inputs no longer available remotely: samples/python/push_lazy.configuration.json (4ecc1dbc…/84)
```

That was seen for real in this repo: the 5 GB cap on the disk cache in
`.bazelrc` evicted the blob in the middle of a `bazel build //...`. You can make
it happen on purpose. The disk cache is a cache you can reach with `rm`, so no
server is needed, and `--remote_download_toplevel` gives it the same
without-the-bytes behaviour as `local-bwb`.

**1. Build without the bytes from a warm cache.** The first build fills the
cache. After the `bazel clean`, everything comes back from it:

```bash
bazel build //samples/python:push_lazy
bazel clean
bazel build --remote_download_toplevel --execution_log_json_file=/tmp/exec.json \
  //samples/python:push_lazy
ls bazel-bin/samples/python/push_lazy.configuration.json     # No such file: it stayed in the cache
```

**2. Be the eviction.** The execution log has the digest of the file Bazel
skipped. Delete that blob, and delete the output of the action that reads it,
so that action has to run again:

```bash
H=$(grep -A3 '"path": ".*push_lazy.configuration.json"' /tmp/exec.json | grep -o '[0-9a-f]\{64\}' | head -1)
rm ~/.cache/bazel-disk/cas/${H:0:2}/$H
rm -f bazel-bin/samples/python/push_lazy.layer_path_hints
```

**3. Watch it fail.** Bazel normally retries on its own (more on that in
step 4), so turn that off. `no-cache` makes `PushMetadata` really run. Without
it, Bazel takes the action's result from the cache and never needs the missing
input:

```bash
bazel build --remote_download_toplevel --experimental_remote_cache_eviction_retries=0 \
  --modify_execution_info=PushMetadata=+no-cache //samples/python:push_lazy
# ERROR: ... PushMetadata ... failed: Unexpected lost inputs ...
# ERROR: Build did NOT complete successfully
```

**4. Recover, three ways.** Repeat steps 1–2 before each one, then run step 3's
command with one change:

| Change to step 3 | What you see | Cost |
|---|---|---|
| drop `--experimental_remote_cache_eviction_retries=0` (the default is 5) | the same `ERROR:`, then `Found transient remote cache error, retrying the build...`, then success | the whole build runs again, and the scary error is still printed |
| add `--rewind_lost_inputs` | success, no error | Bazel re-runs only the action that produced the lost file. The flag is experimental in Bazel 9.1.1 and missing from `bazel help` |
| `--remote_download_outputs=all` instead of `--remote_download_toplevel` (in steps 1 and 3) | step 1's `ls` finds the file, and nothing can get lost | every byte is downloaded, so you've given up building without the bytes |

The last row is what this repo's `.bazelrc` does by default, because the disk
cache cap made the race a real problem for attendees. The `*-bwb` and
`local-rbe` configs turn it back to `--remote_download_minimal`. With a hosted
cache, a further option is `--experimental_remote_cache_lease_extension`: it
asks the server to keep the blobs a running build depends on. It works only if
the server supports it, and that hasn't been tested with the services in this lab.

---

## 3 · A local registry, and lazy push

```bash
bazel run //tools:local_registry
bazel run //samples/python:push
```

`//tools:local_registry` uses Docker's `registry:2` when a daemon is around, and
otherwise serves `crane registry serve` from the pinned binary — same endpoint
either way. `rules_img` needs no `--insecure` flag: go-containerregistry already
treats `localhost:PORT` as plain HTTP.

**Dedup, measured.** Push, edit one line of `app.py`, push again, revert, push a
third time:

| push | blob transfers |
|---|---|
| 1 — first ever | 7 |
| 2 — after editing `app.py` | **3** |
| 3 — after reverting | **2** |

Push 3 produced a digest byte-identical to push 1. Same inputs, same image, and
the registry recognised it without being told.

### Lazy push does not need RBE

A common assumption is that `strategy = "lazy"` needs remote execution. It
doesn't — it needs a remote **cache**, which is a much lower bar. Point `img` at
the local one:

```bash
bazel run --config=local-bwb \
  --@rules_img//img/settings:remote_cache=grpc://localhost:9092 \
  //samples/python:push_lazy -- --registry localhost:5000
```

```
blob transfers: 0 from disk, 0 from disk cache, 0 from container registry, 2 from remote cache
```

Zero blobs from disk. The push tool streamed them straight out of the CAS over
ByteStream — no giant runfiles, no remote executor. Compare the two targets'
runfiles: `push_eager` carries 5 layer blob entries (~78 MB), `push_lazy` carries
a `layer_hints` file instead (~59 KB).

### Read the image back, with no daemon

A registry is also a way to *read* an image. `crane` is a pinned static binary,
so nothing needs to be installed:

```bash
bazel run //tools:crane_cli -- manifest localhost:5000/bwb/python-graphviz:latest
bazel run //tools:crane_cli -- export localhost:5000/bwb/python-graphviz:latest - \
  | tar tf - | grep bin/dot
```

The `grep` prints nothing, and that's the point: the Python sample ships no
`dot`. That's the ghost from the deck, proven without starting a container.

On disk, the default output is a *sparse* OCI layout (`image_sparse_oci_layout/`)
that deliberately leaves out the layer bytes, which is why `skopeo` and `dive`
bounce off it. Ask for a real one with `bazel build //samples/python:image.oci`
(a directory of symlinks) or `:image.oci.tar` (real bytes, packed).

---

## 4 · Remote execution (advanced)

```bash
bazel run //tools:local_rbe                          # Buildfarm + Redis, 3 containers
bazel build --config=local-rbe //samples/python:image
bazel test  --config=local-rbe //samples/python/... //labs/playground/...
```

**What works.** Everything that isn't downstream of an apt layer — 6 of 6 tests
green, including both daemonless `container_structure_test`s:

```
173 processes: 3 action cache hit, 120 internal, 4 local, 53 remote.
Executed 6 out of 6 tests: 6 tests pass.
```

**What doesn't, and why it's the point.** On a laptop whose gcc differs from
the worker's, `bazel test --config=local-rbe //...` fails (here: Ubuntu 22.04,
gcc 11, against the Ubuntu 24.04 / gcc 13 worker):

```
Compiling version.c [for tool] failed:
absolute path inclusion(s) found in rule '@@gawk+//:awk':
  '/usr/lib/gcc/x86_64-linux-gnu/13/include/stdbool.h'
```

Bazel's auto-detected C++ toolchain describes **your machine's** compiler,
including the list of system header directories it's allowed to include. The
action then runs on the worker, with the *worker's* gcc and its headers. They
aren't in your machine's list, so Bazel rejects the action. `gawk` is a build
tool for `rules_distroless`' genrule, so this takes out every apt-layer target:
`//samples/distroless`, `//labs/level0_graphviz`, `//labs/level2_ghost`,
`//labs/level3_hardware`.

If your host happens to run the same gcc as the worker (a GitHub Ubuntu 24.04
runner does), it passes. That's a coincidence, not hermeticity; CI checks
both sides of it.

Nothing is broken. Remote execution simply *reported* a non-hermeticity your
laptop had been quietly covering for — which is the single best argument for
adopting it. The fix is to use a hermetic C++ toolchain instead of letting
Bazel autodetect the host compiler. This repo ships one, opt-in:
`--config=hermetic-cc` (a pinned zig cc from
[`hermetic_cc_toolchain`](https://github.com/uber/hermetic_cc_toolchain); see
`.bazelrc`). It is off by default on purpose, so the failure above stays visible
for this lab. The same config is what lets attendees with no compiler build the
apt layers at all (main [README](../../README.md#no-c-compiler)).

Two targets can never run remotely, by design: `//tools:render_graph` and
`//tools:local_registry` shell out to the host.

### Two config switches that look like a hang

Buildfarm needs both of these, and `tools/rbe/config/config.yml` sets both:

| Setting | If missing |
|---|---|
| `backplane.queues[].allowUnmatched` | the server refuses to enqueue the action |
| `worker.dequeueMatchSettings.allowUnmatched` | it queues fine and then **sits forever** |

The second failure shows up as `[Sched] … 41s` climbing with no worker activity.
It reads like a dead scheduler; it is a platform mismatch.

Also: Buildfarm takes its config from the **`CONFIG_PATH` environment variable**.
Pass a path as a positional argument and it is ignored silently — the process
falls back to its bundled example config, which points Redis at `localhost`, and
you get what looks like a Redis outage.

---

## 5 · Pointing at a hosted service instead

Everything above works against any REAPI provider — BuildBuddy, EngFlow,
Buildbarn, NativeLink. Put the endpoint and key in `.bazelrc.user` (gitignored,
already `try-import`ed):

```bash
echo 'build --remote_header=x-buildbuddy-api-key=YOUR_KEY' >> .bazelrc.user
bazel build --config=remote-cache //samples/...
```

`.bazelrc` keeps `remote-cache` / `bwb` / `rbe` pointed at BuildBuddy's hosted
tier for exactly this. The hosted configs are **not** covered by CI; the local
ones are.

> One that will *not* work: NativeLink's single-container image is distroless
> (Nix + musl, no shell). Actions here need `/bin/bash` — py_binary launchers,
> `container_structure_test`'s generated launcher, `rules_distroless`' genrules —
> so its bundled worker cannot run this repo. Worth knowing before you spend an
> evening on it.

---

## Reading

- Bazel — [Remote caching](https://bazel.build/remote/caching) ·
  [Remote execution](https://bazel.build/remote/rbe) ·
  [Adapting rules for remote execution](https://bazel.build/remote/rules) ·
  [Build without the Bytes](https://blog.bazel.build/2023/10/06/bwob-in-bazel-7.html)
- [`--remote_download_outputs`](https://bazel.build/reference/command-line-reference#flag--remote_download_outputs)
- [Buildfarm](https://github.com/buildfarm/buildfarm) ·
  [bazel-remote](https://github.com/buchgr/bazel-remote) ·
  [crane](https://github.com/google/go-containerregistry/blob/main/cmd/crane/README.md)
- `rules_img` push strategies — [docs/push.md](https://github.com/bazel-contrib/rules_img/blob/main/docs/push.md)
