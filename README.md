# High Velocity Image Composition at Scale

Workshop repo for the BazelCon 2026 talk [**"High Velocity Image Composition at Scale - Building with images with rules_img"**](https://events.linuxfoundation.org/bazelcon/features/training-day/#build-without-the-bytes-high-velocity-image-composition-at-scale) (see [`PROPOSAL.md`](PROPOSAL.md)).

A single Bazel workspace that builds **both** the container-image samples and
the Slidev presentation about them — the slides are a build artifact of the
same graph that builds the images.

📊 **Live deck:** https://tweag.github.io/bazelcon-2026-workshop-docker-build/
— published from `main` by [`.github/workflows/pages.yml`](.github/workflows/pages.yml)
**once the repo is public** (GitHub Pages can't publish from a private free-tier
repo; the workflow self-skips while private).
📄 **PDF:** attached to every
[release](https://github.com/tweag/bazelcon-2026-workshop-docker-build/releases/latest)
— built from that version's sources by [`.github/workflows/pdf.yml`](.github/workflows/pdf.yml),
which also uploads it as a build artifact on every run. To make your own:
`bazel run //slides:export_pdf`.

## Prerequisites

- [Bazelisk](https://github.com/bazelbuild/bazelisk) (pins Bazel via `.bazelversion`)
- Optional: Docker, only for the `Dockerfile` baseline, the ★ `docker run`
  stretch tasks and `//tools:local_rbe`
- Optional: `graphviz` (`dot`) on PATH, only for `//tools:render_graph`

You don't need Node.js: Bazel fetches its own pinned Node for the slides.

## Setup (do this before you arrive)

A cold build fetches the pinned Python interpreter, the wheels and the `.deb`
packages behind the hermetic layers, about 15 minutes and 600 MB, and leaves
~8 GB in Bazel's caches, so check your free disk first. On conference
wifi, in a room of 60, that is not a five-minute lab. Do it on a good connection:

```bash
git clone https://github.com/tweag/bazelcon-2026-workshop-docker-build
cd bazelcon-2026-workshop-docker-build
bazel test //samples/... //labs/... //tools/...   # warms everything the labs need (all green)
```

To view the slides locally (optional):

```bash
bazel run //slides:present       # dev server with hot reload
```

Don't use `//...` for setup: it also builds the Slidev deck and its Node
dependencies, which you don't need to follow along.

## Doing the labs

The self-guided labs live in [`labs/`](labs/). Each lab folder has a README with
its goal, start command and tasks. Start with:

```bash
bazel run //labs:progress        # every lab and task, with its command
bazel test -k //labs:tasks       # your progress: one PASSED/FAILED line per task
bazel run //labs:explain         # why is my test red? (decodes structure tests)
```

[`labs/README.md`](labs/README.md) is the index. Two labs have nothing to fix: [`labs/playground/`](labs/playground/) is a working two-layer image
meant to be edited, and [`labs/remote/`](labs/remote/) runs a remote cache, an
OCI registry and a remote-execution cluster **on your own machine** — no account,
and no Docker for the first two:

```bash
bazel run //tools:local_cache       # REAPI cache      -> localhost:9092
bazel run //tools:local_registry    # OCI registry     -> localhost:5000
bazel run //tools:local_rbe         # remote execution -> localhost:8980 (Docker)
```

## Handy commands

```bash
bazel run //samples/python:image_load                     # load the sample image into Docker
bazel run //samples/shared_layers:digests                 # prove two images share layers
bazel run //tools:render_graph -- //samples/python:image  # render the dependency graph
bazel run //slides:build                                  # static deck in slides/dist
bazel run //slides:export_pdf                             # PDF lands in docs/
bazel test //...                                          # everything, slides included
```

## Layout

| Path | What |
|------|------|
| `samples/python/` | Python + Graphviz app via `rules_img` (+ a `Dockerfile` baseline) |
| `samples/distroless/` | the `dot` system dep as a hermetic, pinned layer (`rules_distroless`, on scratch) |
| `samples/shared_layers/` | two images sharing layers + a digest-diff proof |
| `labs/` | self-guided labs (Dockerfile → rules_img / build-time / ghost / hardware) + `playground/` + `remote/` |
| `benchmark/pytest_tax/` | the "docker tax": pytest in Docker vs. Bazel `py_test` |
| `slides/` | Slidev deck that transcludes the real sample sources |
| `tools/` | `render_graph` (graph → PNG), `local_registry`, `local_cache`, `local_rbe` |
