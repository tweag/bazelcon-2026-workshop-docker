# Building Without Bytes — 2-Hour Workshop Script

Full facilitator script for the BazelCon 2026 workshop **"Building Without
Bytes: High-Velocity Image Composition at Scale."** This is the source of truth
for what the workshop *says and does*; [`slides.md`](slides.md) is the projected
deck. The workshop ramps from first principles → layer optimization → registry
push, with a hands-on **Lab** in every module. Source outline:
[`../ref/draft.md`](../ref/draft.md) · Proposal: [`../PROPOSAL.md`](../PROPOSAL.md).

> Thesis: if you can model a conference talk as a build artifact, you can model
> your whole software supply chain as one — and these slides prove it (built by
> the same `bazel build` as the images they describe).

**Format:** ~120 min, 6 modules, each = short concept + a Lab. Attendees clone
the repo and run real targets.

**Run sheet**

| # | Module | Time | Lab |
|---|--------|------|-----|
| 0 | Why: correct & hermetic | 15m | clone + `bazel build //...` |
| 1 | Basics: a first declarative image | 20m | build/run image vs Dockerfile |
| 2 | Hermeticity in practice | 20m | the "docker tax" benchmark |
| 3 | Layer optimization | 30m | layer split, dedup, distroless |
| 4 | Push operations | 20m | push to a local registry |
| 5 | rules_img & shipping choices | 15m | wrap-up + Q&A |

---

# Module 0 — Why: correct & hermetic (15m)

**Bazel's mantra [Q1].** "Bazel's pitch is **{Fast, Correct} — choose two**.
*Correct* means **hermetic**: a build with no external influence, so identical
inputs always produce identical outputs. Reproducibility isn't a feature bolted
on — it's the whole point. Everything in this workshop is a consequence of
taking that seriously for container images."

**Two kinds of hermeticity [Q2].** "Where does Docker fit? Docker gives you
**runtime / deploy hermeticity** — it bundles your dependencies so the artifact
runs the same everywhere. But the `docker build` *itself* is **not** hermetic:
`RUN apt-get install …` reaches out to the network, bakes in timestamps, and is
order-sensitive. So Docker hermetizes the **deploy** boundary; Bazel hermetizes
the **build**. The win is having both — a reproducible build that emits a
self-contained runtime."

**The "black box" Dockerfile.** Imperative script → non-deterministic
(`apt-get` today ≠ tomorrow), coarse cache invalidation (one early edit busts
everything below), and a privileged daemon dependency (`/var/run/docker.sock`:
security surface + CI bottleneck).

> **Lab 0 (5m):** `git clone … && bazel build //...`. Then note: these very
> slides are a build target — `bazel build //slides:build`. The deck is an
> artifact of the same graph as the images. CI even enforces it
> (`bazel query 'somepath(//slides, //samples/...)'` must be non-empty).

---

# Module 1 — Basics: a first declarative image (20m)

**Imperative → declarative.** "In Bazel we stop *running* commands to create
layers and instead **assemble** them from pre-built, content-addressed
artifacts. The filesystem becomes pure data; every input is tracked."

**The payload + the honest hard case.** "Our app uses the `graphviz` Python
package, which shells out to the `dot` **system binary** — an apt dependency,
not a pip wheel. That's the dependency we'll have to make *explicit* once we
leave the daemon. The app renders the workshop's own supply-chain graph."

**On screen:** [`../samples/python/Dockerfile`](../samples/python/Dockerfile)
(the before) and the `oci_image` from
[`../samples/python/BUILD.bazel`](../samples/python/BUILD.bazel) (the after).

> **Lab 1 (8m):**
> `bazel run //samples/python:image_load && docker run --rm bwb/python-graphviz`
> → prints DOT, reports `dot not found` (bare base has no `dot`).
> `docker build -t before samples/python && docker run --rm before`
> → `apt-get install`ed graphviz renders the PNG. **That contrast is the
> workshop:** the system dep is hidden in a `RUN` vs. forced into an explicit
> layer. (We make it *hermetic* in Module 3.)

---

# Module 2 — Hermeticity in practice (20m)

**Is Docker a good hermeticity validator? [Q3]** "Sort of — as a **negative
test**. Run a script in a pinned base with `--network=none` and it *fails* if it
secretly needs host tools or the network. That flushes out undeclared
dependencies. But it's **not a proof**: build-time network, timestamps, and
ordering still sneak in. Bazel's sandbox is the stronger validator — it only
exposes *declared* inputs, so a missing dependency fails at build time, every
time."

**The "docker tax" [Q6].** "People reach for Docker to *get* hermeticity —
'just put it in a container.' What does that cost per iteration? Same test
suite, two ways: `py_test` under Bazel (sandboxed, cached, parallel,
incremental) vs. a `docker build` that pip-installs and runs pytest. Change one
line and re-run."

- Bazel: re-runs only the affected test — **seconds**.
- Docker: invalidates at `COPY`, reinstalls, re-runs — **minutes**.

"The numbers are machine-dependent, so we *measure* them live rather than quote
them. The point is the **order of magnitude** per edit."

> **Lab 2 (8m):** `bazel run //benchmark/pytest_tax:compare` → prints the
> Bazel-vs-Docker timings (cold + warm, after a one-line change). Optional:
> `docker run --network=none --rm before` to watch a hidden-dep failure.

