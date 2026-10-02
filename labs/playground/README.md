# Playground — a working image you are meant to change

**Goal:** the three levels each hide a problem to fix. This package doesn't. It
is green from the first command, and it's the place to *change* things and watch
the build graph react: layers, digests, dependencies, config, base, push.

**Deck concepts:** an image is tar layers + a manifest + a config (OCI) ·
content-addressed digests · split layers by volatility · a base is a digest ·
distroless · the Docker tax · daemonless push.

## Start

```bash
bazel run  //labs/playground:app          # the payload, no image involved
bazel test //labs/playground/...          # unit test + daemonless image test
bazel run  //labs/playground:image_load   # into the local Docker daemon
docker run --rm bwb/playground
```

## What's in it

| Layer | Built by | Holds |
|---|---|---|
| app | `pkg_tar(:app_layer)` → `layer_from_tar` | the hermetic interpreter, `app.py`, any deps you add |
| config | `pkg_tar(:config_layer)` → `layer_from_tar` | just `greeting.txt`, at `/etc/playground/` |

Both sit on `python_base_img`, pinned by digest in `MODULE.bazel`.

## Tasks

Pick them in any order. Each one is independent.

| # | Task | Deck module |
|---|---|---|
| 1 | Read the recipe card: manifest + config | 0 · a sandwich of tars |
| 2 | Prove the layer split | 2 · catering |
| 3 | Add a dependency, watch it appear | 1 · `pip.parse` hub |
| 4 | Add a file to the image and assert it | appendix · `container_structure_test` |
| 5 | Change the entrypoint / env | 1 · the entrypoint is a launcher |
| 6 | One base, N images | 1 · a base is a digest · 4 · one base, N images |
| 7 | Drop the bread: distroless | 2 · distroless |
| 8 | Add a system dependency | 1 · the system dep becomes pinned bytes |
| 9 | Break it on purpose | 2 · when the image won't run |
| 10 | Pay the Docker tax | 1 · the "Docker tax" |
| 11 | Push it | 3 · shipping software |

**1 — Read the recipe card.** An image is an ordered list of layer digests plus a
config. Neither needs a daemon to read:

```bash
bazel build //labs/playground:image
cat bazel-bin/labs/playground/image_manifest.json   # config digest + layers[]
cat bazel-bin/labs/playground/image_config.json     # Env, Entrypoint, rootfs.diff_ids
```

The first four layers are the base. The last two are the app and config layers
built in this package.

**2 — Prove the layer split.** Save the digests, edit one thing, compare:

```bash
grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/playground/image_manifest.json > /tmp/before
echo "edited" >> labs/playground/greeting.txt
bazel build //labs/playground:image
grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/playground/image_manifest.json | diff /tmp/before -
```

Two digests move: the config layer and the image config that lists it. The
~36 MB app layer and the base were reused untouched. Revert `greeting.txt` and rebuild: the digests
come back byte-identical.

**3 — Add a dependency.** `app.py` reports which pinned libraries it can import.
In `BUILD.bazel`:

```python
load("@labs_pypi//:requirements.bzl", "requirement")
# ... then in py_binary(name = "app", ...):
deps = [requirement("cryptography")],
```

Re-run `bazel run //labs/playground:app` and watch `cryptography` go from
"not a dep" to a version.

**4 — Add a file and assert it.** Drop a file next to `greeting.txt`, add it to
`config_layer`'s `srcs`, add a `fileExistenceTests` entry to
[`image_test.yaml`](image_test.yaml), and run
`bazel test //labs/playground:image_structure_test`.

**5 — Change the entrypoint / env.** Edit `env` or `entrypoint` on
`image_manifest`, then update the `metadataTest` in `image_test.yaml`. That's
how you pin runtime contracts without a `Dockerfile`: they're attributes, not
steps.

**6 — One base, N images.** Build a second image on the same base and compare:

```bash
bazel build //labs/playground:image //labs/level1_buildtime/solution:image
diff <(grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/playground/image_manifest.json) \
     <(grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/level1_buildtime/solution/image_manifest.json)
bazel run //samples/shared_layers:digests   # the same idea, with a shared lib layer too
```

Only the first line (the config) and the app layers differ. The four base layer
digests are identical, so they're stored, cached and pushed
**once**. Find the base in `MODULE.bazel` (region `base_pull`). It's a `digest`,
not a tag, and `layer_handling = "lazy"` fetches its blobs only when something
needs them.

**7 — Drop the bread (distroless).** Read and run the scratch image:

```bash
bazel run //samples/distroless:image_load && docker run --rm bwb/distroless
```

Look at [`samples/distroless/BUILD.bazel`](../../samples/distroless/BUILD.bazel)
for what *isn't* there: no `base`, no shell, no package manager. Now delete
`base` from the playground's `image_manifest`. It still builds and loads, but
`docker run --rm bwb/playground` fails with `exec /app/app: no such file or
directory`. The launcher needs a shell and libc that only the base provided. A
scratch image works only when every layer brings its own runtime.

**8 — Add a system dependency.** For example `jq`:

1. Copy [`../level2_ghost/tesseract.yaml`](../level2_ghost/tesseract.yaml) to
   `labs/playground/jq.yaml` and list `"jq"` under `packages:`.
2. Register it in `MODULE.bazel`, next to the other `apt.install`s:

   ```python
   apt.install(
       name = "jq_apt",
       manifest = "//labs/playground:jq.yaml",
       mergedusr = True,  # see the mergedusr note in MODULE.bazel
   )
   use_repo(apt, "jq_apt")
   ```

3. Lock it with `bazel run @jq_apt//:lock`. That writes `jq.lock.json`; then add
   `lock = "//labs/playground:jq.lock.json",` to the `apt.install`. (The tool
   offers `-- --autofix`, which needs `buildozer` on your `PATH`.)
4. Wrap `@jq_apt//:flat` in a `layer_from_tar`, add it to `layers`, and run it:

   ```bash
   bazel run //labs/playground:image_load && docker run --rm --entrypoint /usr/bin/jq bwb/playground --version
   ```

**9 — Break it on purpose.** Remove a layer from `layers`, or point `entrypoint`
at a path that doesn't exist. Which test catches it, and which doesn't? A
`build_test` can't catch anything about content, which is why Level 1 has an
`image_layer_test`. Then inspect the layer by hand:

```bash
bazel build //labs/playground:app_layer
tar tf bazel-bin/labs/playground/app_layer.tar | head
```

**10 — Pay the Docker tax.** The same test suite run as a sandboxed `py_test`
and inside a `docker build` (needs Docker):

```bash
bazel run //benchmark/pytest_tax:compare
```

**11 — Push it.** Start a local registry, then add a push target to
`BUILD.bazel`, modelled on `push` in
[`samples/python/BUILD.bazel`](../../samples/python/BUILD.bazel):

```python
load("@rules_img//img:push.bzl", "image_push")  # at the top, with the other loads

image_push(
    name = "push",
    image = ":image",
    registry = "localhost:5000",
    repository = "bwb/playground",
    tag = "latest",
)
```

```bash
bazel run //tools:local_registry        # add `-- --hermetic` if you have no Docker
bazel run //labs/playground:push
```

Push twice: the second push re-sends only the manifest and config; every layer
is already there. For remote cache, lazy push and remote execution, continue in
[`../remote/`](../remote/).

## Stuck?

```bash
bazel run //labs:explain -- playground    # decodes structure-test failures
git checkout labs/playground               # back to green
```
