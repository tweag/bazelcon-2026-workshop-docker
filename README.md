# High Velocity Image Composition at Scale

Workshop repo for the BazelCon 2026 talk [**"High Velocity Image Composition at Scale - Building with images with rules_img"**](https://events.linuxfoundation.org/bazelcon/features/training-day/#build-without-the-bytes-high-velocity-image-composition-at-scale) (see [`PROPOSAL.md`](PROPOSAL.md)).

A single Bazel workspace that builds **both** the container-image samples and
the Slidev presentation about them — the slides are a build artifact of the
same graph that builds the images. The plan and task breakdown live in
[`TASK.md`](TASK.md).

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
- Node.js + npm (for the Slidev deck)
- `graphviz` (`dot`) on PATH for the live graph-rendering demo
- Docker (only for the `Dockerfile` baseline / benchmark "before")

## Attending the workshop? Do this before you arrive

The first lab is "clone and build", and it is the one thing that can eat the
session: a cold build fetches the pinned Python interpreter, the `@pypi` hub, and
the 162 `.deb` packages behind the hermetic `dot` layer. On conference wifi, in a
room of 60, that is not a five-minute lab.

```bash
git clone https://github.com/tweag/bazelcon-2026-workshop-docker-build
cd bazelcon-2026-workshop-docker-build
bazel build //samples/...     # warms the cache — do this on a good connection
docker pull registry:2        # optional: the registry lab prefers registry:2 when
                              # Docker is around, but falls back to a pinned,
                              # daemonless binary if it isn't
```

Use `//samples/...`, not `//...`: the latter also builds the Slidev deck, which
pulls a whole Node toolchain you don't need to follow along.

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

## Doing the labs

The take-home labs live in [`labs/`](labs/) and are self-paced. Start with:

```bash
bazel run //labs:progress        # the ladder + the command for every rung
bazel run //labs:explain         # why is my rung red? (decodes structure tests)
bazel test //labs/...            # the green reference set — also warms the cache
```

[`labs/README.md`](labs/README.md) is the full guide. Two things there are not
puzzles: [`labs/playground/`](labs/playground/) is a working two-layer image
meant to be edited, and [`labs/REMOTE.md`](labs/REMOTE.md) runs a remote cache, an
OCI registry and a remote-execution cluster **on your own machine** — no account,
and no Docker for the first two:

```bash
bazel run //tools:local_cache       # REAPI cache      -> localhost:9092
bazel run //tools:local_registry    # OCI registry     -> localhost:5000
bazel run //tools:local_rbe         # remote execution -> localhost:8980 (Docker)
```

## Layout

| Path | What |
|------|------|
| `samples/python/` | Python + Graphviz app via `rules_img` (+ a `Dockerfile` baseline) |
| `samples/distroless/` | the `dot` system dep as a hermetic, pinned layer (`rules_distroless`, on scratch) |
| `samples/shared_layers/` | two images sharing layers + a digest-diff proof |
| `labs/` | self-paced "Flow descent" labs (build-time / ghost / hardware) + a `playground/` to edit |
| `benchmark/pytest_tax/` | the "docker tax": pytest in Docker vs. Bazel `py_test` |
| `slides/` | Slidev deck that transcludes the real sample sources |
| `tools/` | `render_graph` (graph → PNG), `local_registry`, `local_cache`, `local_rbe` |

See [`TASK.md`](TASK.md) for the full, numbered build plan and acceptance
criteria.
