# Level 1 hints — The Build-Time Trap

Progressive hints. Read only as far as you need.

## surface — `:app_test` is red (`ModuleNotFoundError: cryptography`)
- The `py_binary` has `deps = []`. pip never fetched the wheel.
- <details><summary>answer</summary>

  ```python
  deps = [requirement("cryptography")]
  ```
  No compiler runs — Bazel pulls the prebuilt manylinux wheel pinned (with
  hashes) in `//labs:requirements_lock.txt`.
  </details>

## deep — `:image_build_test`
- Once the wheel is a dep, the image assembles with the wheel packed into a
  content-addressed layer. It should pass with no extra changes.
- The real exercise: rebuild for arm64 and watch `rules_python` select the
  *aarch64* wheel from the same lock — that's "cross-compilation" here. The lock
  already carries both arches; nothing is compiled, the wheel is just selected
  by platform tag.

## abyss — force + diagnose the sdist fallback
- Pick a package/version with **no** wheel for your platform (or force a source
  build). `pip` then downloads the **sdist** and compiles the extension against
  the host's compiler + OpenSSL headers — the non-hermetic moment.
- The fix is to stay on prebuilt, hashed wheels for every target platform, and
  to treat a missing wheel as a red flag, not a silent host build.

## Read more

- `rules_python` — [installing pip dependencies](https://rules-python.readthedocs.io/en/latest/pypi/index.html)
  · [`py_binary` / `py_test`](https://rules-python.readthedocs.io/en/latest/api/rules_python/python/defs.html)
- Wheels vs. sdists — [Python packaging formats](https://packaging.python.org/en/latest/discussions/package-formats/)
  · [PEP 600, the `manylinux` tags](https://peps.python.org/pep-0600/) that decide
  whether you get a prebuilt wheel or a source build
- `rules_img` — [`layer_from_tar`](https://github.com/bazel-contrib/rules_img/blob/main/docs/layer.md)
  · [`image_manifest`](https://github.com/bazel-contrib/rules_img/blob/main/docs/image.md)
- `rules_pkg` — [`pkg_tar`](https://github.com/bazelbuild/rules_pkg), which turns
  the `py_binary`'s runfiles into the tar this level packs
