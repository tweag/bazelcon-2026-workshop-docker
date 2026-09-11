#!/usr/bin/env bash
# Depth meter / guide for the "Flow descent" labs (TASK §10).
# Prints the rung ladder and the exact command for each rung. Run a command;
# green = you cleared that rung. Descend as deep as you like — every depth is a
# win, nobody is gated. Run me with:  bazel run //labs:progress
set -euo pipefail

cat <<'LADDER'

  ~~~  THE FLOW DESCENT  ~~~  build images that survive contact with reality

  Copy a command, run it, read what it says. [RED] rungs start failing and you
  make them pass. [green] rungs already pass — run them anyway and read the test
  to see what they prove. Go as deep as you want; every depth is a win.

  LEVEL 1 — The Build-Time Trap        (cryptography: Rust + OpenSSL wheel)
    surface  [RED]    bazel test //labs/level1_buildtime:app_test
    deep     [RED]    bazel test //labs/level1_buildtime:image_layer_test
    ·        [green]  bazel test //labs/level1_buildtime:image_build_test
    abyss             open labs/level1_buildtime/HINT.md   (sdist fallback)

  LEVEL 2 — The "Ghost" Runtime Trap   (pytesseract -> system `tesseract`)
    surface  [green]  bazel test //labs/level2_ghost:app_test
    deep     [RED]    bazel test //labs/level2_ghost:image_structure_test
    ·                   3 checks: the binary, its language data, TESSDATA_PREFIX
    abyss             open labs/level2_ghost/HINT.md       (OCR for real)

  LEVEL 3 — The Hardware Wall          (pyopencl + POCL on CPU)
    surface  [green]  bazel test //labs/level3_hardware:app_test
    deep     [RED]    bazel test //labs/level3_hardware:image_structure_test
    abyss             open labs/level3_hardware/HINT.md    (run a kernel; GPUs)

  PLAYGROUND — nothing to fix, everything to change
    bazel test //labs/playground/...     then read labs/playground/README.md

  LAB R — remote cache, registry & remote execution, all on localhost
    bazel run //tools:local_cache      then read labs/REMOTE.md

  ---------------------------------------------------------------------------

  A rung is red and the error is useless?  container_structure_test reports
  through JUnit XML, so the console only says `level=fatal msg=FAIL`. Decode it:

      bazel run //labs:explain
      bazel run //labs:explain -- level2      # just one level

  Still stuck? Every level has a HINT.md with progressive, foldable answers, and
  a solution/ you can diff against:

      diff labs/level2_ghost/BUILD.bazel labs/level2_ghost/solution/BUILD.bazel

  The whole reference set is green:  bazel test //labs/...

LADDER
