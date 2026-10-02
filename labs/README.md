# Self-guided labs

Hands-on, test-driven labs for the workshop. Each lab folder has a `README.md`
with its **goal, the command to start, and the tasks**. That's all you need to
begin, and you don't have to open any other file first. Work at your own pace,
in any order, and stop whenever you like. `bazel test` tells you when a task is
done.

| Lab | Goal | Start with |
|---|---|---|
| [**Level 0 · Dockerfile → rules_img**](level0_graphviz/) | rebuild the deck's graphviz app without a Dockerfile | `bazel test //labs/level0_graphviz:image_structure_test` |
| [**Level 1 · Build-Time Trap**](level1_buildtime/) | ship a compiled wheel (`cryptography`) with no compiler running | `bazel test //labs/level1_buildtime:app_test` |
| [**Level 2 · Ghost**](level2_ghost/) | make the `tesseract` binary pip never installs into a pinned layer | `bazel test //labs/level2_ghost:image_structure_test` |
| [**Level 3 · Hardware Wall**](level3_hardware/) | give an OpenCL app a CPU device (POCL); see why GPUs stay a runtime contract | `bazel test //labs/level3_hardware:image_structure_test` |
| [**Level 4 · One interpreter, N images**](level4_shared/) *(extra)* | split a py_binary into interpreter / wheels / app layers that two services share | `bazel test //labs/level4_shared:shared_layers_test` |
| [**Playground**](playground/) | change a working image: layers, digests, deps, base, distroless, push | `bazel test //labs/playground/...` |
| [**Remote**](remote/) | remote cache, registry, lazy push, Build without the Bytes, RBE on localhost | `bazel run //tools:local_cache` |

## Before you start

