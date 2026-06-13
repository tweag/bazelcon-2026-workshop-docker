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
layout: center
class: text-center
---

# Takeaways

**Slide-as-Code** — clone this repo's structure.<br>
**Benchmark** — measure Dockerfile vs. Bazel/OCI on your own images.<br>
**Mental model** — layers are granular, cacheable build outputs, not blobs.

<div class="mt-8 opacity-70">

Once layers are just artifacts, the daemon stops being special.

</div>
