# Samples — the same image, built the hermetic way

Every sample here packages the **same** Python + Graphviz app (it renders the
repo's own supply-chain graph via the `dot` binary). The point is the contrast
between the imperative `Dockerfile` "before" and the declarative, daemonless
`rules_img` "after", holding the payload constant.

| Path | How it's built | Run it |
|------|----------------|--------|
| [`python/Dockerfile`](python/Dockerfile) | the "before": imperative `docker build` | `docker build -t bwb/python-graphviz-dockerfile python && docker run --rm bwb/python-graphviz-dockerfile` |
| [`python/`](python/) | the "after": `rules_img` — `py_binary` → `pkg_tar` → `layer_from_tar` → `image_manifest` | `bazel run //samples/python:image_load` |
| [`distroless/`](distroless/) | `rules_distroless` — the `dot` system dep as a hermetic, pinned layer on scratch | `bazel run //samples/distroless:image_load` |
| [`shared_layers/`](shared_layers/) | two images sharing layers + a digest-diff proof | `bazel run //samples/shared_layers:digests` |

## The "before" vs. "after"

The **Dockerfile** handles the `dot` system dependency the daemon way —
`apt-get install graphviz` in a `RUN` layer. It works, but that layer is an
opaque blob produced by a stateful daemon, and editing `app.py` busts every
layer after the `COPY`.

The **`rules_img`** variant treats the same dependency as a declarative,
content-addressed layer in the action graph: change `app.py` and only the app
layer rebuilds; the base and deps layers are reused (and dedupe across images
and at the registry). See the workshop walkthrough in
[`../slides/content.md`](../slides/content.md).

## Why `rules_img`

`rules_img` builds images **tar-less**: `image_manifest` + `layer_from_tar`
treat layers as transparent content-addressed blobs, skipping `tar`/compression
on every build and using a Go-based incremental loader/pusher (`image_load` /
`image_push`). The base is pulled via its own `images` extension
(`python_base_img`, `layer_handling = "lazy"` so the daemonless
`container_structure_test` can read a full tarball).

Push to a local registry: `bazel run //tools:local_registry`, then
`bazel run //samples/python:push`.
