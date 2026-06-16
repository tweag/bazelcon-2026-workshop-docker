---
theme: default
title: Building Without Bytes
info: |
  ## Building Without Bytes — 90-min workshop (9:00–10:30)
  High-Velocity Image Composition at Scale — BazelCon 2026 · Rafael Lima.
  Sponsored by Tweag by Modus Create.

  A graph-based approach to containerization: with Bazel, rules_oci, and
  rules_img we treat container layers as pure, declarative artifacts —
  assembling images in seconds, independent of a local Docker daemon, so what
  you build in CI is byte-for-byte identical to what runs in production.

  These slides are built by the same Bazel workspace that builds the images
  they describe; code on screen is imported live. Script: slides/content.md.
class: text-center bazel-cover
transition: slide-left
mdc: true
---

<div class="bazel-blocks"><i></i><i></i><i></i><i></i></div>

# Building Without Bytes

### High-Velocity Image Composition at Scale

<div class="opacity-70 mt-6">

These slides were not exported from an app — they were **built by Bazel**,
from the same workspace that builds the containers they describe.

</div>

<div class="opacity-80 mt-6 text-sm">Sponsored by <strong>Tweag by Modus Create</strong></div>

<div class="abs-br m-6 opacity-50 text-sm">BazelCon 2026 · 9:00–10:30 · Rafael Lima</div>

---
layout: statement
---

# This slide is a build artifact

`bazel build //slides:build` → this deck.<br>
`bazel build //samples/python:image` → the image we'll discuss.

Same graph. Same cache. Same guarantees.

What you build is byte-for-byte what runs in production —<br>starting with the deck you're watching.

---
layout: section
---

# Module 0 · Why: correct & hermetic
<div class="opacity-60">10 min · Lab: clone + `bazel build //...`</div>

---

# Bazel's promise: {Fast, Correct}

**Correct** means **hermetic** — a build with *no external influence*, so
identical inputs always produce identical outputs.

<div class="mt-4">

Reproducibility isn't bolted on; it's the whole point. Everything in this
workshop is a consequence of taking that seriously for **container images**.

</div>

---

# Two kinds of hermeticity

<div class="grid grid-cols-2 gap-6 mt-4">
<div>

### Docker
**Runtime / deploy** hermeticity.<br>
Bundles deps so the artifact runs the same everywhere.<br>
But `docker build` itself is **not** hermetic — `RUN apt-get` is networked,
timestamped, order-sensitive.

</div>
<div>

### Bazel
**Build** hermeticity.<br>
Only declared inputs are visible; identical inputs → identical outputs.<br>
Emits a reproducible, content-addressed artifact.

</div>
</div>

<div class="mt-6 text-center opacity-80">

Docker hermetizes the **deploy** boundary; Bazel the **build**. Want both.

</div>

---

# The "black box" build

Standard Dockerfiles are imperative scripts — and that hurts three ways:

- **Non-deterministic** — `apt-get` today ≠ `apt-get` tomorrow.
- **Coarse cache invalidation** — one early edit busts every layer below.
- **The Docker socket** — a privileged daemon: security surface + CI bottleneck.

<div class="mt-6 opacity-80">

Bazel's answer: stop **running** commands to make layers — **assemble** them
from pre-built, content-addressed artifacts. The filesystem becomes data.

</div>

---
layout: section
---

# Module 1 · A first declarative image
<div class="opacity-60">15 min · Lab: build/run the image vs the Dockerfile</div>

---

# The "before": an imperative Dockerfile

The Docker daemon installs the `dot` system dependency with `RUN apt-get` —
an opaque, stateful layer. Editing `app.py` busts everything below the `COPY`.

<<< ../samples/python/Dockerfile docker {14-28}

---

# The payload: Python + a *non-hermetic* system dep

`graphviz` shells out to the `dot` binary — the apt dependency we must make
explicit once we leave the daemon. The app renders the workshop's own graph:

<<< ../samples/python/app.py#build_graph python {*}{maxHeight:'360px'}

---

# The "after": layers as declarative build outputs

No daemon. The image is composed from content-addressed layers in the action
graph; changing `app.py` reuses the base + deps layers untouched.

<<< ../samples/python/BUILD.bazel#oci python {*}{maxHeight:'360px'}

---
layout: section
---

# Module 2 · Hermeticity in practice
<div class="opacity-60">15 min · Lab: the "docker tax" benchmark</div>

---

# Is Docker a good hermeticity validator?

As a **negative test** — yes:

```bash
docker run --network=none --rm myscript   # fails if it needs the host/network
```

A pinned base with no network *surfaces undeclared dependencies*. But it's
**not a proof** — build-time network, timestamps, and ordering still sneak in.

<div class="mt-4">

Bazel's **sandbox** is the stronger validator: it exposes only *declared*
inputs, so a missing dependency fails the build — every time.

</div>

---

# The "docker tax"

Same suite, two ways — `py_test` (sandboxed, cached, incremental) vs. a
`docker build` that pip-installs and runs pytest. Change one line, re-run:

