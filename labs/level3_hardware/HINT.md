# Level 3 hints — The Hardware Wall

Progressive hints. Read only as far as you need.

## surface — `:app_test`
- Just checks the bindings + kernel are wired and the device probe runs. Whether
  a device exists depends on the environment — that's the wall, shown for real
  below.

## deep — `:image_structure_test` is red (no `libOpenCL` / ICD in the image)
- The image has bindings but no **driver**. Bundle a CPU OpenCL implementation
  (POCL) so the image carries a device that works without a GPU.
- <details><summary>answer</summary>

  Same two edits as Level 2. Wrap the tar as a layer:

  ```python
  layer_from_tar(
      name = "pocl_layer_img",
      src = "@pocl_apt//:flat",  # libOpenCL loader + POCL CPU ICD + /etc/OpenCL/vendors
  )
  ```

  Then add `":pocl_layer_img"` to the `image_manifest`'s `layers`.

  Re-pin after editing `pocl.yaml`: `bazel run @pocl_apt//:lock`.
  </details>

## abyss — run a kernel, then punch a hole for a GPU
- Run it on CPU: `bazel run //labs/level3_hardware:image_load`, then
  `docker run --rm bwb/level3-hardware` → POCL exposes a CPU device and
  `vector_add` runs. No GPU, no host driver — fully portable.
- Punch a hole for a real GPU:
  - NVIDIA: `docker run --gpus all ...` (NVIDIA Container Toolkit), or
  - Intel/AMD: `docker run --device /dev/dri ...`.
- Why it can't be baked in: the GPU driver/userspace must match the **host
  kernel module**. So the device is a *declared runtime contract*, the one place
  we deliberately step outside hermeticity. The build stays hermetic; only the
  device binding is external.

## Read more

- [POCL](https://github.com/pocl/pocl) — the portable OpenCL implementation that
  turns your CPU into an OpenCL device
- [pyopencl docs](https://documen.tician.de/pyopencl/) — contexts, queues,
  buffers, and `create_some_context`
- `rules_distroless` — [the `apt` extension](https://github.com/GoogleContainerTools/rules_distroless)
- [Debian's usr-merge](https://wiki.debian.org/UsrMerge) — why the lab layers set
  `mergedusr = True` in `MODULE.bazel`
- Runtime device contracts — [NVIDIA Container Toolkit](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/index.html)
  · [`docker run --device`](https://docs.docker.com/reference/cli/docker/container/run/#device)
