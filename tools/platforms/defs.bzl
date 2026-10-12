"""LINUX: the `platform` every image_manifest here builds for.

Container images are Linux, whatever the laptop. On a Linux host this is None:
the image builds in the current configuration, so nothing changes. On macOS it
moves the image (and everything in its layers: interpreter, wheels, apt
packages) to Linux on the Mac's own CPU, so an Apple-silicon Mac gets an arm64
image that Docker Desktop runs natively. Tests and `bazel run` tools stay on
the host.

Check it from Linux:
    bazel build --platforms=//tools/platforms:macos_aarch64_simulated //labs/level1_buildtime:image
"""

LINUX = select({
    "//tools/platforms:macos_aarch64": "//tools/platforms:linux_aarch64",
    "//tools/platforms:macos_x86_64": "//tools/platforms:linux_x86_64",
    "//conditions:default": None,
})
