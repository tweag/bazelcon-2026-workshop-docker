# Building Without Bytes — 90-Minute Workshop Script

Full facilitator script for the BazelCon 2026 workshop **"Building Without
Bytes: High-Velocity Image Composition at Scale."**
**9:00–10:30 · Instructor: Rafael Lima · Sponsored by Tweag by Modus Create.**

This is the source of truth for what the workshop *says and does*;
[`slides.md`](slides.md) is the projected deck. The workshop ramps from first
principles → layer optimization → registry push, with a hands-on **Lab** in
every module. Source outline: [`../ref/draft.md`](../ref/draft.md) · Proposal:
[`../PROPOSAL.md`](../PROPOSAL.md).

> **Abstract.** In modern CI/CD the traditional `docker build` is often the
> slowest link: imperative, sequential Dockerfiles struggle with cache
> invalidation and lack the fine-grained dependency tracking large monorepos
> need. This workshop takes a **graph-based** approach — with Bazel,
> `rules_oci`, and `rules_img` we treat container layers as pure, declarative
> artifacts, assembling images in seconds, independent of a local Docker
> daemon. Attendees move from legacy "black box" builds to a transparent,
> content-addressable architecture so that **what you build in CI is
> byte-for-byte identical to what runs in production**.

**Format:** ~90 min, 6 modules, each = short concept + a Lab. Attendees clone
the repo and run real targets.

**Run sheet**

| # | Module | Time | Lab |
|---|--------|------|-----|
| 0 | Why: correct & hermetic | 10m | clone + `bazel build //...` |
| 1 | Basics: a first declarative image | 15m | build/run image vs Dockerfile |
| 2 | Hermeticity in practice | 15m | the "docker tax" benchmark |
| 3 | Layer optimization | 25m | layer split, dedup, distroless |
| 4 | Push operations | 15m | push to a local registry |
| 5 | rules_img & shipping choices | 10m | wrap-up + Q&A |

---

# Module 0 — Why: correct & hermetic (10m)

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

# Module 1 — Basics: a first declarative image (15m)

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

# Module 2 — Hermeticity in practice (15m)

**Validate images without the daemon [Q3].** "How do you check an image is
correct without a runtime? `container_structure_test` with `driver = "tar"`
inspects the image's **files and config directly in the Bazel sandbox** — no
daemon. We assert the launcher + runfiles exist and the entrypoint metadata
(`fileExistenceTests` + `metadataTest`; no `commandTests`, which would need
execution). It runs in CI alongside every other test — see
`//samples/python:image_structure_test`."

**A quick negative test (aside).** "For a *script's* hermeticity,
`docker run --network=none` surfaces undeclared host deps — handy, but not a
proof. Bazel's sandbox is the rigorous validator: only *declared* inputs are
visible, so a missing dependency fails at build time, every time."

**The "docker tax" [Q6].** "People reach for Docker to *get* hermeticity —
'just put it in a container.' What does that cost per iteration? Same test
suite, two ways: `py_test` under Bazel (sandboxed, cached, parallel,
incremental) vs. a `docker build` that pip-installs and runs pytest. Change one
line and re-run."

- Bazel: re-runs only the affected test — **seconds**.
- Docker: invalidates at `COPY`, reinstalls, re-runs — **minutes**.

"The numbers are machine-dependent, so we *measure* them live rather than quote
them. The point is the **order of magnitude** per edit."

> **Lab 2 (8m):** `bazel test //samples/python:image_structure_test`
> (daemonless validation), then `bazel run //benchmark/pytest_tax:compare`
> → the Bazel-vs-Docker timings (cold + warm, after a one-line change).

---

# Module 3 — Layer optimization (25m)

**Architect by volatility.** Order layers least → most volatile so rebuilds stay
cheap: **1. Base OS** (static) · **2. runtimes/deps** (infrequent) · **3. app
code** (most volatile). Bazel re-assembles only the changed layer.

**Action deduplication [Q5].** "Bazel's action cache keys every action on
**input digests + command + environment**. Identical action → built once,
reused. Because layers are **content-addressed**, a shared base/deps layer is
built once and reused across *every* image that references it — and later, at
the registry, an existing blob is skipped on push. Optimization = arrange your
layers so the common ones are **byte-identical**, and dedup does the rest."

**How to build a layer, and what's shared [Q4/Q5].** "Build a layer with
`pkg_tar`, `image_layer`, or `layer_from_tar`. What can be shared? The **base
OS** and any **byte-identical** layer (deps, config). Concretely:
`//samples/shared_layers` builds `image_a` and `image_b` on the same base + a
common layer — `bazel run //samples/shared_layers:digests` prints the shared
blob digests (the base layers + the common layer are shared; each image adds one
unique app layer)."

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
> 3. `bazel run //samples/shared_layers:digests` → two images, shared base +
>    common layer; the diff prints the shared blob digests (built once).

---

# Module 4 — Push operations (15m)

**Daemonless push.** "`rules_oci` gives `oci_push`; `rules_img` gives
`image_push`. Neither needs the Docker daemon. Both push **only the blobs the
registry doesn't already have** — the content-addressed dedup from Module 3 now
pays off as **bandwidth**: a base/deps layer shared across images uploads once."

**Multi-arch.** The base is pulled multi-arch (`linux/amd64` + `linux/arm64/v8`);
building an image *index* to push both is a one-liner — no QEMU-in-Docker.

> **Lab 4 (10m):**
> 1. `bazel run //tools:local_registry` → starts `registry:2` on `localhost:5000`.
> 2. `bazel run //samples/rules_oci:push`, then `//samples/rules_img:push`.
>    They share the base + `app_layer`, so the **second push reports those blobs
>    as already present** — registry dedup is by content digest, even across
>    repositories. (Observed: "N from container registry" / "existing blob".)

---

# Module 5 — rules_img & shipping choices (10m)

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

**(If asked) ship as Docker vs. source-only? [Q7]** A Docker image is
self-contained, immutable, scannable — it carries **deploy hermeticity**;
shipping source pushes non-hermeticity onto the consumer's build. With Bazel
you emit **both from one graph**. _(Cut from the deck to protect the 90-min
budget — keep as a backup answer.)_

**One last loop (closer).** The Python sample renders *this repo's own
dependency graph* with `dot`, and the deck imports the result — a build action
drawing the graph of the build that produced this very slide.

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
