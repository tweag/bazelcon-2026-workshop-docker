# Building Without Bytes — Presentation Content

Written content and speaker notes for the BazelCon 2026 workshop **"Building
Without Bytes: High-Velocity Image Composition at Scale."** This is the source
of truth for what the talk *says*; [`slides.md`](slides.md) is the Slidev deck
that shows the highlights. Sections marked **[slide]** have a corresponding
slide in the current deck; the rest are workshop narrative (and a roadmap for
deepening the deck). Source outline: [`../ref/draft.md`](../ref/draft.md).

> Thesis: if you can model a conference talk as a build artifact, you can
> model your whole software supply chain as one. (See [`../PROPOSAL.md`](../PROPOSAL.md).)

**Workshop goals**
- Transition from **imperative** (scripts) to **declarative** (data) image builds.
- Achieve **sub-minute iterations** even for multi-gigabyte images.
- Eliminate the dependency on the **Docker daemon** and root privileges.
- Understand the evolution from `rules_oci` to `rules_img`.

---

## 1. Cover — "This deck is a build artifact" **[slide]**

**Say:** "Before we start — a confession. These slides weren't exported from
Keynote or PowerPoint. They were *built* by Bazel, by the same workspace that
builds the container images we're about to discuss. Same `bazel build`. Same
cache. The code you'll see on these slides is imported live from the repo's
real source files — not copy-pasted."

**Why it matters:** it sets up the dogfooding frame. Everything that follows
is demonstrated on the very artifact in front of the audience.

---

## 2. The dogfooding thesis (statement slide) **[slide]**

**Say:** "`bazel build //slides:build` produces this deck.
`bazel build //samples/python:image` produces the image we'll discuss. Same
graph, same cache, same guarantees. So the claim of this talk is simple: if a
presentation — something we think of as creative and fluid — can be a
deterministic build artifact, then so can every container image in your
supply chain."

**Speaker note:** CI even enforces it —
`bazel query 'somepath(//slides, //samples/...)'` must be non-empty, so a
broken sample literally breaks the deck.

---

## 3. The problem: the "black box" build

**Say:** "Let's name the pain first. A standard Dockerfile is an *imperative
script* — a sequence of `RUN apt-get install …` commands. Three things hurt:"

- **Non-deterministic** — `apt-get` today ≠ `apt-get` tomorrow. The same
  Dockerfile produces different images on different days.
- **Coarse cache invalidation** — change one early line and every layer below
  it rebuilds, including the expensive dependency installs.
- **The Docker socket dependency** — builds need `/var/run/docker.sock`, which
  means a privileged daemon: a security surface and a CI bottleneck.

**Frame:** "Bazel's answer is to stop *running* commands to create layers and
instead **assemble** layers from pre-built, content-addressed artifacts. The
filesystem becomes pure data."

---

## 4. Pillar 1 — From imperative to declarative **[slide]**

**Say:** "Here's how we package a Python app that needs the `dot` system
binary today. We `RUN apt-get install graphviz`. It works — but that layer is
an opaque blob produced by a stateful daemon, and editing `app.py` busts every
layer below the `COPY`, including the dependency install."

**On screen (the before):** transcluded from the real
[`../samples/python/Dockerfile`](../samples/python/Dockerfile).

**Contrast (the after):** "In Bazel we don't `RUN` — we declare what goes
where. Every input is tracked and content-addressed (hermeticity)."

```python
oci_image(
    name = "image",
    base = "@python_base",
    tars = [":deps_layer", ":app_layer"],  # assembled, not executed
    entrypoint = ["/app/app"],
)
```

**Key terms:** opaque layer, daemon-built, coarse invalidation vs. declarative,
content-addressed, hermetic.

---

## 5. The payload: a non-hermetic system dependency **[slide]**

**Say:** "Our sample is deliberately honest about the hard case. The
`graphviz` Python package is a thin wrapper that shells out to the `dot`
binary — an apt dependency, not a pip wheel. That's the dependency we have to
make *explicit* once we leave the daemon behind. The app renders the
workshop's own supply-chain graph."

**On screen:** the `build_graph` function, transcluded via a `#region` marker
from [`../samples/python/app.py`](../samples/python/app.py).

**Demo beat:** run the OCI image (`bazel run //samples/python:image_load`) — it
prints the DOT source and reports `dot not found`, because the bare base has no
`dot`. The Dockerfile baseline, which apt-installed graphviz, renders the full
PNG. **That contrast *is* the talk:** rules_oci forces the system dependency to
become an explicit, declared layer instead of a hidden `RUN`.

---

## 6. Pillar 2 — High-velocity incrementalism

**Say:** "Build without the bytes: only re-compute what changed. The trick is
architecting layers by volatility."

**Layer strategy (least → most volatile):**
1. **Base OS** — static, essentially never changes.
2. **Runtimes / dependencies** — change infrequently.
3. **Application code** — changes constantly.

"Bazel re-assembles only the changed layer and only uploads that blob to the
registry."

### From `rules_oci` to `rules_img`

