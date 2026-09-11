# Lab R — remote cache, remote execution, and "without the bytes"

Module 4 of the deck talks about a shared cache and RBE. This lab runs both **on
your machine**, with no account, no API key, and — for the cache and the
registry — no Docker either. The services are ordinary Bazel targets:

```bash
bazel run //tools:local_cache       # REAPI cache      -> localhost:9092
bazel run //tools:local_registry    # OCI registry     -> localhost:5000
bazel run //tools:local_rbe         # remote execution -> localhost:8980 (needs Docker)
```

Each one takes `-- stop`. The cache also takes `-- purge` (deletes the store, so
your next build is genuinely cold).

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
INFO: 378 processes: 258 remote cache hit, 120 internal.
```

A `bazel clean` threw away every local output and the build still did almost no
work. That is the "shared pantry" slide, for real — and on a team, those 258 hits
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
| normal build | **258 MB** |
| `--config=local-bwb` | **177 KB** |

Same build, same graph, same result — 1500× less local I/O. For container images
this is the whole game: an image is a set of blobs, and the machine that
*assembles* it rarely needs to hold them.

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

The deck says `strategy = "lazy"` needs remote execution. It doesn't — it needs a
remote **cache**, which is a much lower bar. Point `img` at the local one:

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
runfiles: `push_eager` carries 4 layer blob entries, `push_lazy` carries a
`layer_hints` file instead.

---

## 4 · Remote execution (advanced)

```bash
bazel run //tools:local_rbe                          # Buildfarm + Redis, 3 containers
bazel build --config=local-rbe //samples/python:image
bazel test  --config=local-rbe //samples/python/... //labs/playground/...
```

**What works.** Everything that isn't downstream of an apt layer — 11 of 11 tests
green, including both daemonless `container_structure_test`s:

```
338 processes: 65 remote, 4 local, 271 internal, 4 action cache hit
Executed 7 out of 11 tests: 11 tests pass.
```

**What doesn't, and why it's the point.** `bazel test --config=local-rbe //...`
fails:

```
Compiling support/malloc/dynarray_emplace_enlarge.c [for tool] failed:
absolute path inclusion(s) found in rule '@@gawk+//:support':
  '/usr/lib/gcc/x86_64-linux-gnu/13/include/stdbool.h'
  '/usr/lib/gcc/x86_64-linux-gnu/13/include/stddef.h'
```

Bazel's auto-detected C++ toolchain hardcodes **your machine's** GCC 13 headers by
absolute path. Locally that is invisible, because those files are right there.
On a worker they do not exist. `gawk` is a build tool for `rules_distroless`'
genrule, so this takes out every apt-layer target: `//samples/distroless`,
`//labs/level2_ghost`, `//labs/level3_hardware`.

Nothing is broken. Remote execution simply *reported* a non-hermeticity your
laptop had been quietly covering for — which is the single best argument for
adopting it. The fix is to register a hermetic C++ toolchain (e.g.
[`toolchains_llvm`](https://github.com/bazel-contrib/toolchains_llvm)) instead of
letting Bazel autodetect the host compiler. That is a real dependency decision,
so this repo leaves it undone on purpose and leaves the failure visible.

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
