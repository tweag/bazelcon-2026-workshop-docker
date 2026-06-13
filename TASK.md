# TASK: Prepare the Bazel Workspace (Samples + Presentation)

Bootstrap the `bazelcon2026-docker-build-workshop` repo into a single Bazel
workspace that builds **both** the container-image samples and the
presentation itself. This is the "dogfooding" backbone of the talk
(see `PROPOSAL.md`): the slides and the example images are produced by the
same `bazel build`.

## Goal

A clean `git clone && bazel build //...` produces:
1. The example OCI container images (`rules_oci` / `rules_img`).
2. The rendered presentation as a build artifact.
3. A benchmark target comparing a `Dockerfile` build vs. the Bazel/OCI build.

## Requirements

1. **Single workspace** — samples, presentation, and benchmark all live in one
   Bazel module; no separate build systems or manual export steps.
2. **bzlmod** — dependencies managed via `MODULE.bazel`, not legacy `WORKSPACE`.
3. **Hermetic** — no reliance on a host Docker daemon, host Node, or ambient
   tools; toolchains and npm deps are pinned and fetched by Bazel.
4. **Reproducible** — identical inputs yield identical outputs (stable OCI
   image digests); builds are cache-friendly for local and remote caches.
5. **`bazel build //...` and `bazel test //...` are the only entry points** —
   anything a contributor or attendee needs to do is a Bazel target.
6. **Cross-platform** — builds on Linux and macOS (`linux/amd64` and
   `linux/arm64` image targets) without host-specific setup.
7. **Self-contained for the talk** — the deck builds from the real sample
   sources (see §3), so what's on screen is guaranteed to match the repo.
8. **Latest `rules_oci` and `rules_img`** — pin to the most recent released
   versions of both rulesets (and bump as releases land), so the talk reflects
   current APIs rather than deprecated patterns.

## 1. Workspace foundation

1. [ ] Add `MODULE.bazel` (bzlmod) with pinned versions of:
   - `rules_oci`
   - `rules_img`
   - `aspect_rules_js` (+ `rules_nodejs`) to run **Slidev** hermetically.
   - any language rules the sample app needs (e.g. `rules_go`, `rules_python`).
2. [ ] Add `.bazelrc` (remote-cache-friendly defaults, `--enable_bzlmod`).
3. [ ] Add `.bazelversion`.
4. [ ] Add root `BUILD.bazel`.
5. [ ] Update `README.md`: what the repo is, prerequisites, `bazel build //...`,
   how to view the slides, how to run the benchmark.

## 2. Container-image samples (`//samples/...`)

1. [ ] A minimal sample app to containerize (small static binary or service).
2. [ ] **`samples/dockerfile/`** — the "before": a traditional `Dockerfile`
   build, kept as the benchmark baseline and the on-slide contrast.
3. [ ] **`samples/oci/`** — the "after": the same image via `rules_oci`
   (`oci_image`, `oci_load`, `oci_push`) with explicit, granular layers.
4. [ ] **`samples/img/`** — the equivalent via `rules_img`, highlighting its
   differences from `rules_oci`.
5. [ ] Image tests that fan out in parallel (`oci`/container structure tests,
   smoke tests) to demonstrate parallelized testing.
6. [ ] Demonstrate incremental rebuild + layer cache reuse on a small source
   change (this is the payoff shown live).
7. [ ] Unit tests for the sample app itself (`go_test` / `py_test` /
   equivalent), so the thing being containerized is independently verified.
8. [ ] Cross-image equivalence test: assert the `dockerfile`, `oci`, and
   `img` variants produce functionally identical images (same entrypoint,
   same runtime behavior on a smoke request) so the "before/after" contrast
   is honest.
9. [ ] **`samples/python/`** — a Python + **Graphviz** sample (`rules_python` +
   `py_binary`) packaged into an OCI image. The app uses the `graphviz`
   Python package, which shells out to the `dot` system binary — a clear,
   loud **non-hermetic system dependency** (`graphviz` apt package). Package
   it as three distinct, cacheable layers: the `dot` system binary/base
   layer, the pip deps layer, and the app-source layer — so a change to app
   code reuses the cached system + deps layers untouched. This is the
   granular-layer payoff for an interpreted language with a system dep, not
   just a static binary.
   - Dummy app renders something interesting: e.g. the repo's own
     dependency graph (`bazel query --output=graph` / `aquery`) into a PNG
     via `dot`, closing the dogfooding loop (the build draws its own graph).
