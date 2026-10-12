# High Velocity Image Composition at Scale

Workshop repo for the BazelCon 2026 talk [**"High Velocity Image Composition at Scale - Building images with rules_img"**](https://events.linuxfoundation.org/bazelcon/features/training-day/#build-without-the-bytes-high-velocity-image-composition-at-scale).

A single Bazel workspace that builds **both** the container-image samples and
the Slidev presentation about them — the slides are a build artifact of the
same graph that builds the images.

📊 **Live deck:** https://tweag.github.io/bazelcon-2026-workshop-docker/
— published from `main` by [`.github/workflows/pages.yml`](.github/workflows/pages.yml).
📄 **PDF:** attached to every
[release](https://github.com/tweag/bazelcon-2026-workshop-docker/releases/latest)
— built from that version's sources by [`.github/workflows/pdf.yml`](.github/workflows/pdf.yml),
which also uploads it as a build artifact on every run. To make your own:
`bazel run //slides:export_pdf`.

## Prerequisites

- Linux or macOS. On Windows, use WSL2 and clone inside it: the labs'
  `solution/app.py` files are symlinks, and a native Windows checkout without
  `core.symlinks` turns them into one-line text files.
- [Bazelisk](https://github.com/bazelbuild/bazelisk) (pins Bazel via `.bazelversion`)
- The [GitHub CLI](https://cli.github.com) (`gh`), logged in with `gh auth login`,
  to fork and clone in one step. No `gh`? See the fallback under [Setup](#setup-do-this-before-you-arrive).
- A C compiler: `build-essential` on Debian/Ubuntu, `xcode-select --install` on
  macOS. Most developer machines already have one. Only the images with apt
  layers need it (`//samples/distroless`, labs Levels 0, 2 and 3), because they
  build a small tool (`gawk`) from source. **No compiler, or not allowed to
  install one?** Add `--config=hermetic-cc` to your commands and Bazel uses its
  own pinned compiler instead; see [No C compiler](#no-c-compiler) below.
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
gh repo fork tweag/bazelcon-2026-workshop-docker --clone -- --single-branch
cd bazelcon-2026-workshop-docker
bazel test //samples/... //labs/... //tools/...   # warms everything the labs need (all green)
```

This forks the repo into your account and clones **your fork** (`origin`), with
the workshop repo as `upstream`. You work in your fork, so keep it **public**:
that keeps GitHub Actions free. No `gh`? Fork on github.com, then clone your fork:

```bash
git clone --single-branch --branch main https://github.com/<you>/bazelcon-2026-workshop-docker
```

To view the slides locally (optional):

```bash
bazel run //slides:present       # dev server with hot reload
```

Don't use `//...` for setup: it also builds the Slidev deck and its Node
dependencies, which you don't need to follow along.

### No C compiler

If setup stops with an error that mentions `gawk`, `gcc`, `cc`, or
`@bazel_tools//tools/cpp:toolchain_type`, Bazel couldn't find a C compiler on
your machine. You don't need to install one. Run the same command with
`--config=hermetic-cc`:

```bash
bazel test --config=hermetic-cc //samples/... //labs/... //tools/...
```

It downloads a pinned compiler (zig cc, about 50 MB) and uses that. The images
come out byte-for-byte the same either way. To turn it on for every command, so
you don't have to remember the flag:

```bash
echo "common --config=hermetic-cc" >> .bazelrc.user   # gitignored, read by .bazelrc
```

It isn't the default only because [`labs/remote/`](labs/remote/README.md#4--remote-execution-advanced)
uses the host compiler to show what remote execution catches.

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

## Read more

**rules_img**, the ruleset this workshop teaches:

- [rules_img](https://github.com/bazel-contrib/rules_img), with API docs for
  [images](https://github.com/bazel-contrib/rules_img/blob/main/docs/image.md) (`image_manifest`),
  [layers](https://github.com/bazel-contrib/rules_img/blob/main/docs/layer.md) (`layer_from_tar`, `layer_from_binary`),
  [pulling base images](https://github.com/bazel-contrib/rules_img/blob/main/docs/pull.md) and
  [pushing](https://github.com/bazel-contrib/rules_img/blob/main/docs/push.md) (`image_push`)
- [*rules_img: a ground-up redesign of container image building for Bazel*](https://www.youtube.com/watch?v=biYXmAv4Ppk),
  Malte Poll (Tweag), BazelCon 2025, and the
  [companion blog post](https://www.tweag.io/blog/2025-12-18-rules_img/)

**Other rulesets and tools** the samples and labs use:

- [rules_distroless](https://github.com/GoogleContainerTools/rules_distroless): `.deb` packages as pinned, hermetic layers
- [rules_python](https://rules-python.readthedocs.io/en/latest/) and
  [rules_runfiles_group](https://github.com/bazel-contrib/rules_runfiles_group): the Python app and its layer split
- [container-structure-test](https://github.com/GoogleContainerTools/container-structure-test): the checks behind `bazel test //labs:tasks`
- [hermetic_cc_toolchain](https://github.com/uber/hermetic_cc_toolchain): what `--config=hermetic-cc` turns on
- [crane](https://github.com/google/go-containerregistry/blob/main/cmd/crane/README.md),
  [bazel-remote](https://github.com/buchgr/bazel-remote) and
  [Buildfarm](https://github.com/buildfarm/buildfarm): the local registry, cache and remote execution in `labs/remote/`

**Bazel background:**

- [Remote caching](https://bazel.build/remote/caching) and [remote execution](https://bazel.build/remote/rbe)
- [Build without the Bytes in Bazel 7](https://blog.bazel.build/2023/10/06/bwob-in-bazel-7.html)

**Earlier talks and workshops** this one builds on:

- [Bazel and Docker with rules_oci](https://www.youtube.com/watch?v=uFxh6rHfMKc), Alex Eagle (Aspect), Bazel Community Day 2023
- [Talk on migrating off rules_docker](https://www.youtube.com/watch?v=rLDKcNv7xAY), linked from the deck's lineage slide
- [tweag/bazel-workshop-2024](https://github.com/tweag/bazel-workshop-2024), Tweag's Bazel workshop from 2024

## Credits

The code and content are [MIT](LICENSE), except for these files, which belong to
their owners:

- `slides/images/bazelcon_color_alt.svg`: the BazelCon logo, a trademark of The Linux Foundation
- `slides/images/tweag-logo.svg`: the Tweag logo, Modus Create LLC
- `slides/images/talk-rules-oci.jpg` and `slides/images/talk-rules-img.jpg`: title cards of the
  [Alex Eagle (Aspect)](https://www.youtube.com/watch?v=uFxh6rHfMKc) and
  [Malte Poll (Tweag)](https://www.youtube.com/watch?v=biYXmAv4Ppk) talks, shown on the deck's lineage slide
- `slides/fonts/`: Roboto, Google, under the Apache License 2.0 (see its [LICENSE.txt](slides/fonts/LICENSE.txt))
