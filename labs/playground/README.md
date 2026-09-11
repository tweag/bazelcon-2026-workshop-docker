# Playground — a working image you are meant to break

The three levels each hide a puzzle. This package hides nothing: it builds,
tests and runs green from the first command, and it is the only place in the
repo where you are *supposed* to add code.

```bash
bazel run  //labs/playground:app          # the payload, no image involved
bazel test //labs/playground/...          # unit test + daemonless image test
bazel run  //labs/playground:image_load   # into the local Docker daemon
docker run --rm bwb/playground
```

## What's in it

Two layers, on purpose:

| Layer | Built by | Holds |
|---|---|---|
| app | `pkg_tar(:app_layer)` → `layer_from_tar` | the hermetic interpreter, `app.py`, and any deps you add |
| config | `pkg_tar(:config_layer)` → `layer_from_tar` | just `greeting.txt`, at `/etc/playground/` |

The split is the point: change `greeting.txt` and only the tiny config layer's
digest moves — the app layer, and everything below it, is reused untouched.

## Things to try

**1 — Add a dependency, watch it appear.**
`app.py` reports which of the pinned libraries it can import. Add to
`BUILD.bazel`:

```python
load("@labs_pypi//:requirements.bzl", "requirement")
# ... then in py_binary(name = "app", ...):
deps = [requirement("cryptography")],
```

Re-run `bazel run //labs/playground:app`. Then rebuild the image and compare
`bazel build //labs/playground:image` timings — only the app layer rebuilt.

**2 — Prove the layer split.**
Note the digests, edit one thing, note them again:

```bash
bazel build //labs/playground:image
cat bazel-bin/labs/playground/image/index.json     # before
echo "edited" >> labs/playground/greeting.txt
bazel build //labs/playground:image
cat bazel-bin/labs/playground/image/index.json     # after — app layer unmoved
```

**3 — Add a file to the image and assert it.**
Drop a file next to `greeting.txt`, add it to `config_layer`'s `srcs`, then add
a `fileExistenceTests` entry in `image_test.yaml` and re-run
`bazel test //labs/playground:image_structure_test`.

**4 — Change the entrypoint / env.**
Edit `env` or `entrypoint` on `image_manifest`, then update the `metadataTest`
block in `image_test.yaml`. This is how you pin runtime contracts without a
`Dockerfile`.

**5 — Add a system dependency.**
The real exercise. Pick a Debian package, write a manifest like
[`../level2_ghost/tesseract.yaml`](../level2_ghost/tesseract.yaml), register it
in `MODULE.bazel` with `apt.install(..., mergedusr = True)`, lock it
(`bazel run @your_apt//:lock`), wrap it with `layer_from_tar` and add it to
`layers`. `mergedusr = True` matters — see the note in `MODULE.bazel`.

**6 — Break it deliberately.**
Delete a `layer_from_tar` from `layers`, or point `entrypoint` at a path that
does not exist, and see which test catches it and which one does not. The
answer ("`build_test` catches nothing about content") is the lesson behind
Level 1's `image_layer_test`.

**7 — Push it.**
```bash
bazel run //tools:local_registry        # registry:2 on localhost:5000
```
then add an `image_push` target modelled on
[`//samples/python:push`](../../samples/python/BUILD.bazel).

## When something goes red

```bash
bazel run //labs:explain            # decodes structure-test failures
```