```bash
bazel run //benchmark/pytest_tax:compare
#   bazel test  (warm, after edit)    ~0.8 s
#   docker build (warm, after edit)   ~2.2 s   ← per-edit "tax"
#   docker build (cold, --no-cache)  ~11   s   ← upfront "make it hermetic" cost
```

Absolute numbers are machine-dependent; the **ratio per edit** is the point —
and it grows with image size and dependency count.

---
layout: section
---

# Module 3 · Layer optimization
<div class="opacity-60">25 min · Lab: layer split · dedup · distroless</div>

---

# Architect layers by volatility

Order layers least → most volatile so rebuilds stay cheap:

1. **Base OS** — static &nbsp;·&nbsp; 2. **Runtimes / deps** — infrequent &nbsp;·&nbsp; 3. **App code** — constant

Change one string in a multi-GB app:

```bash
$ docker build -t app .              # invalidates at COPY . /app → 2–3 min
$ bazel run //samples/rules_img:load # re-assembles one blob   → seconds
```

Bazel re-assembles only the changed layer — and uploads only that blob.

---

# Action deduplication

Bazel's action cache keys every action on **input digests + command + env** →
identical action, built **once**.

<div class="mt-4">

Layers are **content-addressed**, so the win compounds:

- a shared base/deps layer is **built once**, reused across *every* image;
- at the registry, an existing blob is **skipped on push**.

</div>

<div class="mt-4 opacity-80">

Optimization = make common layers **byte-identical**, and dedup does the rest.

</div>

---

# rules_distroless: hermetic system deps

Remember the `dot` gap? Replace `RUN apt-get install graphviz` with a **pinned
manifest + lockfile** — Bazel materializes `dot` + its `.deb`s as
content-addressed layers. No network at build, no daemon, no `RUN`.

```python
# MODULE.bazel
apt = use_extension("@rules_distroless//apt:extensions.bzl", "apt")
apt.install(name = "graphviz_apt",
            manifest = "//samples/distroless:graphviz.yaml",
            lock = "//samples/distroless:graphviz.lock.json")
```

Bonus: **no shell, no package manager** → smaller image, smaller attack surface.

---
layout: section
---

# Module 4 · Push operations
<div class="opacity-60">15 min · Lab: push to a local registry</div>

---

# Daemonless push — only the changed blobs

`rules_oci` → `oci_push`; `rules_img` → `image_push`. No daemon. Both upload
**only blobs the registry lacks** — the dedup from Module 3 now pays off as
**bandwidth**: a shared base layer uploads once.

```bash
bazel run //tools:local_registry          # registry:2 on localhost:5000
bazel run //samples/rules_oci:push         # push (changed blobs only)
bazel run //samples/rules_img:push         # same image, rules_img
```

Push a multi-arch **index** (`linux/amd64` + `linux/arm64/v8`) — no QEMU-in-Docker.

---
layout: section
---

# Module 5 · rules_img & shipping choices
<div class="opacity-60">10 min · wrap-up + Q&A</div>

---

# Same artifact, three philosophies

| Feature | Dockerfile | rules_oci | rules_img |
|---|---|---|---|
| **Execution** | Imperative | Declarative | Optimized declarative |
| **Hermetic** | No | Yes | Yes |
| **Speed** | Slow (cache miss) | Fast | Ultra-fast |
| **Daemon req.** | Yes | No | No |
| **Tar-less** | No | No | Yes |

`rules_img` skips `tar`/compression and uses a Go-based incremental loader —
layers stay transparent blobs until final assembly.

---

# Ship as Docker, or as source?

<div class="grid grid-cols-2 gap-6 mt-4">
<div>

### Docker image
Self-contained, immutable, content-addressed, scannable, rollback-able.<br>
Carries **deploy hermeticity**.

</div>
<div>

### Source only
Smaller to transfer — but pushes non-hermeticity onto the consumer's build
("works on my machine" returns).

</div>
</div>

<div class="mt-6 text-center opacity-80">

With Bazel you emit **both from one graph** — choose per audience.

</div>

---
layout: two-cols
layoutClass: gap-8
---

# The dogfooding loop

The Python sample renders **this repo's own dependency graph** with `dot`,
and the deck imports the result.

A Bazel action, needing an apt-installed binary packaged as a layer, draws
the graph of the build that produced the slide.

```bash
bazel run //tools:render_graph \
  -- //samples/python:image
```

::right::

<img src="./graphs/dogfooding.png"
     class="max-h-72 object-contain"
     alt="first-party dependency graph of //samples/python:image" />

---
layout: center
class: text-center
---

# Takeaways

**Stop scripting, start mapping** — declare *what goes where*, not what to run.<br>
**Architect for layers** — heavy deps apart from volatile code.<br>
**Go daemonless** — better CI security and portability.<br>
**Evaluate `rules_img`** — if `tar` is the bottleneck, upgrade.<br>
**Slide-as-Code** — the deck is just another build target.

<div class="mt-8 opacity-70">

Once layers are just artifacts, the daemon stops being special.

</div>
