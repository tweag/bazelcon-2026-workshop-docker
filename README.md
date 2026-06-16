# Building Without Bytes

Workshop repo for the BazelCon 2026 talk [**"Building Without Bytes:
High-Velocity Image Composition at Scale"**](https://events.linuxfoundation.org/bazelcon/features/training-day/#build-without-the-bytes-high-velocity-image-composition-at-scale) (see [`PROPOSAL.md`](PROPOSAL.md)).

A single Bazel workspace that builds **both** the container-image samples and
the Slidev presentation about them — the slides are a build artifact of the
same graph that builds the images. The plan and task breakdown live in
[`TASK.md`](TASK.md).

📊 **Live deck:** https://akafael.github.io/bazelcon2026-docker-build-workshop/
— published from `main` by [`.github/workflows/pages.yml`](.github/workflows/pages.yml)
**once the repo is public** (GitHub Pages can't publish from a private free-tier
repo; the workflow self-skips while private).
📄 **PDF:** [`docs/building-without-bytes.pdf`](docs/building-without-bytes.pdf).

## Prerequisites

- [Bazelisk](https://github.com/bazelbuild/bazelisk) (pins Bazel via `.bazelversion`)
- Node.js + npm (for the Slidev deck)
- `graphviz` (`dot`) on PATH for the live graph-rendering demo
- Docker (only for the `Dockerfile` baseline / benchmark "before")

## Quick start

```bash
# Build everything (images, slides, tools).
bazel build //...

# Run all tests (image structure, snippet integrity, reproducibility, ...).
bazel test //...

# Render the Python + Graphviz sample image and load it into Docker.
bazel run //samples/python:image_load

# Validate the image WITHOUT a daemon (container_structure_test, tar driver).
bazel test //samples/python:image_structure_test

# Prove two images share layers (prints the shared blob digests).
bazel run //samples/shared_layers:digests

# Render the repo's own (first-party) dependency graph.
bazel run //tools:render_graph -- //samples/python:image

# Preview the slides with hot reload; build the deck; export the PDF.
bazel run //slides:present
bazel run //slides:build         # static HTML in slides/dist
bazel run //slides:export_pdf    # PDF lands in docs/
```

## Layout

| Path | What |
|------|------|
| `samples/python/` | Python + Graphviz app via `rules_oci` (+ a `Dockerfile` baseline) |
| `samples/rules_oci/`, `samples/rules_img/` | the same image, one per ruleset (shared layer) |
| `samples/distroless/` | the `dot` system dep as a hermetic, pinned layer (`rules_distroless`) |
| `samples/shared_layers/` | two images sharing layers + a digest-diff proof |
| `benchmark/pytest_tax/` | the "docker tax": pytest in Docker vs. Bazel `py_test` |
| `slides/` | Slidev deck that transcludes the real sample sources |
| `tools/` | `render_graph` (graph → PNG), `local_registry` (registry:2) |

See [`TASK.md`](TASK.md) for the full, numbered build plan and acceptance
criteria.
