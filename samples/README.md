# Samples — one image, several ways

Every sample here packages the **same** Python + Graphviz app (it renders the
repo's own supply-chain graph via the `dot` binary). The point is to compare
*how the image is built*, holding the payload constant.

The Bazel variants reuse the exact same layer — `//samples/python:app_layer`
(the `py_binary` runfiles tar) — so the **only variable is the ruleset**, which
makes the before/after contrast honest.

| Path | How it's built | Run it |
|------|----------------|--------|
| [`python/Dockerfile`](python/Dockerfile) | the "before": imperative `docker build` | `docker build -t bwb/python-graphviz-dockerfile python && docker run --rm bwb/python-graphviz-dockerfile` |
| [`python/`](python/) | `rules_oci` (full example: `py_binary` → `pkg_tar` → `oci_image`) | `bazel run //samples/python:image_load` |
| [`rules_oci/`](rules_oci/) | `rules_oci`, focused — `oci_image` + `oci_load` over the shared layer | `bazel run //samples/rules_oci:load` |
| [`rules_img/`](rules_img/) | `rules_img` — `image_manifest` + `layer_from_tar` + `image_load` | `bazel run //samples/rules_img:load` |
| [`distroless/`](distroless/) | `rules_distroless` — the `dot` system dep as a hermetic, pinned layer | `bazel run //samples/distroless:image_load` |

## The "before" vs. "after"

The **Dockerfile** handles the `dot` system dependency the daemon way —
`apt-get install graphviz` in a `RUN` layer. It works, but that layer is an
opaque blob produced by a stateful daemon, and editing `app.py` busts every
layer after the `COPY`.

The **Bazel** variants treat the same dependency as a declarative,
content-addressed layer in the action graph: change `app.py` and only the app
layer rebuilds; the base and deps layers are reused (and dedupe across images
and at the registry). See the workshop walkthrough in
[`../slides/content.md`](../slides/content.md).

## `rules_oci` vs. `rules_img`

Both produce a functionally identical image from the same `app_layer`:

- **`rules_oci`** (`//samples/rules_oci`): the standard rules — `oci_image`,
  `oci_load`, `oci_push`; packages layers with `tar`.
- **`rules_img`** (`//samples/rules_img`): `image_manifest`, `layer_from_tar`,
  `image_load`, `image_push`; skips `tar`/compression with a Go-based
  incremental loader/pusher (the base is pulled via its own `images` extension).

Push either to a local registry: `bazel run //tools:local_registry`, then
`bazel run //samples/rules_oci:push` / `//samples/rules_img:push`.