- **`rules_oci`** — the industry standard; packages layers with `tar`.
- **`rules_img`** — the next step:
  - avoids expensive `tar` (+ compression) steps on every build,
  - high-performance, Go-based incremental loader/pusher,
  - treats layers as transparent blobs until final assembly.

**On screen / aside:** we ship the *same* image two ways —
[`//samples/rules_oci`](../samples/rules_oci/BUILD.bazel) and
[`//samples/rules_img`](../samples/rules_img/BUILD.bazel) — from the **same**
`//samples/python:app_layer`, so only the ruleset changes.

**Demo beat — the 1-second rebuild:** with a large (e.g. ~1.5 GB) app image,
change a single string in the app and rebuild. Docker invalidates at
`COPY . /app` and re-runs everything (2–3 min). Bazel re-assembles only the
application-layer blob — done in seconds — because the action graph proved
nothing else changed.

> _Repo status: the 1-second-rebuild benchmark is TASK §2.6 / §4 — still to be
> built. Today the layer split is a single runfiles layer; the volatility-tiered
> split (system / deps / app) is the planned refinement (TASK §2.9)._

---

## 7. Pillar 3 — Daemonless & secure, and verification

**Say:** "Dropping the daemon isn't just speed — it's security and portability."

**Breaking the socket dependency** — no `/var/run/docker.sock`. You can build:
- on restricted CI runners with no root,
- on macOS / Windows without a Linux VM,
- side-by-side with every other Bazel action, cached and remote-executable.

**Verification without running the container** — `container_structure_test`
validates file existence, content, and metadata inside the Bazel sandbox,
without ever starting the container:

```python
container_structure_test(
    name = "structure_test",
    image = ":image",
    configs = ["test_config.yaml"],
)
```

> _Repo status: container structure tests are TASK §2.5 — pending. Today we have
> `build_test` (the image assembles), `app_test` (the payload), and the CI
> reproducibility + dogfooding-invariant checks._

---

## 8. The dogfooding loop (two-column) **[slide]**

**Say:** "And here's the loop closing on itself. The Python sample renders
*this repo's own dependency graph* using `dot`. A Bazel action — which needs
an apt-installed binary packaged as a layer — draws the graph of the build
that produced this slide. The image on the right was generated by
`bazel run //tools:render_graph -- //samples/python:image`."

**Speaker note:** if doing it live, run
`bazel run //tools:render_graph -- //tools:render_graph` so the rendered
graph literally contains its own node.

---

## 9. Comparing the tooling

| Feature        | Dockerfile          | rules_oci      | rules_img            |
|----------------|---------------------|----------------|----------------------|
| **Execution**  | Imperative          | Declarative    | Optimized declarative|
| **Hermetic**   | No                  | Yes            | Yes                  |
| **Speed**      | Slow (cache misses) | Fast           | Ultra-fast           |
| **Daemon req.**| Yes                 | No             | No                   |
| **Tar-less**   | No                  | No             | Yes                  |

**Say:** "Same artifact, three philosophies. The further right you go, the more
the build behaves like the rest of your Bazel graph: deterministic, cacheable,
daemonless."

---

## 10. Takeaways **[slide]**

1. **Stop scripting, start mapping** — use `rules_pkg` / layer rules to declare
   *what goes where*, not *what to run*.
2. **Architect for layers** — keep heavy dependencies separate from volatile
   application code so rebuilds stay cheap.
3. **Go daemonless** — better CI security and portability; no root, no socket.
4. **Evaluate `rules_img`** — if `tar`/compression is your bottleneck, upgrade.
5. **Slide-as-Code** — clone this repo's structure; the deck is just another
   build target, and the benchmark lets you measure the wins on your own images.

**Mental model:** container layers are granular, deterministic, cacheable build
outputs — not opaque blobs.

**Close:** "Once layers are just artifacts, the daemon stops being special —
and your container builds inherit every guarantee Bazel already gives the rest
of your code."

---

## 11. Q&A — anticipated

- **Multi-stage builds?** — map each stage to layers / intermediate targets;
  the "builder" stage becomes ordinary build actions.
- **Secret injection?** — keep secrets out of layers; inject at runtime or via
  the registry/orchestrator, never baked into a content-addressed blob.
- **Migrating legacy repositories?** — start with the base + deps split, wrap
  the existing app as one layer, then tighten hermeticity incrementally.
- **Cross-arch?** — multi-platform indexes (`linux/amd64`, `linux/arm64/v8`)
  built without QEMU-in-Docker; see the digest-pinned base in `MODULE.bazel`.

---

## Appendix — running everything

```bash
bazel build //...                      # images, slides, tools
bazel test  //...                      # unit + structure + invariant tests
bazel run //samples/python:image_load  # OCI image -> Docker
bazel run //samples/rules_img:load     # rules_img image -> Docker
bazel run //tools:render_graph -- //...# draw the dependency graph
bazel run //slides:present             # live preview
bazel run //slides:export_pdf          # -> docs/building-without-bytes.pdf
```