10. [ ] **`//tools:render_graph`** — a `py_binary` run target (`bazel run
    //tools:render_graph -- //...`) that uses `BUILD_WORKSPACE_DIRECTORY` and
    a separate `--output_base` to query the graph and render it to
    `slides/graphs/*.png` via `dot`. Utility target (non-hermetic: needs
    `bazel`+`dot` on PATH); powers the live "it draws its own node" demo.
    Note the hermetic, cacheable alternative (a `dot_aspect` feeding the
    slides graph artifact) as a stretch goal.

## 3. Presentation (`//slides/...` — "Slide-as-Code")

Tooling: **[Slidev](https://sli.dev)** — Markdown slide source, rendered via
Node under Bazel (`rules_js` / `aspect_rules_js` + `npm` deps).

1. [ ] Slide source as Markdown under `slides/` (`slides.md` + any partials).
2. [ ] `package.json` / pinned `@slidev/cli` deps wired into the workspace's
   npm setup (`pnpm`/`npm_translate_lock`), so the toolchain is hermetic.
3. [ ] A Bazel rule/macro that runs `slidev build` (and `slidev export` for
   PDF) → final artifact, so the deck is a normal build output, not a
   manual export.
4. [ ] `bazel run //slides:present` → `slidev` dev server for live preview.
5. [ ] Slide content references the *actual* sample targets above (Slidev
   code blocks / `<<< @/...` imports), so the code shown on screen is the
   code in the repo.
6. [ ] **Live snippet transclusion**: slides import spans from real source
   files via Slidev's `<<< @/path` syntax — whole file, named region
   (`<<< @/samples/oci/BUILD.bazel#oci-image`), or line range with
   highlighting (`<<< @/samples/oci/BUILD.bazel {4-9}`). Author with
   `// #region` / `// #endregion` markers in the sample sources so the
   deck never holds a drifting copy.
7. [ ] **Declare sample files as slides inputs**: every transcluded file
   (BUILD files, Dockerfile, app source) must be in the `//slides`
   target's `srcs`/`data` so it exists in the Bazel sandbox. This makes
   `//slides` explicitly depend on `//samples` — a broken sample can
   break the deck, which is the strongest form of the dogfooding thesis.
8. [ ] **Spike — Vite/Slidev path resolution under sandbox**: the `@` alias
   and `vite.resolve.alias` assume a normal project root; runfiles
   symlinks may need the base pointed at the right directory.
9. [ ] Build smoke test: `slidev build` succeeds and emits the expected
   artifact (non-empty `index.html` / PDF) as a `build_test` or
   `sh_test`, so a broken deck fails CI.
10. [ ] Snippet-integrity test: every `<<< @/...` import resolves and each
    referenced `#region` marker still exists in the source — fails loudly
    when a sample is renamed or a region deleted, instead of rendering an
    empty code block.

## 4. Benchmark target (`//benchmark/...`)

1. [ ] A runnable target that times the `Dockerfile` build vs. the Bazel/OCI
   build, cold and warm cache, and reports the deltas.
2. [ ] Reproducible: documents exactly what is measured so attendees can run
   it on their own images. This is takeaway #2 in `PROPOSAL.md`.
3. [ ] Harness test: the benchmark runs end-to-end and emits parseable
   output with the expected fields (cold/warm, deltas). Assert structure
   and that it completes — NOT specific timing thresholds, which are
   machine-dependent and would make the test flaky.

## 5. Testing & CI

1. [ ] `bazel test //...` is green from a clean clone and is the single
   command that runs every test above.
2. [ ] CI workflow (`.github/workflows/`) running `bazel test //...`
   (+ `build_test //...`) on push/PR, ideally with a remote cache so the
   caching story is real, not just narrated.
3. [ ] Dogfooding-invariant test: assert via `bazel query` that
   `//slides` depends on `//samples` (e.g. `somepath(//slides, //samples/...)`
   is non-empty), locking in the thesis that the deck is built from the
   real sample graph.
4. [ ] Reproducibility check: build the OCI image twice and assert an
   identical digest (deterministic, content-addressable output) — the
   concrete proof behind the "content-addressable" claim in `PROPOSAL.md`.

## Acceptance criteria

1. `bazel build //...` succeeds from a clean clone.
2. `bazel test //...` runs the image tests in parallel and passes.
3. `bazel run //slides:present` renders the deck.
4. `bazel run //benchmark:compare` (name TBD) produces the comparison.
5. The three takeaways in `PROPOSAL.md` each map to a real target in the repo:
   Slide-as-Code structure, the benchmark, and granular cacheable layers.

## Open decisions

- Sample app language/runtime (keep it tiny to keep build times honest).
- Whether `samples/img/` ships in v1 or is added after the `rules_oci` path
  is solid.