---

# Module 3 — Layer optimization (30m)

**Architect by volatility.** Order layers least → most volatile so rebuilds stay
cheap: **1. Base OS** (static) · **2. runtimes/deps** (infrequent) · **3. app
code** (constant). Bazel re-assembles only the changed layer.

**Action deduplication [Q5].** "Bazel's action cache keys every action on
**input digests + command + environment**. Identical action → built once,
reused. Because layers are **content-addressed**, a shared base/deps layer is
built once and reused across *every* image that references it — and later, at
the registry, an existing blob is skipped on push. Optimization = arrange your
layers so the common ones are **byte-identical**, and dedup does the rest."

**rules_distroless: hermetic system deps [Q4].** "Remember the `dot` gap?
Here's the fix. Instead of `RUN apt-get install graphviz`, we declare the
package in a manifest and pin it in a lockfile with `apt.install()`. Bazel
materializes `dot` + its transitive `.deb`s as **content-addressed, reproducible
layers** — no network at build, no daemon, no `RUN`. Bonus: distroless images
have **no shell and no package manager**, so they're smaller and have a far
smaller attack surface."

**On screen:** the layer split in
[`../samples/python/BUILD.bazel`](../samples/python/BUILD.bazel) and the
manifest + `oci_image` in
[`../samples/distroless/`](../samples/distroless/).

> **Lab 3 (12m):**
> 1. Edit one line in `app.py`, rebuild → only the app layer rebuilds (watch the
>    cache hits).
> 2. `bazel run //samples/distroless:image_load && docker run --rm bwb/distroless`
>    → runs `dot` (graphviz 2.43) from a **fully hermetic, pinned layer** built
>    on scratch — no daemon, no `RUN apt-get`. (Wiring the plugin `config6` so
>    it also *renders* is the documented follow-up in the sample.)
> 3. Build two images sharing the base layer → it's built once.

---

# Module 4 — Push operations (20m)

**Daemonless push.** "`rules_oci` gives `oci_push`; `rules_img` gives
`image_push`. Neither needs the Docker daemon. Both push **only the blobs the
registry doesn't already have** — the content-addressed dedup from Module 3 now
pays off as **bandwidth**: a base/deps layer shared across images uploads once."

**Multi-arch.** Push an image *index* (`linux/amd64` + `linux/arm64/v8`) built
without QEMU-in-Docker.

> **Lab 4 (10m):**
> 1. `bazel run //tools:local_registry` → starts `registry:2` on `localhost:5000`.
> 2. `bazel run //samples/rules_oci:push` and `//samples/rules_img:push`.
> 3. Push a second image that shares the base layer → watch the shared blob
>    report as already present (skipped).

---

# Module 5 — rules_img & shipping choices (15m)

**rules_oci → rules_img.** `rules_oci` is the standard (packages layers with
`tar`). `rules_img` is the next step: skips expensive `tar`/compression on every
build, uses a Go-based incremental loader/pusher, and treats layers as
transparent blobs until final assembly.

| Feature | Dockerfile | rules_oci | rules_img |
|---|---|---|---|
| Execution | Imperative | Declarative | Optimized declarative |
| Hermetic | No | Yes | Yes |
| Speed | Slow (cache miss) | Fast | Ultra-fast |
| Daemon req. | Yes | No | No |
| Tar-less | No | No | Yes |

**Ship as Docker vs. source-only? [Q7]** "A Docker image is self-contained,
immutable, content-addressed, scannable, and rollback-able — it carries
**deploy hermeticity**. Shipping source is smaller to transfer but pushes
non-hermeticity onto the consumer's build (they need the right toolchain and
deps — 'works on my machine' returns). The nice part: with Bazel you emit
**both from one graph** and choose per audience."

**The dogfooding loop.** The Python sample renders *this repo's own dependency
graph* with `dot`, and the deck imports the result — a build action drawing the
graph of the build that produced the slide.

**Takeaways.** Stop scripting, start mapping · architect for layers · go
daemonless · evaluate `rules_img` · Slide-as-Code. **Mental model:** layers are
granular, deterministic, cacheable build outputs — not opaque blobs.

**Q&A.** Multi-stage builds → layers/intermediate targets · secrets → never in a
cacheable layer; inject at runtime · legacy migration → base+deps split first,
tighten hermeticity incrementally · cross-arch → multi-platform indexes, no QEMU.

---

## Appendix — running everything

```bash
bazel build //...                         # images, slides, tools
bazel test  //...                         # unit + structure + invariant tests
bazel run //samples/python:image_load     # OCI image (no dot) -> Docker
bazel run //samples/distroless:image_load # hermetic, pinned `dot` (scratch)
bazel run //samples/rules_img:load        # rules_img image -> Docker
bazel run //benchmark/pytest_tax:compare  # the "docker tax" delta
bazel run //tools:local_registry          # registry:2 on localhost:5000
bazel run //samples/rules_oci:push        # push (only changed blobs)
bazel run //tools:render_graph -- //...    # draw the dependency graph
bazel run //slides:present                # live preview
bazel run //slides:export_pdf             # -> docs/building-without-bytes.pdf
```
