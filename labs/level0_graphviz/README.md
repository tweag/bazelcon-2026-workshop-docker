# Level 0 — From Dockerfile to `rules_img` (`graphviz`)

**Goal:** rebuild the deck's running example, the graphviz app from
[`samples/python/Dockerfile`](../../samples/python/Dockerfile), without a
Dockerfile. Translate `FROM` and `ENTRYPOINT` into `image_manifest` attributes,
and replace `RUN apt-get install graphviz` with a pinned `dot` layer.

**The before**, from [`samples/python/Dockerfile`](../../samples/python/Dockerfile):

```dockerfile
FROM python:3.12-slim-bookworm

# System dep: `dot` binary — non-hermetic.
RUN apt-get update \
    && apt-get install -y --no-install-recommends graphviz \
    && rm -rf /var/lib/apt/lists/*

# Python deps.
COPY requirements_lock.txt /tmp/requirements.txt
RUN pip install --no-cache-dir -r /tmp/requirements.txt

# App source — edits bust the layers below.
WORKDIR /app
COPY app.py /app/app.py

ENTRYPOINT ["python", "/app/app.py", "--render", "/tmp/supply_chain.png"]
```

**Deck concepts:** the whole translation (Module 1) · a base is a digest, not a
tag · the system dep becomes pinned bytes · the entrypoint is a launcher ·
daemonless validation.

## Start

```bash
bazel test //labs/level0_graphviz:image_structure_test   # starts RED (3 checks)
bazel run  //labs:explain -- level0                       # decodes the bare "FAIL"
```

No install? Edit in a fork and let GitHub check it: see
[Check your answers on GitHub](../README.md#check-your-answers-on-github-nothing-to-install).

You only edit [`BUILD.bazel`](BUILD.bazel). Look for the `# TODO`s. The app
layer is done for you: it's the deck's own `//samples/python:app_layer`,
unchanged. The checks live in [`image_test.yaml`](image_test.yaml).

| Dockerfile | → | Bazel |
|---|---|---|
| `FROM python:3.12-slim-bookworm` | Task 1 | `base = image("python_base_img")` |
| `RUN apt-get install graphviz` | Task 2 | `layer_from_tar(src = "@graphviz_lab_apt//:flat")` |
| `RUN pip install` · `COPY app.py` | done | `//samples/python:app_layer` |
| `ENTRYPOINT ["python", "/app/app.py", "--render", ...]` | Task 1 | `entrypoint = ["/app/app", ...]` |

## Tasks

| # | Run | Starts | Done when |
|---|---|---|---|
| 1 | `bazel test //labs/level0_graphviz:image_structure_test` | 🔴 | the python base is underneath and the entrypoint is set |
| 2 | *same test* | 🔴 | `/usr/bin/dot` is in the image |
| ★ | `bazel run //labs/level0_graphviz:image_load && docker run --rm bwb/level0-graphviz` | – | the PNG renders (needs Docker) |
| ★ | *same test* | – | the `dot` layer is compressed (shrink the layer) |

### Task 1 — translate `FROM` and `ENTRYPOINT`

The base is already pulled **by digest** in
[`MODULE.bazel`](../../MODULE.bazel) (region `base_pull`) and exposed as
`image("python_base_img")`. The entrypoint doesn't need `python`: `/app/app` is
the `py_binary` launcher, and it runs the hermetic interpreter that ships in the
app layer.

<details><summary>Answer</summary>

```python
image_manifest(
    name = "image",
    base = image("python_base_img"),
    entrypoint = [
        "/app/app",
        "--render",
        "/tmp/supply_chain.png",
    ],
    layers = [":app_layer_img"],
)
```
</details>

### Task 2 — `dot` as a pinned layer

`@graphviz_lab_apt//:flat` is `graphviz` plus its dependencies, resolved from
[`graphviz.lock.json`](graphviz.lock.json) at load time. No build action touches
the network.

<details><summary>Answer</summary>

```python
layer_from_tar(
    name = "graphviz_layer_img",
    src = "@graphviz_lab_apt//:flat",
)

image_manifest(
    ...
    layers = [
        ":app_layer_img",
        ":graphviz_layer_img",
    ],
)
```
</details>

### ★ Stretch — make it render

```bash
bazel run //labs/level0_graphviz:image_load
docker run --rm bwb/level0-graphviz
# ... There is no layout engine support for "dot"
#     Perhaps "dot -c" needs to be run (with installer's privileges) to register the plugins?
```

`dot` is there, but its plugin registry isn't. On a normal system, Debian's
**postinst** script runs `dot -c` during `apt-get install`. A pinned apt layer
only unpacks files and never runs maintainer scripts. Run the step yourself to
confirm:

```bash
docker run --rm --entrypoint sh bwb/level0-graphviz \
  -c 'dot -c && /app/app --render /tmp/g.png'          # -> [ok] rendered /tmp/g.png
```

Now compare with the "before" image, where `apt-get` did run postinst:

```bash
docker build -t before samples/python && docker run --rm before
```

The harder version is to generate that plugin config at *build* time, so the
image renders with no runtime step. It's an open follow-up in the repo too (see
the note in [`samples/distroless/BUILD.bazel`](../../samples/distroless/BUILD.bazel)).

### ★ Stretch — shrink the layer

`layer_from_tar` ships a tar exactly as it gets it, and `@graphviz_lab_apt//:flat` is a plain,
uncompressed tar. The app layer already asks `rules_img` to rewrite it.
Do the same for the system layer:

```python
layer_from_tar(
    name = "graphviz_layer_img",
    src = "@graphviz_lab_apt//:flat",
    optimize = True,  # identical files -> hardlinks, then zstd (see .bazelrc)
)
```

```bash
bazel build //labs/level0_graphviz:image
grep -o '"size":[0-9]*' bazel-bin/labs/level0_graphviz/image_manifest.json   # the last one is your layer
```

The layer goes from about **94 MB to 38 MB**. Its digest changes, but the files
inside it don't, so the structure test stays green. Docker unpacks zstd layers
from version 23 onwards.

## Stuck?

```bash
bazel run //labs:explain -- level0
diff labs/level0_graphviz/BUILD.bazel labs/level0_graphviz/solution/BUILD.bazel
```

This lab has its own **bookworm** manifest with `mergedusr = True`. The
`//samples/distroless` one pins bullseye and is built for `scratch`, and
stacking it on a bookworm base would mix two glibcs. Re-pin after editing
`graphviz.yaml`: `bazel run @graphviz_lab_apt//:lock`.

## Read more

- `rules_img`: [pull](https://github.com/bazel-contrib/rules_img/blob/main/docs/pull.md)
  · [`image_manifest`](https://github.com/bazel-contrib/rules_img/blob/main/docs/image.md)
- [`rules_distroless` apt extension](https://github.com/GoogleContainerTools/rules_distroless)
  · [Debian maintainer scripts](https://www.debian.org/doc/debian-policy/ch-maintainerscripts.html)
- [Graphviz](https://graphviz.org/) · [graphviz on PyPI](https://pypi.org/project/graphviz/)
