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

# Correct means hermetic

Bazel's promise is **{Fast, Correct}** — and *correct* means **hermetic**: a
build with no external influence, so identical inputs → identical outputs.

<div class="grid grid-cols-2 gap-6 mt-5">
<div>

### Docker — *runtime* hermeticity
Bundles deps so the artifact runs the same everywhere. But `docker build`
itself isn't hermetic: `RUN apt-get` is networked, timestamped, order-sensitive.

</div>
<div>

### Bazel — *build* hermeticity
Only declared inputs are visible; identical inputs → identical,
content-addressed outputs.

</div>
</div>

<div class="mt-5 text-center opacity-80">

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

<<< ../samples/python/Dockerfile#dockerfile docker

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

# rules_oci, start to finish

1. **Pull a base** — `oci.pull` in `MODULE.bazel` (digest-pinned, multi-arch).
2. **Build a layer** — `pkg_tar` the app's runfiles (or any files).
3. **Assemble** — `oci_image(base, tars = [...], entrypoint = [...])`.
4. **Load / push** — `oci_load` → Docker · `oci_push` → registry.

```python
oci_image(name = "image", base = "@python_base",
          tars = [":app_layer"], entrypoint = ["/app/app"])
oci_load(name = "image_load", image = ":image", repo_tags = ["bwb/app:latest"])
oci_push(name = "push", image = ":image",
         repository = "localhost:5000/bwb/app", remote_tags = ["latest"])
```

---
layout: section
---

# Module 2 · Hermeticity in practice
<div class="opacity-60">15 min · Lab: the "docker tax" benchmark</div>

---

# Validate images without the daemon

`container_structure_test` with `driver = "tar"` checks the image's **files and
config in the Bazel sandbox** — no container runtime, no Docker daemon:

<<< ../samples/python/image_test.yaml yaml {*}{maxHeight:'210px'}

```python
container_structure_test(name = "image_structure_test",
    image = ":image.tar", configs = ["image_test.yaml"], driver = "tar")
```

<div class="mt-2 opacity-70 text-sm">

Aside — a quick *negative* test for scripts: `docker run --network=none …`
surfaces undeclared host deps (handy, but not a proof; the sandbox is).

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

1. **Base OS** — static &nbsp;·&nbsp; 2. **Runtimes / deps** — infrequent &nbsp;·&nbsp; 3. **App code** — most volatile

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
layout: two-cols-header
layoutClass: gap-6
---

# Shared layers: two images, one blob

Both images sit on the same base + `:common_layer`; only the app layer differs.

::left::

<<< ../samples/shared_layers/BUILD.bazel#shared python {*}{maxHeight:'250px'}

::right::

```bash
bazel run \
  //samples/shared_layers:digests
# SHARED (built & pushed once):
#  sha256:…  base layers
#  sha256:…  :common_layer
# + 1 unique app layer each
```

What can be shared? The **base OS** and any **byte-identical** layer (deps,
config). Content-addressing makes the dedup automatic.

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

The base is pulled **multi-arch** (`linux/amd64` + `linux/arm64/v8`); building an
image *index* to push both is a one-liner — no QEMU-in-Docker.

---
layout: section
---

# Module 5 · rules_img & shipping choices
<div class="opacity-60">10 min · wrap-up + Q&A</div>

---
layout: two-cols-header
layoutClass: gap-6
---

# Same image, two rulesets

Same `//samples/python:app_layer` — only the ruleset differs.

::left::

**`rules_oci`** — `oci_image`

<<< ../samples/rules_oci/BUILD.bazel#oci python {*}{maxHeight:'300px'}

::right::

**`rules_img`** — `image_manifest` + `layer_from_tar`

<<< ../samples/rules_img/BUILD.bazel#img python {*}{maxHeight:'300px'}

---

# rules_img, start to finish

1. **Pull a base** — `images.pull` (rules_img's own extension) in `MODULE.bazel`.
2. **Build a layer** — `layer_from_tar` (reuse a `pkg_tar`) or `image_layer`.
3. **Assemble** — `image_manifest(base, layers = [...], entrypoint = [...])`;
   `image_index` for multi-arch.
4. **Load / push** — `image_load` → Docker · `image_push` → registry.

Tar-less + a Go-based incremental loader — layers stay transparent blobs until
final assembly, so builds and pushes stay fast at scale.

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
layout: center
class: text-center
---

# Takeaways

**Stop scripting, start mapping** — declare *what goes where*, not what to run.<br>
**Build layers, share layers** — split by volatility; byte-identical layers dedupe.<br>
**Go daemonless** — validate images with no runtime; push with no socket.<br>
**Evaluate `rules_img`** — if `tar` is the bottleneck, upgrade.<br>
**Slide-as-Code** — the deck is just another build target.

<div class="mt-8 opacity-70">

What you build is byte-for-byte what runs — layers are just build outputs.

</div>

---
layout: two-cols
layoutClass: gap-8
---

# One last loop

The Python sample renders **this repo's own dependency graph** with `dot`, and
the deck imports the result — a build action drawing the graph of the build
that produced this very slide.

```bash
bazel run //tools:render_graph \
  -- //samples/python:image
```

::right::

<img src="./graphs/samples_python-image.png"
     class="max-h-72 object-contain"
     alt="first-party dependency graph of //samples/python:image" />
