# Building Without Bytes

Workshop repo for the BazelCon 2026 talk **"Building Without Bytes:
Orchestrating Containerized Workflows with Bazel"** (see [`PROPOSAL.md`](PROPOSAL.md)).

A single Bazel workspace that builds **both** the container-image samples and
the Slidev presentation about them — the slides are a build artifact of the
same graph that builds the images. The plan and task breakdown live in
[`TASK.md`](TASK.md).

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

# Render the repo's own dependency graph (the live "it draws itself" demo).
bazel run //tools:render_graph -- //...

# Preview the slides with hot reload.
bazel run //slides:present

# Build the deck, then export the PDF (lands in docs/).
bazel build //slides:build
bazel run //slides:export_pdf
```

## Layout

| Path | What |
|------|------|
| `samples/python/` | Python + Graphviz app, packaged via `rules_oci` (and a `Dockerfile` baseline) |
| `samples/oci/`, `samples/img/` | the same image via `rules_oci` and `rules_img` |
| `slides/` | Slidev (Markdown) deck that transcludes the real sample sources |
| `benchmark/` | `Dockerfile` build vs. Bazel/OCI build comparison |
| `tools/` | `render_graph` — turns the build graph into a PNG via `dot` |

See [`TASK.md`](TASK.md) for the full, numbered build plan and acceptance
criteria.
