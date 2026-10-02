# Level 1 — The Build-Time Trap (`cryptography`)

**Goal:** ship a Python app whose dependency is a compiled Rust + OpenSSL
extension, with **no compiler running at build time**. Bazel should *consume* a
pinned, hashed, prebuilt wheel, and you prove that by opening the image layer.

**Deck concepts:** `pip.parse` hub + `requirement()` · `pkg_tar(include_runfiles
= True)` → `layer_from_tar` → `image_manifest` · a layer is just a tar ·
`build_test` can't see what's inside an image.

## Start

```bash
bazel test //labs/level1_buildtime:app_test          # starts RED
```

No install? Edit in a fork and let GitHub check it: see
[Check your answers on GitHub](../README.md#check-your-answers-on-github-nothing-to-install).

You only edit one file: [`BUILD.bazel`](BUILD.bazel). Look for the `# TODO`.

## Tasks

| # | Run | Starts | Done when |
|---|---|---|---|
| 1 | `bazel test //labs/level1_buildtime:app_test` | 🔴 | the app can import `cryptography` |
| 2 | `bazel test //labs/level1_buildtime:image_layer_test` | 🔴 | the compiled wheel is inside the image layer |
| – | `bazel test //labs/level1_buildtime:image_build_test` | 🟢 | already green. It passes even when Task 1 isn't done, and that's the lesson |
| ★ | *(stretch, no command)* | – | you can explain the sdist fallback |

### Task 1 — give the app its wheel

`app_test` fails with `ModuleNotFoundError: cryptography`: the `py_binary` has
`deps = []`, so pip never fetched anything.

<details><summary>Answer</summary>

```python
load("@labs_pypi//:requirements.bzl", "requirement")  # already loaded

py_binary(
    name = "app",
    ...
    deps = [requirement("cryptography")],
)
```

Nothing gets compiled. Bazel pulls the prebuilt manylinux wheel that is pinned,
with hashes, in [`//labs:requirements_lock.txt`](../requirements_lock.txt).
</details>

### Task 2 — prove the wheel is really *in* the image

`image_layer_test` ([`layer_test.py`](layer_test.py)) opens the app layer's tar
and checks two things: `cryptography/.../_rust.abi3.so` is in it, and there are
no source-build leftovers (`.rs`, `.c`, `Cargo.toml`). Task 1's fix turns this
test green too. Afterwards, look at the tar yourself:

```bash
bazel build //labs/level1_buildtime:app_layer
tar tf bazel-bin/labs/level1_buildtime/app_layer.tar | grep _rust
```

Now compare with `image_build_test`, which was green the whole time. A
`build_test` only proves the image *assembled*. An image with a missing Python
dependency assembles just fine, so the only honest check is to look inside the
layer.

### ★ Stretch — the sdist fallback

Pick a package/version with **no** wheel for your platform. pip then downloads
the **sdist** and compiles it against the host's compiler and OpenSSL headers.
That is the non-hermetic moment. The fix is to stay on prebuilt, hashed wheels
for every target platform, and to treat a missing wheel as a red flag rather
than letting it quietly become a host build. Cross-arch works the same way: the
lock carries both amd64 and aarch64 wheels, so an arm64 image is *wheel
selection*, not C cross-compilation.

## Stuck?

```bash
bazel run //labs:explain -- level1                                    # why is it red?
diff labs/level1_buildtime/BUILD.bazel labs/level1_buildtime/solution/BUILD.bazel
```

## Read more

- `rules_python`: [pip dependencies](https://rules-python.readthedocs.io/en/latest/pypi/index.html)
  · [`py_binary` / `py_test`](https://rules-python.readthedocs.io/en/latest/api/rules_python/python/defs.html)
- [Wheels vs. sdists](https://packaging.python.org/en/latest/discussions/package-formats/)
  · [PEP 600, `manylinux` tags](https://peps.python.org/pep-0600/)
- `rules_img`: [`layer_from_tar`](https://github.com/bazel-contrib/rules_img/blob/main/docs/layer.md)
  · [`image_manifest`](https://github.com/bazel-contrib/rules_img/blob/main/docs/image.md)
  · [`rules_pkg` `pkg_tar`](https://github.com/bazelbuild/rules_pkg)
