# Level 2 hints — The "Ghost" Runtime Trap

Progressive hints. Read only as far as you need.

## surface — `:image_structure_test` is red ("tesseract binary is bundled" fails)
- The Python wrapper is already wired; the missing piece is the **engine
  binary**, which `pip` never installs. Add it as a hermetic, pinned apt layer.
- <details><summary>answer</summary>

  Two edits, both in `BUILD.bazel`. First wrap the hermetic apt tar as a layer:

  ```python
  layer_from_tar(
      name = "tesseract_layer_img",
      src = "@tesseract_apt//:flat",  # the real `tesseract` + libs + eng data
  )
  ```

  Then add it to the image's `layers`:

  ```python
  image_manifest(
      name = "image",
      base = image("python_base_img"),
      entrypoint = ["/app/app"],
      layers = [
          ":app_layer_img",
          ":tesseract_layer_img",
      ],
  )
  ```
  </details>

## deep — same test, the data-file & `TESSDATA_PREFIX` checks
- The binary alone can't find its language data. Point it at the tessdata dir.
- <details><summary>answer</summary>

  ```python
  env = {"TESSDATA_PREFIX": "/usr/share/tesseract-ocr/5/tessdata/"}
  ```
  </details>

## abyss — make OCR actually run
- `sample.png` is already in this directory but is not in the image. Add it to
  `pkg_tar(name = "app_layer")`'s `srcs`, then:

  ```bash
  bazel run //labs/level2_ghost:image_load
  docker run --rm bwb/level2-ghost --ocr /app/sample.png     # -> HERMETIC OCR
  ```

  Everything the engine needs — the binary, `libtesseract`, leptonica, the
  English `.traineddata`, and `TESSDATA_PREFIX` — came from the pinned apt
  layer. Nothing was installed at runtime and no network was touched.
- For a *daemonless* run, wire a `py_test` that puts the bundled `tesseract` on
  `PATH` via runfiles and sets `TESSDATA_PREFIX` — this is the genuinely hard
  part, and the point: making a system binary callable hermetically.
- Re-pin the layer after editing `tesseract.yaml`: `bazel run @tesseract_apt//:lock`.

## Read more

- `rules_distroless` — [the `apt` extension](https://github.com/GoogleContainerTools/rules_distroless),
  which resolves and pins `.deb`s without ever running `apt-get`
- [`snapshot.debian.org`](https://snapshot.debian.org/) — the time-machine archive
  the manifest pins to, and the reason the lock is reproducible
- [Debian's usr-merge](https://wiki.debian.org/UsrMerge) — why `MODULE.bazel`
  passes `mergedusr = True` for the lab layers but *not* for the scratch-based
  `//samples/distroless`
- `container_structure_test` — [test types](https://github.com/GoogleContainerTools/container-structure-test#file-existence-tests)
  (`fileExistenceTests`, `fileContentTests`, `metadataTest`, `commandTests`)
- [tesseract docs](https://tesseract-ocr.github.io/tessdoc/) ·
  [pytesseract on PyPI](https://pypi.org/project/pytesseract/) — note that the
  PyPI page tells you to install the engine separately. That sentence *is* this
  level.
