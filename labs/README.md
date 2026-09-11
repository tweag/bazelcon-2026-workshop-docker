# The Flow Descent — hands-on labs

A self-paced, test-driven path through three escalating real-world hermeticity
problems in Python. It's modelled on the game *Flow*: one continuous ladder you
descend **as deep as you want**. Every depth is a win; nobody is gated. `bazel
test` is your depth meter.

## Start here

```bash
bazel run //labs:progress      # the ladder + the exact command for every rung
```

Three commands are all the tooling there is:

| Command | What it does |
|---|---|
| `bazel run //labs:progress` | prints the ladder and every rung's command |
| `bazel run //labs:explain` | says *why* a red rung is red (see below) |
| `bazel test //labs/...` | runs the whole green reference set |

### Before you start

- **Bazel** via [Bazelisk](https://github.com/bazelbuild/bazelisk) — the version
  is pinned in `.bazelversion`, you don't pick one.
- **Docker** — only for the *abyss* rungs, which run the images you build. Every
  other rung is daemonless.
- **~15 minutes and ~600 MB of downloads on the first run** — the pinned Python
  interpreter, the wheels, and two pinned apt archives. Do this on a good
  connection, not on conference wifi:

  ```bash
  bazel test //labs/...     # warms everything the labs need
  ```

  After that, a rung takes **under a second** (Level 1) or **~15 seconds**
  (Levels 2 and 3 — the structure tests unpack the image tarball once per check).

## How to play

1. Pick a rung from `//labs:progress` and run its command.
2. If it's **[RED]**, that failure *is* the spec for what "done" means. Open the
   level's `BUILD.bazel`, find the `# TODO`, and fill it in.
3. If it's **[green]**, run it anyway and read the test — those rungs exist to
   show you something, not to be fixed.
4. Re-run. Green = rung cleared. Descend further, or move across to the next
   level.

Two motions: *across* the three levels, and *down* into the optional depth of
each. Mix and match to your level — entry-level folks might spend the whole time
reaching Level 2's surface and leave happy; experts dive to the abyss.

### When a rung is red and the error is useless

`container_structure_test` reports through a JUnit XML file, so a failure looks
like this in the console — and nothing else:

```
time="..." level=fatal msg=FAIL
```

That is not your fault and there is nothing to debug. Run:

```bash
bazel run //labs:explain            # every failed lab test, decoded
bazel run //labs:explain -- level2  # just one level
```

```
──────────────────────────────────────────────────────────────────────
  //labs/level2_ghost:image_structure_test
──────────────────────────────────────────────────────────────────────
  ✗ File Existence Test: tesseract engine binary is bundled
      Error examining file in container: lstat /tmp/.../usr/bin/tesseract: no such file or directory
  ✗ Metadata Test
      variable TESSDATA_PREFIX not found in image env
```

### Still stuck

Every level has a `HINT.md` with progressive, foldable answers, and a
`solution/` you can diff against:

```bash
diff labs/level2_ghost/BUILD.bazel labs/level2_ghost/solution/BUILD.bazel
```

The entire reference set is green: `bazel test //labs/...`.

## The ladder

| Level | Surface | Deep | Abyss (opt-in) |
|---|---|---|---|
| **1 · Build-Time Trap** (`cryptography`) | 🔴 wheel imports & works (`:app_test`) | 🔴 the wheel is really *in* the layer (`:image_layer_test`) | force + diagnose the sdist fallback |
| **2 · Ghost** (`pytesseract`) | 🟢 the engine is missing, in pure Python (`:app_test`) | 🔴 binary + data + `TESSDATA_PREFIX` (`:image_structure_test`) | OCR runs for real |
| **3 · Hardware Wall** (`pyopencl`) | 🟢 bindings + device probe (`:app_test`) | 🔴 CPU ICD (POCL) bundled (`:image_structure_test`) | run a kernel on CPU; punch a hole for a GPU |

Then, when you want to build rather than solve:

- [**`playground/`**](playground/) — a green, working two-layer image with no
  puzzle in it. This is the place to add your own code, deps, files and
  assertions. Start at [`playground/README.md`](playground/README.md).
- [**`REMOTE.md`**](REMOTE.md) — a remote cache, an OCI registry and a
  remote-execution cluster, all on your own machine. No account, and no Docker
  for the first two — they are pinned static binaries that Bazel fetches:

  ```bash
  bazel run //tools:local_cache       # REAPI cache      -> localhost:9092
  bazel run //tools:local_registry    # OCI registry     -> localhost:5000
  bazel run //tools:local_rbe         # remote execution -> localhost:8980 (Docker)
  ```

  This is where `--remote_download_minimal` stops being a slide: 258 MB of image
  on disk becomes 177 KB. It is also where remote execution catches a real
  hermeticity bug in this very repo — read §4.

## What each level teaches

- **Level 1 — Build-Time Trap.** Bazel *consumes* a pinned, hashed, prebuilt
  wheel; no compiler runs. The trap is the **sdist fallback** when no wheel
  matches the target platform — then `pip` builds from source against the host.
  Cross-arch is per-arch *wheel selection*, not C cross-compilation. The deep
  rung opens the layer tarball and checks, because `build_test` cannot: an image
  missing a Python dependency assembles perfectly.
- **Level 2 — The Ghost.** `pip install` gives a pure-Python wrapper that
  secretly shells out to a system binary. We make the binary (and its data)
  real and hermetic with a pinned `rules_distroless` apt layer — no `RUN`, no
  daemon, no network — and prove it daemonlessly with a structure test.
- **Level 3 — The Hardware Wall.** Even a perfect image can't manufacture a GPU.
  POCL (a software OpenCL ICD) lets the kernel run on the **CPU** anywhere, so
  the lesson is demoable without a GPU. A real GPU stays a *runtime contract*
  (`/dev/dri`, NVIDIA Container Toolkit): the driver must match the host kernel,
  so it can't be baked in — the one deliberate break in hermeticity.

## Mental model (the takeaway)

When a containerized Python app fails, ask **which wall** you hit:
build-time (compiler/wheel) → runtime OS dependency (the ghost) → hardware
(device/driver). Each has a different fix; this descent gives you all three.

## Notes

- **Stacking an apt layer on a distro base needs `mergedusr = True`.** The lab
  layers set it in `MODULE.bazel`; `//samples/distroless` deliberately does not,
  because it builds from scratch. The comment there explains why — it is the
  single sharpest gotcha in the repo, and it fails *silently*: the structure
  test still passes while `docker run` dies with `exec ...: no such file or
  directory`. Read it before you add an apt layer of your own.
- The apt manifests pin **bookworm**, matching the `python:3.12-slim-bookworm`
  base. Mixing Debian releases across a base and its layers gives you two
  glibcs in one filesystem.
- Structure-test paths are amd64 (`x86_64-linux-gnu`); the arm64 layer lands
  under `aarch64-linux-gnu`.
- Skeleton rungs are tagged `manual`, so they're excluded from `bazel test
  //...` — only the green `solution/` targets run in CI. You run your own rungs
  by name (the `progress` meter lists them).
- Re-lock Python deps: `bazel run //labs:requirements.update`. Re-pin an apt
  layer: `bazel run @tesseract_apt//:lock` / `@pocl_apt//:lock`.

## Read more

Each level's `HINT.md` ends with links for that level specifically. The general
background:

- Bazel — [build concepts](https://bazel.build/concepts/build-ref) ·
  [building programs](https://bazel.build/run/build) ·
  [`tags` and other common attributes](https://bazel.build/reference/be/common-definitions#common-attributes)
  (that's what `manual` means) ·
  [test output flags](https://bazel.build/docs/user-manual#test-output)
- [`rules_img`](https://github.com/bazel-contrib/rules_img) —
  [layers](https://github.com/bazel-contrib/rules_img/blob/main/docs/layer.md) ·
  [images](https://github.com/bazel-contrib/rules_img/blob/main/docs/image.md) ·
  [pulling a base](https://github.com/bazel-contrib/rules_img/blob/main/docs/pull.md) ·
  [pushing](https://github.com/bazel-contrib/rules_img/blob/main/docs/push.md)
- [`rules_python`](https://rules-python.readthedocs.io/en/latest/) —
  [pip dependencies](https://rules-python.readthedocs.io/en/latest/pypi/index.html)
- [`rules_distroless`](https://github.com/GoogleContainerTools/rules_distroless)
  — hermetic `.deb` layers
- [`rules_pkg`](https://github.com/bazelbuild/rules_pkg) — `pkg_tar`
- [`container_structure_test`](https://github.com/GoogleContainerTools/container-structure-test)
  — the daemonless assertions used in Levels 2 and 3
