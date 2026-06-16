---
theme: default
title: Building Without Bytes
info: |
  ## Building Without Bytes
  Orchestrating Containerized Workflows with Bazel — BazelCon 2026.

  These slides are built by the same Bazel workspace that builds the
  container images they describe. The code on screen is imported live from
  the repo's real source files.
class: text-center bazel-cover
transition: slide-left
mdc: true
---

<div class="bazel-blocks"><i></i><i></i><i></i><i></i></div>

# Building Without Bytes

### Orchestrating Containerized Workflows with Bazel

<div class="opacity-70 mt-8">

These slides were not exported from an app — they were **built by Bazel**,
from the same workspace that builds the containers they describe.

</div>

<div class="abs-br m-6 opacity-50 text-sm">BazelCon 2026 · Rafael Lima</div>

---
layout: statement
---

# This slide is a build artifact

`bazel build //slides:build` → this deck.<br>
`bazel build //samples/python:image` → the image we'll discuss.

Same graph. Same cache. Same guarantees.

If you can model a talk as a build artifact,<br>you can model your whole supply chain as one.

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

# The "before": an imperative Dockerfile

The Docker daemon installs the `dot` system dependency with `RUN apt-get` —
an opaque, stateful layer. Editing `app.py` busts everything below the `COPY`.

<<< ../samples/python/Dockerfile docker {14-28}

---

# The payload: Python + a *non-hermetic* system dep

`graphviz` shells out to the `dot` binary — the apt dependency we must make
explicit once we leave the daemon. The app renders the workshop's own graph:

<<< ../samples/python/app.py#build_graph python {*}{maxHeight:'380px'}

---

# The "after": layers as declarative build outputs

No daemon. The image is composed from content-addressed layers in the action
graph; changing `app.py` reuses the base + deps layers untouched.

<<< ../samples/python/BUILD.bazel#oci python {*}{maxHeight:'380px'}

---

# High-velocity incrementalism

Architect layers by **volatility**, then rebuild only what changed:

1. **Base OS** — static &nbsp;·&nbsp; 2. **Runtimes / deps** — infrequent &nbsp;·&nbsp; 3. **App code** — constant

The 1-second rebuild — change one string in a multi-GB app:

```bash
$ docker build -t app .              # invalidates at COPY . /app → 2–3 min
$ bazel run //samples/rules_img:load # re-assembles one blob   → seconds
```

**`rules_oci` → `rules_img`:** skip `tar`/compression; a Go-based incremental
loader keeps layers as transparent blobs until final assembly.

---

# Daemonless & verifiable

No `/var/run/docker.sock`. Build on restricted CI runners (no root), on
macOS / Windows without a VM, side-by-side with every other Bazel action.

Test **without running** the container — structure checks in the sandbox:

```python
container_structure_test(
    name = "structure_test",
    image = ":image",
    configs = ["test_config.yaml"],
)
```

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

<img src="./graphs/samples_python-image.png"
     class="rounded shadow max-h-100 object-contain"
     alt="dependency graph of //samples/python:image" />

---

# Same artifact, three philosophies

| Feature | Dockerfile | rules_oci | rules_img |
|---|---|---|---|
| **Execution** | Imperative | Declarative | Optimized declarative |
| **Hermetic** | No | Yes | Yes |
| **Speed** | Slow (cache miss) | Fast | Ultra-fast |
| **Daemon req.** | Yes | No | No |
| **Tar-less** | No | No | Yes |

The further right, the more your build behaves like the rest of your Bazel
graph: deterministic, cacheable, daemonless.

---
layout: center
class: text-center
---

# Takeaways

**Stop scripting, start mapping** — declare *what goes where*, not what to run.<br>
**Architect for layers** — heavy deps apart from volatile code.<br>
**Go daemonless** — better CI security and portability.<br>
**Evaluate `rules_img`** — if `tar` is the bottleneck, upgrade.<br>
**Slide-as-Code** — the deck is just another build target; benchmark your own images.

<div class="mt-8 opacity-70">

Once layers are just artifacts, the daemon stops being special.

</div>
