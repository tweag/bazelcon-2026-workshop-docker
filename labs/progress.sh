#!/usr/bin/env bash
# Lists every self-guided lab and task with its exact command.
#   bazel run //labs:progress
set -euo pipefail

cat <<'LABS'

  ~~~  SELF-GUIDED LABS  ~~~  build images that survive contact with reality

  Each lab's README.md has the goal, the start command and the tasks.
  [RED] tasks start failing: edit the lab's BUILD.bazel until they pass.
  [green] tasks already pass: run them and read the test. * = optional stretch.

  LEVEL 0 — From Dockerfile to rules_img  labs/level0_graphviz/README.md
    task 1-2 [RED]    bazel test //labs/level0_graphviz:image_structure_test
    *                 bazel run //labs/level0_graphviz:image_load   (render the PNG)

  LEVEL 1 — The Build-Time Trap        labs/level1_buildtime/README.md
    task 1   [RED]    bazel test //labs/level1_buildtime:app_test
    task 2   [RED]    bazel test //labs/level1_buildtime:image_layer_test
    ·        [green]  bazel test //labs/level1_buildtime:image_build_test
    *                 the sdist fallback (read the README)

  LEVEL 2 — The "Ghost" Runtime Trap   labs/level2_ghost/README.md
    task 0   [green]  bazel test //labs/level2_ghost:app_test
    task 1-2 [RED]    bazel test //labs/level2_ghost:image_structure_test
    *                 bazel run //labs/level2_ghost:image_load   (OCR for real)

  LEVEL 3 — The Hardware Wall          labs/level3_hardware/README.md
    task 0   [green]  bazel test //labs/level3_hardware:app_test
    task 1   [RED]    bazel test //labs/level3_hardware:image_structure_test
    *                 bazel run //labs/level3_hardware:image_load   (kernel on CPU)

  LEVEL 4 (extra) — One interpreter, N images    labs/level4_shared/README.md
    task 0   [green]  bazel test //labs/level4_shared:groups_test
    task 1   [RED]    bazel test //labs/level4_shared:shared_layers_test
    *                 bazel run //labs/level4_shared:api_load   (both services, shared layers)

  PLAYGROUND — nothing to fix, everything to change    labs/playground/README.md
    bazel test //labs/playground/...

  REMOTE — cache, registry & remote execution on localhost    labs/remote/README.md
    bazel run //tools:local_cache

  ---------------------------------------------------------------------------

  Red with a useless error (`level=fatal msg=FAIL`)? Decode it:

      bazel run //labs:explain
      bazel run //labs:explain -- level2      # just one lab

  Reference answers:

      diff labs/level2_ghost/BUILD.bazel labs/level2_ghost/solution/BUILD.bazel

  Where am I? One PASSED/FAILED line per task:

      bazel test -k //labs:tasks

  The whole reference set is green:  bazel test //labs/...

LABS