- **Bazel** via [Bazelisk](https://github.com/bazelbuild/bazelisk). The version is
  pinned in `.bazelversion`.
- **Docker** is only needed for the ★ stretch tasks that `docker run` an image.
  Everything else is daemonless.
- **The first run takes ~15 minutes and ~600 MB of downloads** (the Python
  interpreter, wheels and three apt archives) and needs **~8 GB of free disk**
  for Bazel's caches, so do it on a good connection:

  ```bash
  bazel test //labs/...     # warms everything the labs need (all green)
  ```

  After that, a task takes under a second (Level 1) or ~5–15 s (the structure tests).

## Check your answers on GitHub (nothing to install)

You can do every lab in the browser: edit in a web editor, and let GitHub
Actions run Bazel and Docker for you.

1. **Fork** this repo (keep the fork public; Actions minutes are free for
   public repos).
2. **Enable Actions** in your fork: open its **Actions** tab and click *"I
   understand my workflows, go ahead and enable them"*.
3. **Open the editor:** press <kbd>.</kbd> on your fork's page (github.dev), or
   go to `https://vscode.dev/github/<you>/<your-fork>`.
4. **Do a lab:** edit `labs/<lab>/BUILD.bazel` as its README says, then commit
   from the Source Control panel. Committing to a new branch and opening a pull
   request **into your own fork's `main`** keeps each attempt tidy.
5. **Read the result:** Actions → **labs** → **check my lab answers** → the
   **Summary** tab. It has a task-by-task table, whether the images actually
   `docker run`, and *why* anything red is red. The check fails only if a lab
   you changed is still red; untouched labs show as ⚪ not started.
6. **Iterate:** every commit re-runs the check. The first run downloads
   ~600 MB, so it's the slow one; later runs reuse a cache.

To require *every* lab to be green, use Actions → labs → **Run workflow** with
"fail on ANY red lab" ticked. Don't open pull requests against the upstream
repo: there the workflow runs the maintainers' checks instead of yours.

The same report works locally: `python3 labs/ci/labs_ci.py answers --all`.

## How the labs work

1. Open a lab's `README.md` and run its **Start** command.
2. 🔴 **Red** means the failure *is* the spec. Edit that lab's `BUILD.bazel` at
   the `# TODO` and re-run until it's green.
3. 🟢 **Green** tasks already pass. Run them anyway and read the test, because
   they're there to show you something.
4. ★ **Stretch** tasks are optional and go deeper.

Three helper commands:

| Command | What it does |
|---|---|
| `bazel run //labs:progress` | prints every lab and task with its exact command |
| `bazel test -k //labs:tasks` | your progress: one PASSED/FAILED line per task |
| `bazel run //labs:explain [-- level2]` | says *why* a red test is red |
| `diff labs/<lab>/BUILD.bazel labs/<lab>/solution/BUILD.bazel` | shows the reference answer |

`container_structure_test` reports through JUnit XML, so a failure shows up in
the console only as `level=fatal msg=FAIL`. That's expected; `:explain` prints
the per-check reason:

```
──────────────────────────────────────────────────────────────────────
  //labs/level2_ghost:image_structure_test
──────────────────────────────────────────────────────────────────────
  ✗ File Existence Test: tesseract engine binary is bundled
      Error examining file in container: lstat /tmp/.../usr/bin/tesseract: no such file or directory
```

## Deck concept → where you practise it

| Module | Concept | Exercise |
|---|---|---|
| 0 | image = tar layers + manifest + config (OCI) | [Playground](playground/) 1 · [Level 1](level1_buildtime/) task 2 |
| 0 | content addressing: same bytes, same digest | [Playground](playground/) 2, 6 |
| 0 | hermetic build: only declared inputs are visible | [Level 2](level2_ghost/) task 0 |
| 1 | the whole translation: Dockerfile → `rules_img` | [Level 0](level0_graphviz/) tasks 1–2 |
| 1 | a base is a digest, not a tag (`images.pull`) | [Level 0](level0_graphviz/) task 1 · [Playground](playground/) 6 |
| 1 | system dep becomes pinned bytes (`apt.install` + `layer_from_tar`) | [Level 0](level0_graphviz/) task 2 · [Level 2](level2_ghost/) task 1 · [Level 3](level3_hardware/) task 1 · [Playground](playground/) 8 |
| 1 | pip hub + `pkg_tar(include_runfiles)` → one layer | [Level 1](level1_buildtime/) task 1 · [Playground](playground/) 3 |
| 1 | entrypoint / env are attributes, not steps | [Level 0](level0_graphviz/) task 1 · [Level 2](level2_ghost/) task 2 · [Playground](playground/) 5 |
| 1 | `image_load` + `docker run` | ★ stretch in Levels 0, 2 and 3 · [Playground](playground/) start |
| 1 | the "Docker tax" | [Playground](playground/) 10 |
| 2 | split layers by volatility (catering) | [Playground](playground/) 2 · [Level 4](level4_shared/) task 1 |
| 2 | distroless / `scratch` | [Playground](playground/) 7 |
| 2 | shared layers dedupe | [Playground](playground/) 6 · [Level 4](level4_shared/) task 1 |
| 2 | when the image won't run (`mergedusr`) | [Level 2](level2_ghost/) ★ B · [Playground](playground/) 9 |
| 3 | daemonless push, only missing blobs | [Playground](playground/) 11 · [Remote](remote/) 3 |
| 3–4 | eager vs. lazy push | [Remote](remote/) 3, 4 |
| 4 | Building Without Bytes | [Remote](remote/) 2 |
| 4 | remote cache + RBE | [Remote](remote/) 1, 6 |
| appendix | daemonless validation (`container_structure_test`, `py_test`) | Levels 0, 2, 3 · [Playground](playground/) 4 |
| appendix | inspect a layer / image without a daemon | [Level 1](level1_buildtime/) task 2 · [Remote](remote/) 5 |
| appendix | why there's no `RUN` to run (apt layers skip postinst) | [Level 0](level0_graphviz/) ★ |
| – | the hardware wall (runtime device contract) | [Level 3](level3_hardware/) ★ |

## The takeaway

When a containerized Python app fails, ask **which wall** you hit: build-time
(compiler/wheel, Level 1), runtime OS dependency (the ghost, Level 2), or
hardware (device/driver, Level 3). Each one has a different fix.

## Notes

- Lab tests are tagged `manual`, so `bazel test //...` skips them and only the
  green `solution/` targets run in CI. Run lab tests by name.
- The apt manifests pin **bookworm**, matching the `python:3.12-slim-bookworm`
  base. Mixing Debian releases gives you two glibcs in one filesystem.
- Re-lock Python deps: `bazel run //labs:requirements.update`. Re-pin an apt
  layer: `bazel run @graphviz_lab_apt//:lock` / `@tesseract_apt//:lock` / `@pocl_apt//:lock`.

## Read more

- Bazel: [build concepts](https://bazel.build/concepts/build-ref) ·
  [common attributes](https://bazel.build/reference/be/common-definitions#common-attributes)
  (what `manual` means) · [test output flags](https://bazel.build/docs/user-manual#test-output)
- [`rules_img`](https://github.com/bazel-contrib/rules_img):
  [layers](https://github.com/bazel-contrib/rules_img/blob/main/docs/layer.md) ·
  [images](https://github.com/bazel-contrib/rules_img/blob/main/docs/image.md) ·
  [pull](https://github.com/bazel-contrib/rules_img/blob/main/docs/pull.md) ·
  [push](https://github.com/bazel-contrib/rules_img/blob/main/docs/push.md)
- [`rules_python`](https://rules-python.readthedocs.io/en/latest/) ·
  [`rules_distroless`](https://github.com/GoogleContainerTools/rules_distroless) ·
  [`rules_pkg`](https://github.com/bazelbuild/rules_pkg) ·
  [`container_structure_test`](https://github.com/GoogleContainerTools/container-structure-test)
