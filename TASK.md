# TASK: Prepare the Bazel Workspace (Samples + Presentation)

Bootstrap the `bazelcon2026-docker-build-workshop` repo into a single Bazel
workspace that builds **both** the container-image samples and the
presentation itself. This is the self-build backbone of the talk
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

1. [x] Add `MODULE.bazel` (bzlmod) with pinned versions of:
   - `rules_oci`
   - `rules_img`
   - `aspect_rules_js` (+ `rules_nodejs`) to run **Slidev** hermetically.
   - any language rules the sample app needs (e.g. `rules_go`, `rules_python`).
   - ✅ **Artefact:** [`MODULE.bazel`](MODULE.bazel) + [`MODULE.bazel.lock`](MODULE.bazel.lock)
     (latest BCR: rules_oci 2.3.0, rules_img 0.3.12, rules_python 2.0.2; Slidev
     runs via a pragmatic `sh_binary` wrapper — aspect_rules_js hermetic path
     deferred to §3.8).
2. [x] Add `.bazelrc` (remote-cache-friendly defaults, `--enable_bzlmod`).
   - ✅ **Artefact:** [`.bazelrc`](.bazelrc)
3. [x] Add `.bazelversion`.
   - ✅ **Artefact:** [`.bazelversion`](.bazelversion)
4. [x] Add root `BUILD.bazel`.
   - ✅ **Artefact:** [`BUILD.bazel`](BUILD.bazel)
5. [x] Update `README.md`: what the repo is, prerequisites, `bazel build //...`,
   how to view the slides, how to run the benchmark.
   - ✅ **Artefact:** [`README.md`](README.md)

## 2. Container-image samples (`//samples/...`)

1. [x] A minimal sample app to containerize (small static binary or service).
   - ✅ **Artefact:** [`samples/python/app.py`](samples/python/app.py) (the Graphviz app doubles as the sample app)
2. [x] **`samples/python/Dockerfile`** — the "before": a traditional `Dockerfile`
   build, kept as the benchmark baseline and the on-slide contrast.
   - ✅ **Artefact:** [`samples/python/Dockerfile`](samples/python/Dockerfile)
     (lives alongside the sample; builds & renders the PNG via `apt-get install graphviz`)
3. [x] **`samples/rules_oci/`** — the "after": the same image via `rules_oci`
   (`oci_image`, `oci_load`, `oci_push`) with explicit, granular layers.
   - ✅ **Artefact:** [`samples/rules_oci/BUILD.bazel`](samples/rules_oci/BUILD.bazel)
     → `//samples/rules_oci:image` (+ `:load`); reuses `//samples/python:app_layer`
4. [x] **`samples/rules_img/`** — the equivalent via `rules_img`, highlighting its
   differences from `rules_oci`.
   - ✅ **Artefact:** [`samples/rules_img/BUILD.bazel`](samples/rules_img/BUILD.bazel)
     → `//samples/rules_img:image` (+ `:load`); same app layer via
     `image_manifest` / `layer_from_tar` / `image_load`
5. [x] Image tests that fan out in parallel (`oci`/container structure tests,
   smoke tests) to demonstrate parallelized testing.
   - ✅ **Artefact:** `//samples/python:image_structure_test`
     ([`container_structure_test`](samples/python/BUILD.bazel), `driver = "tar"`)
     + [`image_test.yaml`](samples/python/image_test.yaml) — **daemonless**
     validation (Q3), plus the `*_build_test` targets across samples.
6. [ ] Demonstrate incremental rebuild + layer cache reuse on a small source
   change (this is the payoff shown live).
7. [x] Unit tests for the sample app itself (`go_test` / `py_test` /
   equivalent), so the thing being containerized is independently verified.
   - ✅ **Artefact:** [`samples/python/app_test.py`](samples/python/app_test.py) → `//samples/python:app_test` (passing)
8. [ ] Cross-image equivalence test: assert the `dockerfile`, `oci`, and
   `img` variants produce functionally identical images (same entrypoint,
   same runtime behavior on a smoke request) so the "before/after" contrast
   is honest.
   - ↳ _the `rules_oci` and `rules_img` variants share the exact same
     `//samples/python:app_layer` and were verified by hand to run
     identically; an automated equivalence assertion is still to add._
9. [x] **`samples/python/`** — a Python + **Graphviz** sample (`rules_python` +
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
     via `dot`, closing the loop (the build draws its own graph).
   - ✅ **Artefact:** [`samples/python/`](samples/python/) → `//samples/python:image`
     (builds, loads & runs in Docker) + [`BUILD.bazel`](samples/python/BUILD.bazel).
     _Single runfiles layer for now; the 3-way system/deps/app layer split is
     still to come._
10. [x] **`//tools:render_graph`** — a `py_binary` run target (`bazel run
    //tools:render_graph -- //...`) that uses `BUILD_WORKSPACE_DIRECTORY` and
    a separate `--output_base` to query the graph and render it to
    `slides/graphs/*.png` via `dot`. Utility target (non-hermetic: needs
    `bazel`+`dot` on PATH); powers the live "it draws its own node" demo.
    Note the hermetic, cacheable alternative (a `dot_aspect` feeding the
    slides graph artifact) as a stretch goal.
    - ✅ **Artefact:** [`tools/render_graph.py`](tools/render_graph.py) → `//tools:render_graph`
      (renders its own node + [`slides/graphs/samples_python-image.png`](slides/graphs/samples_python-image.png))
11. [x] **`samples/distroless/`** — the `dot` system dep made **hermetic** via
    `rules_distroless`: a pinned manifest + lockfile (162 transitive `.deb`s)
    materialize `dot` as a content-addressed layer — no network at build, no
    daemon, no `RUN apt-get`. Refines task 9's "system-dep layer".
    - ✅ **Artefact:** [`samples/distroless/`](samples/distroless/) →
      `//samples/distroless:image` (built on scratch; verified `docker run` →
      "dot - graphviz version 2.43.0"). _Follow-ups (noted in BUILD): plugin
      `config6` for rendering; merged-usr conflict when layering onto a slim base._
12. [x] **Registry push** — `image_push` to a local registry.
    - ✅ **Artefact:** `//samples/python:push`,
      [`tools/local_registry.sh`](tools/local_registry.sh) →
      `//tools:local_registry`. (Artefact list corrected: the `//samples/rules_oci`
      and `//samples/rules_img` targets named here were deleted by §11.)
    - ✅ **No longer needs Docker.** `//tools:local_registry` uses `registry:2`
      when a daemon is reachable and otherwise serves `crane registry serve` from
      a pinned static binary (`@crane_linux_*` in MODULE.bazel). Same
      `localhost:5000` endpoint either way; `rules_img` needs no `--insecure`
      because go-containerregistry already treats `localhost:PORT` as plain HTTP.
      Adds `-- stop`. Verified daemonless: push → 7 blob transfers; edit
      `app.py` → 3; revert → 2, with a digest byte-identical to the first push.
    - ✅ **Now covered by CI** (the `remote` job) — this path had no test at all
      before.
13. [x] **`samples/shared_layers/`** — two images sharing layers (Q5): `image_a`
    and `image_b` on the same base + `:common_layer`, only the app layer differs.
    - ✅ **Artefact:** [`samples/shared_layers/`](samples/shared_layers/) →
      `:image_a`/`:image_b` + the `:digests` proof (verified: 5 shared blob
      digests, 1 unique app layer each).

## 3. Presentation (`//slides/...` — "Slide-as-Code")

Tooling: **[Slidev](https://sli.dev)** — Markdown slide source, rendered via
Node under Bazel (`rules_js` / `aspect_rules_js` + `npm` deps).

1. [x] Slide source as Markdown under `slides/` (`slides.md` + any partials).
   - ✅ **Artefact:** [`slides/slides.md`](slides/slides.md)
2. [x] `package.json` / pinned `@slidev/cli` deps wired into the workspace's
   npm setup (`pnpm`/`npm_translate_lock`), so the toolchain is hermetic.
   - ✅ **Artefact:** [`slides/package.json`](slides/package.json) +
     `slides/package-lock.json` (npm; pinned `@slidev/cli` 52.16)
3. [x] A Bazel rule/macro that runs `slidev build` (and `slidev export` for
   PDF) → final artifact, so the deck is a normal build output, not a
   manual export.
   - ✅ **Artefact:** [`slides/BUILD.bazel`](slides/BUILD.bazel) (`//slides:build`,
     `//slides:export_pdf`) + [`slides/slidev.sh`](slides/slidev.sh) →
     [`docs/building-without-bytes.pdf`](docs/building-without-bytes.pdf)
   - The `present`/`export_pdf` wrappers run on the Bazel-pinned Node
     (`@rules_nodejs//nodejs:current_node_runtime` → `SLIDEV_NODE`), not the
     host's `node`. A host Node 12 used to trip the slidev.sh preflight.
4. [x] `bazel run //slides:present` → `slidev` dev server for live preview.
   - ✅ **Artefact:** `//slides:present` in [`slides/BUILD.bazel`](slides/BUILD.bazel)
5. [x] Slide content references the *actual* sample targets above (Slidev
   code blocks / `<<< @/...` imports), so the code shown on screen is the
   code in the repo.
   - ✅ **Artefact:** [`slides/slides.md`](slides/slides.md) imports
     `../samples/python/{Dockerfile,app.py,BUILD.bazel}`
6. [x] **Live snippet transclusion**: slides import spans from real source
   files via Slidev's `<<< @/path` syntax — whole file, named region
   (`<<< @/samples/oci/BUILD.bazel#oci-image`), or line range with
   highlighting (`<<< @/samples/oci/BUILD.bazel {4-9}`). Author with
   `// #region` / `// #endregion` markers in the sample sources so the
   deck never holds a drifting copy.
   - ✅ **Artefact:** `#region` markers in [`samples/python/app.py`](samples/python/app.py)
     (`build_graph`) and [`samples/python/BUILD.bazel`](samples/python/BUILD.bazel) (`oci`)
7. [x] **Declare sample files as slides inputs**: every transcluded file
   (BUILD files, Dockerfile, app source) must be in the `//slides`
   target's `srcs`/`data` so it exists in the Bazel sandbox. This makes
   `//slides` explicitly depend on `//samples` — a broken sample can
   break the deck, which is the strongest form of the self-build thesis.
   - ✅ **Artefact:** `//slides:srcs` filegroup in [`slides/BUILD.bazel`](slides/BUILD.bazel)
     (lists the `//samples/python:*` files)
8. [x] **Spike — Vite/Slidev path resolution under sandbox**: the `@` alias
   and `vite.resolve.alias` assume a normal project root; runfiles
   symlinks may need the base pointed at the right directory.
   - ✅ **Artefact:** [`slides/vite.config.ts`](slides/vite.config.ts) (`server.fs.allow: ['..']`).
     _Resolved for the npm wrapper; full rules_js hermetic sandboxing still open._
9. [x] Build smoke test: `slidev build` succeeds and emits the expected
   artifact (non-empty `index.html` / PDF) as a `build_test` or
   `sh_test`, so a broken deck fails CI.
   - ✅ **Artefact:** `//slides:srcs_build_test` + the `slides` CI job in
     [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (runs `slidev build`)
10. [ ] Snippet-integrity test: every `<<< @/...` import resolves and each
    referenced `#region` marker still exists in the source — fails loudly
    when a sample is renamed or a region deleted, instead of rendering an
    empty code block.
    - ↳ _partially covered: the CI `slidev build` fails on a broken import
      path; a dedicated `#region`-existence assertion is still to add._

## 4. Benchmark target (`//benchmark/...`)

1. [x] A runnable target that times the `Dockerfile` build vs. the Bazel/OCI
   build, cold and warm cache, and reports the deltas.
   - ✅ **Artefact:** [`benchmark/pytest_tax/`](benchmark/pytest_tax/) →
     `//benchmark/pytest_tax:compare` — the "docker tax": same unittest suite
     via Bazel `py_test` vs. pytest-in-Docker; prints warm (per-edit) + cold
     deltas.
   - ✅ **Image-build-time + push benchmark (closes the follow-up + §8.8):**
     [`benchmark/oci_vs_img/`](benchmark/oci_vs_img/) →
     `:compare` (rules_oci vs rules_img build, 128 MiB incompressible layer,
     cold + warm, min-of-3), `:push_compare` (push timing + dedup on a local
     `registry:2`, needs docker), `:dedup` (3 images share one blob).
     **Honest findings (verified on this machine):** single-image build gap
     ~1.1×, warm ≈ equal; cold push shows **no clear rules_img win** (oci 791 ms
     vs img 1595 ms in one run). The dramatic, **ruleset-agnostic** win is
     **dedup**: a 2nd image sharing the 128 MiB layer pushes ~2.5× faster
     (749 → 296 ms) because the blob is skipped. Replaces the deck's "trust me"
     Speed row with measured numbers. _(Benchmark uses port 5055 to avoid a busy
     5000; samples keep 5000.)_
2. [x] Reproducible: documents exactly what is measured so attendees can run
   it on their own images. This is takeaway #2 in `PROPOSAL.md`.
   - ✅ **Artefact:** `compare.sh` header + content.md Module 2; uses a
     dedicated `--output_base` (warm) reusing `--disk_cache`.
3. [ ] Harness test: the benchmark runs end-to-end and emits parseable
   output with the expected fields (cold/warm, deltas). Assert structure
   and that it completes — NOT specific timing thresholds, which are
   machine-dependent and would make the test flaky.
   - ↳ _`compare` is a verified run target; an automated `*_test` wrapper is
     still to add._

## 5. Testing & CI

1. [x] `bazel test //...` is green and is the single command that runs every
   test above.
   - ✅ **Verified:** `bazel build //...` (65 targets) + `bazel test //...`
     (10/10) pass; structure test sized to silence the timeout warning.
2. [x] CI workflow (`.github/workflows/`) running `bazel test //...`
   (+ `build_test //...`) on push/PR, ideally with a remote cache so the
   caching story is real, not just narrated.
   - ✅ **Artefact:** [`.github/workflows/ci.yml`](.github/workflows/ci.yml)
   - ✅ **The remote-cache half is now real** (it was narrated, not done). The
     `remote` job stands up `//tools:local_cache` (pinned `bazel-remote`) and
     asserts a warm build after `bazel clean` is served over the wire —
     locally: `378 processes: 258 remote cache hit`. It also asserts
     `--config=local-bwb` keeps the bytes remote (258 MB → 177 KB for
     `//samples/python:image.tar`).
   - ✅ **`bazel test //...` split.** The `bazel` job now uses explicit patterns
     instead of `//...`, which was dragging the 116 MB Node toolchain into a job
     that never needed it (`//...` = 1,668 packages / 20,107 targets; the
     patterns = 753 / 7,749). The hermetic `//slides:build` moved to the `slides`
     job, which already pays for Node, so coverage is unchanged.
3. [x] Self-build invariant test: assert via `bazel query` that
   `//slides` depends on `//samples` (e.g. `somepath(//slides, //samples/...)`
   is non-empty), locking in the thesis that the deck is built from the
   real sample graph.
   - ✅ **Artefact:** "Self-build invariant" step in
     [`.github/workflows/ci.yml`](.github/workflows/ci.yml) (verified locally:
     `somepath(//slides:srcs, //samples/python:app.py)` is non-empty)
4. [x] Reproducibility check: build the OCI image twice and assert an
   identical digest (deterministic, content-addressable output) — the
   concrete proof behind the "content-addressable" claim in `PROPOSAL.md`.
   - ✅ **Artefact:** "Reproducible image digest" step in
     [`.github/workflows/ci.yml`](.github/workflows/ci.yml)

## 6. Serve slides as GitHub Pages

1. [x] Configure the Slidev build base path for project pages
   (`slidev build --base /<repo>/`), so assets resolve under
   `https://<user>.github.io/<repo>/`.
   - ✅ **Artefact:** `build:pages` script in [`slides/package.json`](slides/package.json)
     (workflow derives the base from `$GITHUB_REPOSITORY`)
2. [x] GitHub Actions workflow that builds the deck and deploys the static
   site to GitHub Pages (`actions/upload-pages-artifact` +
   `actions/deploy-pages`), triggered on push to `main`.
   - ✅ **Artefact:** [`.github/workflows/pages.yml`](.github/workflows/pages.yml)
3. [x] Set the workflow permissions (`pages: write`, `id-token: write`) and
   the `github-pages` environment; document enabling Pages → "GitHub Actions"
   as the source in repo settings.
   - ✅ **Artefact:** permissions + `github-pages` environment in
     [`.github/workflows/pages.yml`](.github/workflows/pages.yml).
     _Manual one-time step: repo Settings → Pages → Source = "GitHub Actions"._
4. [x] Link the published URL from `README.md` so attendees can open the live
   deck.
   - ✅ **Artefact:** [`README.md`](README.md) →
     `https://tweag.github.io/bazelcon-2026-workshop-docker-build/`

## 7. 90-minute workshop format (9:00–10:30)

Reframe the deck + notes from a conference talk into a 6-module, ~90-min
hands-on workshop (basics → layer optimization → push), with a Lab per module.
Instructor: Rafael Lima · Sponsored by Tweag by Modus Create.

1. [x] `slides/content.md` — full facilitator script: run sheet + six timed
   modules + a Lab each, weaving the 7 conceptual answers (mantra, runtime-vs-
   build hermeticity, Docker as a negative test, rules_distroless, action
   dedup, the "docker tax", ship-Docker-vs-source).
   - ✅ **Artefact:** [`slides/content.md`](slides/content.md)
2. [x] `slides/slides.md` — deck restructured (25 slides incl. a closing Thanks) with `layout: section`
   module dividers + concept/lab slides; on-brand BazelCon palette.
   - ✅ **Artefact:** [`slides/slides.md`](slides/slides.md) +
     [`slides/style.css`](slides/style.css) → [`docs/building-without-bytes.pdf`](docs/building-without-bytes.pdf)
3. [x] Runnable samples backing the labs: distroless (§2.11), the "docker tax"
   benchmark (§4.1), and registry push (§2.12).
   - [x] **Lab N slide closing each module (0–4)** — problem · commands · "you're
     done when" (`class: lab-slide`, `.lab-done` / `.lab-stuck` in `style.css`).
     Lab 4 is take-home (`labs/remote/README.md` §1). The lab card is now two ways
     in: README setup on a laptop, or fork + PR with the `labs` workflow
     (`.lab-card` in `style.css`). PDF re-exported locally (54 pages); a full
     one-shot `//slides:export_pdf` crashed Chromium on a low-RAM laptop, so it
     was exported in four `--range` chunks and joined with `pdfunite`.
   - [x] **No-compiler path.** Only `@gawk` (built from source by rules_distroless
     for every apt layer) compiles C, with the autodetected host compiler.
     Documented as a prerequisite, and `--config=hermetic-cc` (opt-in
     `hermetic_cc_toolchain` 4.3.0, zig cc, ~54 MB, never fetched by default)
     builds it with nothing installed. Same image digest either way. Guarded by
     the `no-compiler` CI job. Kept opt-in so `labs/remote/README.md` §4 still fails.
   - [x] **Appendix: "What 'hermetic' still borrowed from the laptop"**: the five
     host requirements found (C compiler for `gawk`, `python3`, `bash`, Docker,
     `dot`) and what each became. `python3` fixed: `//samples/shared_layers:digests`
     is now a `py_binary` with the images as data (same output, byte for byte; no
     second Bazel server or `~/.cache/bazel-shared-layers-ob` output base).
   - [x] **"When the image won't run" moved to the appendix**, between "Test:
     `container_structure_test`" and "Inspecting a layer outside Bazel". It was
     titled "Lab:" just before the real Lab 2, and its reason for sitting in
     Module 2 ("Lab 2's tasks hit it") is gone: only Level 2 ★ Stretch B triggers
     `mergedusr`. Also fixed: distroless "no apt database" (the layer ships
     `/var/lib/dpkg/status`), and "the ghost from Module 2" → Lab 1's missing `dot`.
   - [x] **Appendix review** (all 12 slides): "no network in a build action" was
     false by default (`--sandbox_default_allow_network=true`), now "shouldn't" plus
     the enforcing flag; "Daemonless validation" retitled (its `docker run` bullet
     needs a daemon); lazy push pushes to `ttl.sh`, not a local registry, and is
     retitled; `#oci_layout` code no longer overflows; divider subtitle lists the
     real sections; "Test:" prefix dropped; comparison-table rows softened; interop
     claim narrowed to what rules_img does. "78M" re-measured and kept: on ZFS,
     `du -L` shows compressed blocks (44M); the apparent size is 78M.
4. [x] The deck answers the 5 core how-to questions, each on a named slide:
   - **rules_oci steps** → "rules_oci, start to finish"
   - **rules_img steps** → "rules_img, start to finish"
   - **validate without a daemon** → "Validate images without the daemon"
     (`container_structure_test`, `driver = "tar"`)
   - **build layers + dedup** → "Architect layers by volatility" + "Action deduplication"
   - **shared layers + two-image sample** → "Shared layers: two images, one blob"
     (`//samples/shared_layers`)
   Trimmed to fit 90 min: merged the two hermeticity slides, cut ship-vs-source,
   demoted the closing self-build loop to a flourish.
5. [ ] **Dedicated Q&A session** — add an explicit Q&A slide/segment to the run
   sheet and budget time for it within the 90 min. Today Q&A topics only appear
   in the Module 5 closer (multi-stage builds, secrets injection, legacy
   migration, cross-arch); promote them to a structured session.

## Acceptance criteria

1. `bazel build //...` succeeds from a clean clone.
2. `bazel test //...` runs the image tests in parallel and passes.
3. `bazel run //slides:present` renders the deck.
4. `bazel run //benchmark:compare` (name TBD) produces the comparison.
5. The three takeaways in `PROPOSAL.md` each map to a real target in the repo:
   Slide-as-Code structure, the benchmark, and granular cacheable layers.

## 8. Presentation improvements (post-review backlog)

Suggestions and things to investigate from the workshop review, to make the
talk land better. These are presentation-quality items, distinct from the
build-correctness tasks above.

1. [ ] **Migration path beat** — a "convert an existing Dockerfile to Bazel
   incrementally" segment. Likely the highest-value addition for an intro
   audience and currently absent. Investigate where it fits the 90-min run
   sheet (short module vs. appendix vs. Q&A handout).
2. [ ] **Close the slide↔sample volatility gap** — the deck teaches the 3-way
   base/deps/app layer split (§2.9, Module 3) but the Python sample still ships
   a single `app_layer` (§2.6). Make the sample embody the taught split so the
   live cache-reuse demo matches the slide. Ties to §2.6.
3. [ ] **Reproducibility as a live demo** — promote "build twice, diff the
   digests, byte-identical" from a CI-only assertion (§5.4) to an on-screen
   moment. Decide if it's compelling for an intro or stays narrated.
4. [ ] **Settle the system-dependency payload story** — the distroless
   `graphviz` sample runs `dot` but can't render PNGs (plugin `config6` unwired,
   §2.11). Decide intent: (a) wire `config6` for hermetic render, (b) keep it as
   an explicit "where hermeticity gets hard" teaching moment, or (c) swap to a
   payload that better mirrors real-world messiness. Gather candidate examples
   from the Slack thread (Python packages needing extra system packages or
   ENV/config at runtime).
   - ↳ _Candidate payloads, grouped by the flavor of runtime non-hermeticity
     they expose (graphviz only shows "shells out to a binary"):_
     - _**Binary** (like `dot`): `pytesseract` → `tesseract` binary **+**
       tessdata files **+** `TESSDATA_PREFIX` (hits 3 flavors at once, OCRs an
       image → text); `ffmpeg-python`/`moviepy` → `ffmpeg`._ https://archive.org/details/carroll-1898-alice-in-wonderland/Carroll_1898_Alice_in_Wonderland/page/n1/mode/2up
     - _**Shared lib (dlopen):** OpenCV `cv2` → the famous
       `ImportError: libGL.so.1` on slim (fix: `libgl1` **or** switch to
       `opencv-python-headless`); WeasyPrint → Pango/cairo/gdk-pixbuf._
     - _**Data files:** fonts + fontconfig for matplotlib/Pillow text._
     - _**ENV/config:** `PROJ_LIB`/`GDAL_DATA` (pyproj/GDAL maps),
       `MPLCONFIGDIR`._
     - _Honorable mention: `ca-certificates` (HTTPS `CERTIFICATE_VERIFY_FAILED`
       on scratch) — ubiquitous but needs network, so a callout not a lab._
     - _Extreme: Playwright (`playwright install-deps` apt-installs ~60 libs) —
       rich but heavy for 90 min._
   - ↳ _Leaning: keep `graphviz` as the spine (self-build loop), add one
     contrasting sample — `pytesseract` (richest), OpenCV `libGL` (most
     relatable), or WeasyPrint (cleanest shared-lib story)._
5. [ ] **Live-demo resilience** — pre-pull / vendor base images and prepare an
   offline fallback (conference wifi risk). Re-check module timing: Module 3 is
   25 of 90 min; build in buffer.
   - ✅ **Partly done: the infrastructure no longer needs the network or a
     daemon.** The registry (`crane`) and the remote cache (`bazel-remote`) are
     pinned static binaries fetched by MODULE.bazel, so the push and caching labs
     run on a plane. See [`labs/remote/README.md`](labs/remote/README.md). Still open: vendoring
     the base image itself, and the timing re-check.
6. [ ] **Reconsider the "Slide-as-Code" framing** — the self-build loop is
   currently demoted to a flourish (§7.4) but is the deck's most distinctive
   hook. Decide whether to lead with it.
7. [ ] **Fold in Slack-thread feedback** — once the thread settles, work answers
   to the six open questions (scope, migration, payload, repro demo,
   oci-vs-img, live-demo risk) back into the deck and run sheet.
8. [x] **Investigate: when is `rules_img` faster than `rules_oci`?** —
   characterize the conditions where the tar-less path wins (large layers,
   tar/compression cost, incremental Go-based loads, push-time dedup), with
   numbers if possible. Feeds the "rules_oci vs. rules_img" slide (§2.4).
   - ✅ Measured via `:compare` + `:push_compare` (see §4.1). Finding:
     single-image build/push gap is small (and rules_img isn't automatically
     faster); the dramatic win is layer **dedup** (~2.5× on a 2nd shared-layer
     push), which is content-addressed and ruleset-agnostic. Slide now cites it.
9. [ ] **Investigate: build/push/run effects of Bazel + `rules_img` +
   `rules_oci`** — map each ruleset's impact across the three phases (build,
   push, run/load a Docker image): what's faster, what's daemonless, what
   changes for the local dev loop. Turn it into a comparison table for the deck.

## Open decisions

- Sample app language/runtime (keep it tiny to keep build times honest).
- Whether `samples/img/` ships in v1 or is added after the `rules_oci` path
  is solid.
- Fix distroless render (`config6`) vs. keep the gap as a teaching moment vs.
  switch payload (see §8.4).
- Whether a Dockerfile→Bazel migration beat fits inside the 90 min (see §8.1).
- Show both `rules_oci` and `rules_img`, or cut one to lower intro-level
  cognitive load (see §8.6 / §7.4).
- Adopt the three-level narrative spine (§9) as the deck's backbone vs. the
  current 6-module format (§7)?
- Keep `graphviz` self-build loop as the closer while `pytesseract` carries
  Level 2, or retire one?

## 9. Narrative spine: three levels of hermetic complexity (Python)

A proposed restructure: frame the talk around three escalating real-world
Python examples, each exposing a deeper layer of the hermeticity problem.
Doubles as a diagnostic mental model — "is this a compiler, an OS-dependency,
or a hardware problem?" (maps to takeaway #3). Supersedes the feature-tour
framing; reconcile with §7.

**Level 1 — The Build-Time Trap** (example: `cryptography`; `numpy` as footnote)
- Standard C/Rust extensions: wheel caching, deterministic per-arch selection.
- ↳ _Refine: with `rules_python`, Bazel **consumes** pinned + hashed prebuilt
  manylinux wheels — it does **not** compile them. The real trap is the
  **sdist fallback** (no wheel for the platform → `pip` builds from source with
  the host compiler/headers = non-hermetic). "Cross-compilation ARM vs x86" is
  really **per-arch wheel selection** by platform tag, not C cross-compile._
- ↳ _Use `cryptography` (Rust + OpenSSL, vivid/recent) over `numpy` (modern
  wheels bundle OpenBLAS → already a clean case)._
- ↳ _New sample needed under `samples/`._

**Level 2 — The "Ghost" Runtime Trap** (example: `pytesseract`)
- Pure-Python wrapper that secretly shells out to a system binary →
  motivates bundling OS deps with `rules_distroless` + `rules_oci`.
- ↳ _Already the family of the existing `graphviz` sample (§2.9/§2.11);
  `pytesseract` is a sibling carrying binary **+** tessdata data files **+**
  `TESSDATA_PREFIX` (three ghosts). Linux binary is `tesseract` (not `.exe`)._
- ↳ _Hermetic chain: `rules_distroless` fetches the `.deb` → `rules_oci`
  layers it → `container_structure_test` catches the ghost before prod._

**Level 3 — The Hardware Wall** (example: `pyopencl`)
- The limit of hermeticity: OpenCL needs host GPU drivers to execute; how to
  safely "punch holes" for hardware access.
- ↳ _Demo-ability: no GPU at the venue → use **POCL** (`pocl-opencl-icd`), a
  CPU-based OpenCL ICD from apt, so `pyopencl` runs hermetically on CPU with no
  host driver. The true wall is the GPU ICD/driver — must match the host kernel,
  so it **can't be baked in portably**; it's a declared runtime contract
  (`/dev/dri` mount, NVIDIA Container Toolkit), the one deliberate break in
  hermeticity. Build stays hermetic; only device binding is the escape hatch._
- ↳ _New sample needed under `samples/`._

**Takeaways:** (1) how Bazel caches Python wheels and OCI image layers;
(2) why `pip` is blind to system deps and how to fix it in CI/CD
(`rules_distroless` + layering + structure tests); (3) a mental model for
classifying a failure as compiler vs. OS-dependency vs. hardware.

**Open scope question:** Levels 1 + 3 as tighter "show & explain" beats with
Level 2 as the full hands-on lab, to fit 90 min (see §7 timing).

## 10. Self-guided labs (test-driven)

Self-guided labs: each lab is a set of failing tests the attendee turns green at
their own pace, going as far as they want. Every task is a win on its own and
nobody is gated, so a mixed entry-level/advanced room self-sorts without anyone
waiting. Builds on the three-level spine (§9) and reuses the repo's existing
test types (`container_structure_test` `driver = "tar"`, `build_test`,
`py_test`).

**Tasks per level** (each = a failing test to turn green; ★ = optional stretch):

| Level | Task 1 | Task 2 | ★ Stretch |
|---|---|---|---|
| 0 · Dockerfile → rules_img (graphviz) | translate `FROM` + `ENTRYPOINT` (structure test) | `dot` as a pinned bookworm layer | render the PNG: apt layers skip postinst (`dot -c`) |
| 1 · Build-time (cryptography) | pin the wheel; `py_test` import passes | the wheel is inside the layer (`image_layer_test`) | diagnose the sdist fallback; per-arch wheel selection |
| 2 · Ghost (pytesseract) | structure test: `tesseract` binary + data present | `TESSDATA_PREFIX` metadata test | OCR runs; reproduce the `mergedusr` silent failure |
| 3 · Hardware (pyopencl) | POCL CPU ICD present (structure test) | — | run a kernel on CPU; `/dev/dri` / NVIDIA-toolkit + why drivers can't be baked in |

**Mechanics (under `//labs/...`):**
1. [x] Each task is its own target. Learners run tasks **by name** (`progress`
   lists them); skeleton tests are tagged `manual` so `bazel test //...` skips
   them and only the green `solution/` targets gate CI.
2. [x] **Guide**: `bazel run //labs:progress` lists every lab and task with its
   exact command.
   - ✅ **Artefact:** [`labs/progress.sh`](labs/progress.sh) → `//labs:progress`.
3. [x] **Skeletons, not blanks**: each level's `BUILD.bazel` has the boilerplate
   done and a `# TODO(task N)` at the one decision that teaches the lesson.
4. [x] **`//labs/levelN/.../solution`** reference targets — green and CI-gated.
5. [x] **One README per lab folder**: goal, start command, tasks, and collapsed
   answers — self-contained, readable on GitHub without opening other files.
   (Replaced the per-level `HINT.md`s; `REMOTE.md` moved to `labs/remote/`.)
6. [~] **Pre-generated apt locks** checked in (no network mid-lab);
   ✅ [`tesseract.lock.json`](labs/level2_ghost/tesseract.lock.json),
   [`pocl.lock.json`](labs/level3_hardware/pocl.lock.json),
   [`labs/requirements_lock.txt`](labs/requirements_lock.txt). _Venue base
   pre-pull/vendoring still open (ties to §8.5)._
7. [x] **Deck concept → exercise map** in [`labs/README.md`](labs/README.md):
   every concept on the slides points at a lab task. Gaps filled with playground
   tasks (manifest/config, one base N images, distroless, Docker tax), a Level 2
   `mergedusr` stretch, and a `crane` read-back task in the remote lab.
   - ✅ Level 0 ([`labs/level0_graphviz/`](labs/level0_graphviz/)) added for the
     deck's graphviz sample: reuses `//samples/python:app_layer`, with its own
     bookworm `graphviz_lab_apt` (the sample's lock pins bullseye, for scratch).
     _Open: generate graphviz's plugin config at build time so no `dot -c`._
   - ↳ _Open: Level 1's arm64 wheel-selection stretch has no command — the repo
     defines no `linux_arm64` `platform()` target to pass to `--platforms`._

**Built & validated (2026-06-18):** all three levels under
[`labs/`](labs/) — `level1_buildtime` (cryptography), `level2_ghost`
(pytesseract + `tesseract_apt`), `level3_hardware` (pyopencl + `pocl_apt`), each
with a skeleton + `solution/` + `README.md`, plus [`labs/README.md`](labs/README.md)
and a dedicated `labs_pypi` pip hub. Verified: each skeleton task is RED and each
solution GREEN; `bazel test //...` passes (15 tests) and `bazel build //...`
is clean.

## 11. rules_img-only migration (supersedes the dual-ruleset framing)

Decision (2026-06-24): the talk teaches **`rules_img` only**. `rules_oci` is
removed repo-wide; the `Dockerfile` stays as the sole "before/non-hermetic"
contrast. This supersedes the "two rulesets / three philosophies" framing in
§1–§9 (those sections are kept as build history).

- [x] Convert every image to `rules_img` — `image_manifest` + `layer_from_tar`
  + `image_load`/`image_push`. Done in `samples/python`, `samples/distroless`
  (scratch via a `platform` target), `samples/shared_layers`, and all six lab
  BUILDs. Daemonless `container_structure_test` now reads `image_load`'s
  `tarball` output group (needs `layer_handling = "lazy"` on the base pull).
- [x] **Delete** `samples/rules_oci/`, `samples/rules_img/` (folded into
  `samples/python`), and `benchmark/oci_vs_img/` (its purpose was the oci↔img
  comparison, now moot; dedup is still proven by
  `//samples/shared_layers:digests`). Closes/retires §4.1's image-build-time
  benchmark and §8.8's "when is rules_img faster" investigation.
- [x] `MODULE.bazel`: drop `rules_oci` + the `oci.pull(python_base)` extension;
  base now via `images.pull(python_base_img, layer_handling = "lazy")`.
- [x] Slides + `content.md` + README + `samples/README.md` + PROPOSAL scrubbed
  of `rules_oci`; deck table is now Dockerfile vs `rules_img`.
- Open decision (resolved): "show both rulesets vs. one" → **rules_img only**.

## 12. Presentation review actions

Talk content & delivery follow-ups from a review pass (see also the slides).

### Title & framing
- [ ] Rename to **"High-Velocity Composition at Scale"**; lead with the explicit
  core *Docker build reproducibility*; "Building Without Bytes" as subtitle.
- [ ] Add a recurring "how it ties together" beat so modules read as one story.

### Delivery & pacing
- [ ] Cover less, with more confidence; slow down and articulate.
- [ ] More interactive; budget enough time for the core Docker concepts.
- [ ] "For-dummies" command explainers — one slide per Docker lifecycle stage,
  walked start-to-finish (build → run → test → push).

### Wayfinding
- [ ] "Clone to start" GitHub link on the opener + repo link in every slide footer.

### New content slides
- [ ] Closing slide on **Remote Build Execution (RBE)**.
- [ ] **container_structure_test** explainer — what it is, how to use it, what
  it can test.
- [ ] Illustrate **shared layers** → how it maps to BUILD code.
- [ ] Diagram — **limits of the Bazel sandbox** (GPU vs CPU; shift testing left).
- [x] "Further resources" slide — **done, folded into "The lineage: three
  generations"** (Module 1) rather than a separate slide, so the history lands
  where the three rulesets are introduced. Real, curated links, no placeholders:
  Alex Eagle's *Bazel and Docker with `rules_oci`* (Bazel Community Day, 2023) and
  Malte Poll's *`rules_img`: A Ground-Up Redesign* (BazelCon 2025) as committed
  thumbnail citation cards, plus *Migrating away from rules_docker to rules_oci*
  as a text link on the `rules_docker` row. Provenance: `PROMPTS.md` §"Reference
  cards"; details in §13 below.

### Bazel × Docker — when to use which (new section)
- [ ] Bazel-in-Docker vs Docker-in-Bazel use cases (dev container → `bazel run`;
  `bazel build` → docker env; images for remote workers; the DinD problem).
- [ ] 4-usage comparison diagram (isolated dev env vs delivery packaging vs
  isolated tests vs building inside Docker).

### Dependency packaging deep-dive
- [ ] Outline the limits of `rules_distroless`; how to get apt packages; how to
  get pip packages; creating custom tar layers.
- [ ] Translating an arbitrary Docker `RUN` into Bazel — the fundamental hard
  problem; what's hard to translate and the boundaries of doing so.

### Interactivity for GitHub Pages viewers (future evaluation)
- [ ] Evaluate adding an interactivity layer to the **current Slidev deck**
  (keep Slidev — wins on PDF export, the Bazel self-build/transclusion thesis,
  and looks; see below). Static Pages has no backend, so real `bazel`/`docker`
  can't run from the hosted deck — the lever is an execution path, not the tool:
  - [ ] **asciinema** casts of the real `bazel`/`docker` runs — replay live,
    copy-pasteable, zero backend; embed on the command/demo slides.
  - [ ] **"Open in Codespaces / Binder / Gitpod"** button so remote viewers can
    actually run the labs in a real cloud env.
  - [ ] (niche) JupyterLite/Pyodide to run only the pure-Python graphviz DOT
    generation in-browser — not bazel/docker.
- [ ] ↳ _Decided against **RISE (Jupyter + reveal.js)**: its live-kernel edge is
  for Python, not shell, doesn't work on static Pages anyway, and would cost the
  PDF fallback + `<<< @/...` transclusion + self-build invariant. Keep Slidev._

### Follow-up (outside the deck)
- [ ] Blog post on automatic layer creation.

## 13. Deck image assets (antique-cookbook illustrations)

The deck uses hand-generated 19th-century-cookbook-style illustrations (watercolor
"plate" look on aged cream paper) plus an aged-paper slide background. Prompts and
the house style live in [`slides/images/PROMPTS.md`](slides/images/PROMPTS.md);
each `<!-- IMAGE: … -->` marker in `slides/slides.md` names the target file.

- [ ] **Generate & test all illustrations** first (one per `slides/images/*`
  marker), wiring each into its slide with `class="… plate"` (soft radial mask)
  and eyeballing fit in the exported PDF. _(In progress: `bechamel-to-sandwich`
  and `paper-bg` done; `croque-shared-layers` still to generate — see below.)_
- [ ] **Optimize deck images (do this LAST, in one pass, after all art is
  approved).** Raw AI exports are huge (e.g. `bechamel-to-sandwich.png` ~9 MB,
  `paper-bg` ~6.5 MB) — far too heavy for a deck + PDF. Right-size every
  `slides/images/*` raster (longest side ≈1600px; background ≈1920px) and convert
  to **WebP** (`quality≈80–82`); expect ~9 MB→~300 KB and ~6.5 MB→~250 KB with no
  visible loss. Then repoint the `src`/`url()` in `slides.md` + `style.css` to the
  `.webp` files and `git rm` the heavy originals.
  - Tooling: **Pillow (with WebP) is available** via `python3`; no
    `cwebp`/imagemagick/pngquant installed. A short `python3` + Pillow script
    (`Image.open → resize(LANCZOS) → save('WEBP', quality=…)`) does it.
  - Rationale (SVG was asked): SVG can't lighten these — the watercolor/paper art
    is inherently raster (SVG would embed the bitmap or trace away the look). WebP
    + right-sizing is the lever; keeps transparency for the divider/diagram plates.
- [ ] _(Optional, later)_ a dark aged-linen texture for the section
  dividers/cover to match the paper on light slides.
- [x] **Review the "Two ideas to keep: CAS & the OCI standard" slide** — done. It
  was collapsed to a single idea, "**The same layer, only once**": content
  addressing explained as a hash table (digest = key, blob = value), with the
  manifest/config/index taxonomy moved into the `content.md` speaker script as an
  "if asked" aside. The seam is now motivated from the previous slide — "A
  sandwich of tars" ends on the shared-prefix hinge ("same ingredients, same order
  → the same sandwich, so far"), which the next slide answers in its first
  sentence. Also standardized on the precise term *image manifest* at first
  mention.
- [x] **Generate `croque-shared-layers.png`** (prompt in `PROMPTS.md`) — done and
  wired; `oci-manifest-cas.png` deleted. Two post-processing steps were needed and
  are worth reusing for the remaining art:
  1. **Key the checkerboard to real alpha.** It generated *opaque*, with the
     transparency checkerboard painted in as pixels (white + `#cccbc9`). Fixed with
     a pure-PIL pass (no numpy/scipy in this env): mark pixels that are achromatic
     (`max-min ≤ 16`) **and** bright (`min ≥ 178`), then scanline flood-fill inward
     from the borders and zero their alpha. The flood fill is the important part —
     a plain colour key would also punch out the egg white and the label boxes;
     filling only from the edges leaves anything enclosed by ink intact. Result:
     74.7% cleared, no halo.
  2. **Crop to the alpha bbox.** It came with fat dead margins (178px right, 141px
     top); cropping took the aspect 2.49 → 2.77, so the plate renders ~12% larger
     inside the same vertical budget — which is what made the `sha256:` tags
     legible at `max-h-64`.
  Digests verified hex-valid and the egg's is distinct. Still **4.6 MB PNG** — must
  go through the §13 WebP batch below.
  Design decisions worth keeping if it is ever re-generated: the egg stays its
  natural golden colour and is marked by a lime **annotation** ring rather than
  being tinted lime — a green egg reads as spoiled and fights the plate's
  food-realism, so this deliberately departs from the tint-the-difference
  convention used in `one-base-n-images`; the shared stack is washed in quieter
  sepia so the saturated egg pops instead. The per-layer `sha256:` tags (styled as
  an antique specimen catalogue number) are what make the plate show *why* dedup
  works — same bytes → same name — and not merely that it does; the prompt
  constrains them to six characters from `0-9a-f` because image models mangle long
  alphanumeric strings and a Bazel audience will squint at a non-hex digest.
  - Note: `sandwich-layers.png` on the preceding slide is a panino *caprese*, so
    the two slides show different sandwich species back to back. Judged
    acceptable (the croque pair reads as "two different images", and croque
    monsieur is already the cover art). If the seam feels jolty when rehearsed,
    the fallback is to make the pair caprese too — same bread, one adds prosciutto.
- [x] **Generate `without-bytes.png`** (prompt in `PROMPTS.md`) — done and wired
  into the "Building Without Bytes" slide at `max-h-48`, replacing the `img-slot`
  placeholder; the slide's closing punchline moved *below* the plate as a
  `text-sm` caption so the art gets the vertical budget. Fit checked in the
  exported PDF (p. 35): `max-h-56` collided with the footer, `max-h-40` wasted
  ~70px — `max-h-48` is the fit.
  - **The magenta key only cleared 10.6%**, because the generator ignored the
    "no paper" instruction and baked a **cream plate with an ornamental frame**;
    the flood fill got the magenta field around it and nothing else. Crop to the
    alpha bbox took 3264×1312 → 3172×1207 (aspect 2.49 → 2.63). No halo after a
    despill pass (17.7k edge px: `b > g and r > g` ⇒ pull blue down to green,
    safe because the palette is sepia, `r ≥ g ≥ b`).
    Consequence: unlike `croque-shared-layers`, this plate does **not** dissolve
    into the slide's aged paper — it reads as a mounted card. Judged acceptable
    (the frame is handsome and the tone matches), but it's the reason `.plate`'s
    radial mask was **not** applied: masking a drawn frame fades it unevenly.
  - **Known flaws:** several digest cards repeat the same `sha256:a1b2c3d4`
    instead of being distinct, and a few incidental labels are mangled
    ("PRESEESY", "Preg: Black Garlic Aioli", "imperand Truffles"). At `max-h-48`
    none of that text is legible — what reads is the *shape* (BUILD → REGISTRY →
    RUN over a stocked CAS vault), which is the slide's whole point. **The wired
    asset is usable as-is**, so the slide is not blocked.
  - **⚠️ Superseded prompt — re-roll when convenient.** The checked-in PNG was
    generated from the *old* `without-bytes` prompt, which asked for "digest
    reference cards" and "layer blob boxes in a CAS vault" — abstract diagram
    nouns with no food in them. That is diagnosed as the root cause of every flaw
    above, and the prompt has since been rewritten (see the next entry). The new
    one asks for a real kitchen: paper dispatch dockets travelling prep bench →
    order rail → table, over a cold larder of ham, béchamel, pickles, herbs and
    gruyère that never moves. Re-generating from it should also fix the baked
    frame, since the frame/title ban is now explicit.
  - **8.3 MB PNG** — must go through the §13 WebP batch below.
- [x] **Rewrite the abstract diagram prompts around food** — done, in
  [`slides/images/PROMPTS.md`](slides/images/PROMPTS.md). The section opens with a
  house rule, **"Draw food, annotate computing"**: the drawn subject must be a
  dish, an ingredient, a larder shelf, a docket rail or a brigade range, and the
  computing idea may enter only as *annotation* (hand-lettered labels, leader
  lines, lime brackets, catalogue tags). Diagnosis: the two prompts that produced
  good art (`sandwich-layers`, `croque-shared-layers`) name actual food; the rest
  reached for "blob", "box", "node", "hub-and-spoke schematic" and got mush. The
  slides had the vocabulary all along — the remote-cache slide already says
  *commissary*, *brigade of line cooks*, *one shelf, many dishes* — so the prompts
  had simply drifted from their own slides.
  - Five rewritten: **`one-base-n-images`** (one prepared bread+béchamel+ham
    foundation → five finished sandwiches differing only by topping, numbered
    I–V and trailing off to "N"); **`without-bytes`** (dockets travel, the larder
    never moves); **`remote-cache-rbe`** (a central commissary larder feeding a
    domestic bench = laptop, a hotel pass = CI, and a brigade range of five line
    cooks = RBE workers); **`docker-lifecycle`** (the *same* sandwich round a ring:
    prep bench → diner → dispatch window → delivery cart); **`catering-vs-onepot`**
    (a fused cast-iron gratin vs. a steam-table line where only the last tray is
    swapped). `sandwich-layers`, `croque-shared-layers` and `shared-pantry` were
    already food-grounded and are untouched.
  - Two guards added to every rewritten prompt, both from observed failures:
    **"and NO other text anywhere on the plate"** after an explicit label list
    (an unconstrained plate invents a garbled title), and an explicit ban on the
    **card, plaque, border rule, frame, cartouche and ribbon banner** (not just
    paper texture — the framed cream card is why the magenta key cleared 10.6%).
  - **Not yet re-generated:** this is a prompt-only change. `without-bytes.png` is
    the one affected asset already in the tree; the other four were never
    generated, so they are simply better specified now.
- [x] **Generate `one-base-n-images.png`** — done and wired, and it **validates the
  rewrite**: one prep tray holding the bread+béchamel+ham foundation on the left,
  leader-lined out to five open sandwiches numbered I–V differing only in the
  topping, trailing off to "… N". Legible labels, no invented title, no baked
  frame, a genuinely flat field — every failure mode of the old `without-bytes`
  prompt, absent. Wired at `max-h-48` with the "at scale" line moved below the
  plate; fit checked in the exported PDF (p. 37), where `max-h-56` and `max-h-52`
  both crowded the footer.
  - **The keying recipe needed an upgrade**, now written up in `PROMPTS.md`
    §"Producing the alpha". Binary key + despill (what `without-bytes` got) pulled
    the lettering and the annotation arcs to muddy rose. The fix is a **soft**
    key: take the foreground colour from a fully-opaque pixel within ~3px and
    solve alpha by least squares; fall back to an analytic un-blend only for
    hairlines that have no opaque core. Both halves are load-bearing — the core
    rule alone erased every numeral and caption on the plate, and the analytic
    rule alone re-roses anything green. Result: 49% cleared, no halo, 2.49 → 2.74.
  - **Measure the field, don't assume it.** It came back on `(255, 71, 253)`, not
    `#FF00FF`. The key is written against a sampled `B` and a `min(r,b) - g` spill
    score, so an off-nominal field costs nothing.
  - **Never judge colour against the magenta.** The arcs looked sage; measured,
    their cores were `(169, 146, 130)` — a taupe, off-palette. Simultaneous
    contrast, not a keying artefact. Fixed without a re-roll by recolouring the
    five arcs to lime `#7CB342` via connected components (≥300px, which keeps the
    speckle on the bread and mushrooms out of it — tinting food green is banned).
  - **Two cosmetic misses, judged not worth a re-roll:** the prompt asked for a
    sardine and the generator drew a **pineapple ring** on IV (a Hawaiian joke the
    plate carries fine), and the numerals I–V are drawn **twice**, above and below
    each sandwich. Neither is legible enough at `max-h-48` to distract.
  - **1.6 MB PNG** — must go through the §13 WebP batch below.
- [x] **Generate `catering-vs-onepot.png`** — done and wired. Left, one fused
  cast-iron bake with a spoon breaking the crust ("re-cook everything"); right, a
  steam-table line of `base` / `deps` / `app` trays with only the `app` tray lifted
  out on a cook's hands ("remake one tray"), bracketed in lime. Second confirmation
  that the food-first rewrite works: correct labels, no invented title, no garbling.
  - **Wired at `max-h-44` with the slide restacked.** The closing paragraph
    duplicated the plate's own two labels, so it moved *below* the art and was cut
    to one line ("One dish, and every edit re-cooks the whole thing — run a
    catering line and you remake only the tray that changed."). Without that trim
    the art is stuck at `max-h-40` behind a code block and reads too small; checked
    in the exported PDF (p. 26), where `max-h-52` pushed a two-line caption off the
    slide and `max-h-48` sat ~15px off the footer.
  - **This one needed the BINARY key, not the soft one.** It came back as a cream
    card in a magenta frame (same as `without-bytes`), and its field carries a
    gradient toward the right edge — enough that the soft `a = 1 - spill/span`
    rule read the far corner as ~28% opaque and left a smear. With no line art
    sitting directly on the field there is nothing for the soft path to rescue, so
    a plain border-seeded fill to `alpha 0` is both correct and simpler. **Rule of
    thumb for the rest of the art:** soft key when the ink sits on the magenta
    (`one-base-n-images`), binary key when the generator mounted the plate on a
    card (`catering-vs-onepot`, `without-bytes`). 14.1% cleared, 1.79 → 1.83.
  - **Unrequested but kept:** a lime "UPDATE:" callout pointing at the swapped
    tray, which the prompt never asked for and which reads correctly. The word
    "app" is drawn twice (on the lifted tray and the one below it) — not legible
    at `max-h-44`.
  - **3.6 MB PNG** — must go through the §13 WebP batch below.
- [x] **Generate `remote-cache-rbe.png` and refactor its slide** — done, and it is
  the **best plate of the batch**: ink and wash directly on a flat field, no cream
  card, no ornamental frame, no invented title, and every label legible — a
  commissary pantry of tagged jars at the centre, one green jar leader-lined out
  to a domestic cook at his bench, a hotel pass hung with tickets, and a range of
  five line cooks working in parallel.
  - **The slide lost its three bullets.** They described exactly what the plate now
    shows, so "The pantry, chain-wide" is one framing line + the plate + the
    `--remote_cache` snippet + two lines of payoff, at `max-h-60` (checked in the
    exported PDF, p. 37). What survived is what a picture cannot say: the flags,
    and *why sharing is safe* — same digest ⇒ same bytes.
    - The **"one shelf, many dishes"** bullet (sandwich · distroless · salad) was
      **dropped, not moved**: with "One base, N images" now running two slides
      earlier, it was making the same point twice. If distroless needs a
      name-check here, that bullet is the thing to restore.
    - The generator labelled the domestic bench **"domestic cook"**, not "laptop"
      as the prompt asked, so the slide's framing line now does the mapping
      explicitly: domestic cook = your laptop, hotel pass = CI, brigade = RBE
      workers.
  - **Two corrections to the alpha recipe**, both now in `PROMPTS.md`:
    1. **Seed the flood fill from the field's own colour, not just the borders.**
       This plate was full of background *pockets* fenced in by ink — under the
       ticket rail, beside each cook's arm — which a border-seeded fill cannot
       reach, so they survived as solid magenta blocks. Seeding from any strongly
       magenta pixel clears them, and it is safe precisely because magenta is
       absent from the palette: a cream egg white has `spill ≈ 0` and never seeds.
       The fill still earns its keep — it is what stops a global key eating that
       egg white.
    2. **Despill globally afterwards:** `b > g and r > g ⇒ b = g`. The palette is
       sepia and green (`r ≥ g ≥ b`), so blue above green is always magenta cast,
       and lime is untouched because its `g > r`. This is what cleared the pink
       haze out of the watercolour shadows under the benches (91k px).
  - **6.9 MB PNG** — must go through the §13 WebP batch below. Four plates are now
    unoptimised in-tree and the exported PDF has gone 37 MB → 56 MB; the WebP pass
    is the thing that brings it back down.
- [x] **Generate `docker-lifecycle.png` and refactor its slide** — done. One
  sandwich goes round a ring of four kitchen scenes: hands assembling it at a prep
  bench (**build**), a waiter setting it before a diner (**run**), a dispatch
  window handing it out boxed and wax-sealed (**push**), a delivery cart at
  another kitchen's back door with the same box (**pull**). All four labels
  legible; keyed clean (45.9% cleared, 1.61 → 1.57).
  - **The four verb cards were only *half* redundant.** The ring shows the verbs
    and the loop, so the icons and the `Dockerfile → image` glosses went. But the
    cards also carried the slide's actual point — *which* verbs are already done —
    and the plate cannot say that. So the 4-column grid became a two-column
    layout: the ring on the left, and a compact right-hand legend that keeps the
    `verb-done` / `verb-now` split and every progress tag (`Modules 0–2 ✓`,
    `Module 1 ✓`, `this module`, `Module 4`). Checked in the exported PDF, p. 31.
  - `grid-cols-[1fr_auto]` centred the plate inside a too-wide column and left a
    hole between it and the legend; `grid-cols-[auto_auto] … justify-center` sizes
    both columns to content and centres the pair.
  - **Cosmetic miss, not worth a re-roll:** the word "build" is drawn **twice**,
    once on the ring at the top and once again inside it. Not legible at
    `max-h-60`.
  - **6.3 MB PNG** — §13 WebP batch. Five plates now unoptimised in-tree; the
    exported PDF is 61 MB (from 37 MB).
- [x] **`sandwich-no-bread` is a 6:1 party-sub banner, not a 5:2 panel** — prompt
  rewritten, generated and wired. Re-cast the subject as one very long hero roll
  with its halves lifted away, running unbroken end to end, because the distroless
  slide has horizontal room and no vertical room: `h1` + lede + the ~150px
  `#distroless` block + a caption already fill the 552px canvas, so a 5:2 panel
  would sit centred with dead space either side. The slide's copy was trimmed
  ~100px first (lede folded to three lines, the two trailing prose blocks merged
  into one `text-sm` caption) to clear the band. It must **not** read as a row of
  separate sandwiches; that motif is `one-base-n-images`'.
  - Wired `w-full h-auto object-contain` and **not** `max-h-*`, so it spans the
    column: 5088×832 keyed and bbox-cropped to **4746×727** (aspect 6.12 → 6.53),
    rendering **906×139** in the 906px content column. Measured in the browser at
    1024×576: image `y 405.3 → 544.0`, slide overflow **0**. Three slides already
    sit lower (43 at 551.4, 4 at 549.3, 12 at 545.1), so this is inside house
    norms — but it is the tightest of the plates, and the bread's lower-left tip
    grazes the `deck-logo` box by ~3px. The *ink* clears the TWEAG wordmark;
    checked in the exported PDF, p. 27. If it ever needs slack, take it off the
    width (`w-[94%] mx-auto` → bottom 535.7), not the copy.
  - **No `.plate`.** Unlike `without-bytes`, the generator honoured the no-paper
    instruction, so the key cleared the field outright and the art dissolves into
    the slide's paper on its own. The radial vignette would only eat the ends of
    a strip this wide.
  - **The field was not flat** — spill 222 (top-left) → 191 (bottom-right). A
    single global `B` per the recipe left residue as opaque as `a=80`, which no
    step-4 floor can clear without eating hairline art. Fixed by estimating `B`
    on a 64px grid (mean of each cell's purest field pixels, bilinearly
    interpolated) and keeping the floor at 32, plus a component prune for the
    speckle that survived. Both are now written into `PROMPTS.md`'s "Producing
    the alpha" as steps 4/4b, since every remaining plate will hit this.
  - **7.2 MB PNG** — joins the §13 WebP batch. Original generator output backed up
    outside the tree before keying (it was untracked; git could not have
    recovered it).
- [x] **Review pass on slides 11–24 (Module 0 tail → Module 1)** — done. Fourteen
  notes across four problem kinds: dead space/placeholders, invented or truncated
  code, unexplained mechanics ("where does `apt.install` come from?"), and
  leftovers from earlier iterations. Outcome: every code block on these slides is
  now either **transcluded from the repo or verbatim-correct**, and both
  placeholders are resolved.
  - **`MODULE.bazel` is now a transclusion source** (`#region base_pull`,
    `#region apt_ext`), which closes the `apt.install` drift risk logged above.
    Wiring: root `BUILD.bazel` gained `exports_files(["MODULE.bazel"])` ＋
    `copy_to_bin(name = "slides_inputs")`, and `//slides` adds `//:MODULE.bazel`
    to `srcs` and `//:slides_inputs` to the build — so `../MODULE.bazel` resolves
    from `bazel-bin/slides` the same way `../samples/...` already did. Verified
    before any layout work: the digest and the `rules_distroless` extension string
    both appear in `//slides:build` output, and the regions are bounded (nothing
    from the npm stanza leaks in).
  - `#region base_pull` is deliberately a **tight 10 lines** — the `layer_handling
    = "lazy"` rationale comment was moved *above* the region marker, and the slide
    explains "lazy" in prose instead. A 13-line region did not fit the vertical
    layout.
  - **Slide 18 broke the `.xlate` grid and went vertical** (`FROM` → ↓ → the
    full-width pull → the one-line consuming side). Three columns gave the 80-char
    digest less than half a slide. **Decision B1 stands** — checked in the exported
    PDF: the digest sits on one line and the slide fits. The B2 fallback
    (hand-write the block, revert the wiring) was **not** needed.
  - **Drift closed:** `/tmp/out.png` on the `ENTRYPOINT` slide → the real
    `/tmp/supply_chain.png` (the Dockerfile was already correct — the plan's note
    that `Dockerfile:20` was wrong did not hold); `entrypoint = ["/app/app"]` with
    its args dropped → the whole real `image_manifest` call; `apt.install`'s
    attribute order (the slide had `manifest` before `lock`, the file has `lock`
    first); the invented two-line `graphviz` snippet → `app.py#render`; and the
    hand-condensed build snippet → the live `BUILD.bazel#image` region.
  - **Slide 14 now shows the real console output** with `dot` off `PATH`, captured
    byte-for-byte by running the built launcher under a stripped `PATH`. It's a
    graceful `[skip]`, not a crash — framed that way on the slide.
    - Two lines in `app.py`'s `#region render` were reflowed (a wrapped string
      literal and a wrapped `graph.render(...)` call) so the region fits its
      column at 66 columns. Behaviour is unchanged — verified the stderr text is
      identical before and after — and the file is now more PEP-8 conformant than
      it was. **Reformat the source, don't retype it on the slide.**
  - **`.step-code`** added next to `.step-note` (one line per roadmap tile, naming
    the target form). **`.code-sm`** added for columns where a real region is too
    wide: it sets `--slidev-code-font-size` rather than `font-size`, because
    `.slidev-code` declares that property `!important` and a plain rule silently
    loses. Worth remembering for any future code-density fix.
  - **The ①②③④ lifecycle numbering is dropped deck-wide** (decision C1). It was
    out of order — ① Build, ② Run, then ④ Push in Module 3 and ③ Test in the
    Appendix — and "Docker's four verbs" already establishes the loop. Each stage
    now has a takeaway-first title plus a neutral `.step-kicker` chip
    (`build` / `run` / `push` / `test`): "Assemble, don't run", "Load it like any
    other image", "Push — only the changed blobs", "Test:
    `container_structure_test`". `content.md` mirrors all four.
  - **Slide 15's `img-slot` is gone**, which also ticks §12's "curate the actual
    links … don't ship placeholders": two committed YouTube thumbnails as
    citation cards (provenance recorded in `PROMPTS.md` under "Reference cards" so
    nobody tries to regenerate them), plus a plain text link for the
    `rules_docker` migration talk.
  - **Slide 16 lost its numbered list and its code block** — the list was a
    roadmap for the next six slides and slide 17 already *is* that roadmap, and the
    `#image` transclusion moved to the "Assemble, don't run" slide where the
    command that produces it lives. What's left is one idea in Malte's framing:
    *build time produces metadata, run time moves bytes*.
  - Answers that were missing and are now on the slide (with the long forms in
    `content.md`): what `apt.install` actually *is* (a tag class on a module
    extension, running in the loading phase); the full `requirements_lock.txt` →
    `pip.parse` → `requirement()` → runfiles → one layer chain; and the correction
    that **`rules_img` does not generate the launcher** — `py_binary` makes
    `/app/app`, `pkg_tar` ships it, and `entrypoint` is only a pointer in the OCI
    config JSON.
  - Two premises in the review were checked against the repo and **did not hold**:
    `aspect_rules_py` is not a dependency of this workspace (no `bazel_dep`, no
    `py_image_layer`; deps reach the layer via plain
    `pkg_tar(include_runfiles = True)`), and the Dockerfile's render path was
    already `/tmp/supply_chain.png`. The `aspect_rules_py` comparison lives in
    `content.md` as an aside, not on a slide.
  - `@iconify-json/carbon` ＋ `@iconify-json/ph` are now **explicit
    `devDependencies`** in `slides/package.json` (they were only transitive Slidev
    deps, so leaning harder on icons could have broken on a Slidev bump).
    Re-locked via `npm install --package-lock-only` then `bazel run @pnpm//:pnpm --
    --dir=slides import`; carbon moved 1.2.23 → 1.2.26, single version, no
    duplication. `//slides:build` still passes.
  - **`bench-to-plate.png` — generated and wired.** (Renamed from
    `precise-recipe.png`: that prompt was written for the "So… cook with Bazel"
    slide, which `b1ffb76` folded into the Module 0 closer, so it was orphaned;
    the new portrait prompt supersedes it in place under "Metaphor scenes" in
    `PROMPTS.md`.) It now sits in the centre `auto` track of the closer's
    `grid grid-cols-[1fr_auto_1fr]` as a plain
    `<img class="max-h-64 w-auto object-contain">`, replacing the `img-slot w-52`
    placeholder and its `<!-- IMAGE: … -->` marker, flanked by the Bazel and
    Docker columns. Portrait 3:4 is load-bearing: it is what buys the art
    `max-h-64` there, where a stacked full-width band would only afford
    `max-h-32`. **It arrived RGB with the transparency checkerboard baked in at
    alpha 255** — the second time now, after `croque-shared-layers.png` — and was
    recovered with the same border-seeded flood fill (achromatic `max-min ≤ 16`
    ＋ bright `min ≥ 178`, filled inward from the borders so ink-fenced whites
    like the bowl interiors and the plate survive): **62.0% cleared**, cropped
    896×1200 → 798×986. Two checkerboard pockets fenced in by the hanging rack
    were unreachable from the border and needed a second pass seeded from solid
    `#d5d5d5` checker squares (13×13 uniform block test), clearing a further
    3.2% confined to the rack region; edge chroma stayed ≤ 32, so no
    desaturation pass was needed. Still a heavy **PNG (1.1 MB)** — it joins the
    **WebP batch below**, per the optimize-LAST convention. The two talk
    thumbnails are exempt from that batch (JPEG, ~50–95 KB, and they are source
    material rather than deck art).
- [x] **Bridge Module 0's opening: sauce → sauce-in-code → the tray → the
  sandwich** — done. "The secret sauce, in code" was moved up to sit directly
  after "Software: the secret sauce" (it used to land *after* the CAS pair, so
  the code that proves slide 1's claim arrived two slides late and nothing
  motivated *why* a container is the answer). Its closing note now carries the
  hand-off: the system dep is the "special pan," so don't ship the jar — ship the
  **microwavable dish**, one sealed tray with everything it takes to make the
  software *and* to serve it. "A sandwich of tars" opens on "**Open the tray.**"
  to collect it. `content.md` mirrors the move.
  - **Then the format pair moved after the Docker trio**, giving Module 0 a
    problem-first arc: sauce → code → *tray* → Dockerfile → black-box → four
    verbs → a sandwich of tars → the same layer, only once → cook with Bazel.
    The pain now lands ~2 slides earlier, and CAS ends up adjacent to "So… cook
    with Bazel", where "content-addressed outputs" is Bazel's own pitch — a
    stronger seam than the old encyclopedia-first order.
  - That move put three slides that *say* "layer" ahead of the slide that
    **defines** it (black-box's "busts every layer below", four verbs' "image
    (layers)"). Licensed rather than fixed by reordering: the tray bridge now
    ends "a container image — a stack of **layers**", and "A sandwich of tars"
    opens "Open the tray. We've been saying *layer* — here's what one actually
    is." The vocabulary debt is paid on purpose instead of by accident.
  - The CAS pair stays adjacent and in order: "A sandwich of tars" ends on the
    shared-prefix hinge that "The same layer, only once" answers in its first
    sentence (tuned in `61ee880` — don't split them).
  - Fixed a pre-existing `content.md` ↔ `slides.md` mismatch found in passing:
    the script had "Docker's four verbs" before "The black box build", the deck
    had them the other way round. Deck order won.
- [x] **Rebuild "Dockerfile vs BUILD.bazel" as a mapping table** — done. It used
  to be two hand-written code blocks plus a colour legend, and had three
  problems: the legend was decorative (you can't put a `<span>` inside a fenced
  code block, so *"the colors line up across both files"* was a promise nothing
  on the slide kept); both blocks had drifted from the repo (truncated
  `ENTRYPOINT` args, and a right-hand block that wasn't valid Starlark and
  didn't match `samples/python/BUILD.bazel#image`); and it was silent on where
  the base comes from, what happens to `RUN apt-get`, and how pip deps arrive.
  Now a six-row `Dockerfile → rules_img → what actually changes` table, with the
  directive/attribute name chipped in matching colour on both sides — which is
  what finally makes the `hl-*` classes do real work.
  - Dropped the paraphrased code blocks rather than fixing them: both sources
    are already transcluded live earlier (`Dockerfile` on "Building an image
    with a Dockerfile", `BUILD.bazel#image` on "Meet `rules_img`"), so the
    copies were pure drift risk.
  - `.hl-base/.hl-deps/.hl-src/.hl-entry` were three shades of pale green plus
    one blue — indistinguishable on a projector. Re-cut to one wash per brand
    hue (forest / lime / blue / charcoal) with an inset colour bar.
  - Two rows are deliberately *not* in `samples/python/BUILD.bazel`: `ENV`/`env`
    is reference (the sample sets none), and `RUN apt-get` maps to **nothing** —
    the system dep rides the pinned base until Module 2. That empty cell is the
    most interesting thing on the slide; keep it.
  - **Then the table itself was judged too dense and split into a six-slide
    walk** — the shape the deck now ships. A roadmap tile row, one slide per
    directive (`FROM` → the base · `RUN apt-get` → nothing · `RUN pip`/`COPY` →
    one layer · `ENTRYPOINT` → the launcher), then a light two-column recap.
    Each step slide is the same frame — Dockerfile code, an arrow, `rules_img`
    code, one takeaway line — so the audience learns the frame once and then
    only reads what changed.
    - Step titles are the **directive names**, not ①–④: the module already has
      "Lifecycle ① Build" / "② Run" two slides later, and two numbering systems
      in one module is a collision. Naming the directive also tells the audience
      what's being translated without a legend.
    - `RUN apt-get` → *nothing* gets its own slide on purpose. It's the hook
      into Module 2, and it only lands if the emptiness has room to sit.
    - `magic-move` (the Dockerfile morphing into the BUILD file) stays rejected:
      consecutive slides get the same step-by-step reveal without introducing
      the deck's first click animation or needing `--with-clicks` on
      `//slides:export_pdf`.
    - **Step titles then became takeaway-first, with the directive as a coloured
      kicker above the `h1`** (`.step-kicker`): "A base is a digest, not a tag",
      "The system dep becomes pinned bytes", "Four steps, one layer", "The
      entrypoint is a launcher". The `h1` should state what to remember; the
      chip keeps the wayfinding and the colour link to the roadmap tiles.
    - **`RUN apt-get` no longer maps to *nothing*.** It now shows the real
      answer — `apt.install` in `MODULE.bazel` pinned by `graphviz.lock.json`,
      plus a transcluded `layer_from_tar` — so every Dockerfile directive has a
      translation. This cost the Module 2 cliffhanger; the slide points forward
      to Module 2 building a whole image `FROM scratch` instead.
      - Added `#region apt_layer` to `samples/distroless/BUILD.bazel` so the
        layer half is transcluded, not retyped. The `apt.install` half is still
        hand-written on the slide (MODULE.bazel isn't a transclusion source) —
        **drift risk**: if `apt.install` changes, fix `slides.md` too.
      - Knock-on: Module 2's slide was rewritten from "`RUN apt` vs
        `rules_distroless`" (which re-printed the same `apt.install`) to **"Why
        there's no `RUN` to run"** — the *why* only: build actions are sandboxed
        with no network, so deps resolve in the loading phase and packages
        become content-addressed artifacts, which is what makes dedup and
        `scratch` possible. Keeps Module 2 on layer strategy, not apt mechanics.
- [x] **Name the deck's two halves: local ↔ delivery** — done, after the "Docker's
  four verbs" slide was moved out of Module 0 into Module 3. Modules **0–2** are
  **local** (`build`, `run`); Modules **3–4** are **delivery** (`push`, `pull`).
  - The menu slide gains a `local`/`delivery` chip per row (`.half-local` /
    `.half-ship`) plus a one-line spine; every section divider carries the same
    label (`.divider-half`).
  - The four-verbs slide became **"Two halves of the loop"** — the pivot at the
    Module 3 divider rather than a neutral overture. `build` and `run` are dimmed
    and checked off (`.verb-done`), `push` and `pull` lead in link-blue
    (`.verb-now`). Its old opener ("Before we change anything") and closer ("as
    we go") were Module 0 phrasing and are gone.
  - `content.md`'s run sheet gains a **Half** column, and Module 3 opens with a
    facilitator note to *say the split out loud* at the divider.
  - Two overlaps kept on purpose. "The payload: more than an interpreter"
    (Module 1) replays the `dot`-ghost beat, but the move *widens* the gap;
    Module 0 says "a system dep exists," Module 1 says "here's how we pack it."
    And "Cooking containers with Bazel" already says "self-contained
    delivery" — the microwavable dish now foreshadows it ~4 slides earlier and
    that slide is where the idea gets *named* against Bazel's hermeticity.
  - Chose an inline footer over a dedicated "The ready meal" slide: no new beat
    in a 15-min module, no new art blocked on the §13 WebP pass, and the
    metaphor lands while the code is still on screen.

## 14. Review pass — notes 1–13 (2026-09-09)

A pass over `slides.md` produced thirteen numbered notes: layout/art (image too
small, image too cluttered, labels unclear, a code-heavy stretch with no art),
ordering (lineage slide, the `RUN` slide, eager-read-before-lazy, takeaways drifted
from the modules), content (`rules_img` over-explains, the `RUN pip` slide doesn't
explain the `rules_python` hub, the recap says `rules_img` where it means Bazel),
and one delivery habit (narrate the metaphors). All thirteen are done; two needed a
judgement call, recorded below.

- [x] **1 · "Cooking containers with Bazel" — bigger plate.** The centre `auto`
  track of a 3-column grid was capping `bench-to-plate.png` at `max-h-64`. Now a
  two-column `grid-cols-[auto_1fr]`: the plate takes the whole left column at
  `max-h-80`, and the Bazel / Docker blocks are **stacked** beside it. Their
  `.verb-icon`s needed a `.verb-icon-inline` modifier (the base class centres, which
  reads wrong in a left-aligned column).
- [x] **2 · "The lineage: three generations" opens Module 1.** It sat second, after
  "The payload"; the two committed talk thumbnails now open the module, which also
  starts the code walk one slide later — free help for note 6. `content.md` mirrors.
- [x] **3 · "Meet `rules_img`" — cache/RBE, not the metadata mechanics.** Both
  mechanics bullets are gone (the ~10 KB manifest pull, and tar-once-into-CAS →
  descriptor). They pre-empted Module 4 and were exactly the "metadata and
  optimizations" explanation the review asked us not to attempt here. What's left is
  Malte's statement plus **two** bullets: no daemon, and *built for a remote cache
  and remote execution* — a layer is an ordinary Bazel action, so it builds on RBE
  and lands in the shared cache. `content.md` carries a note saying **not** to
  unpack the mechanics: the same facts land in Module 4 as a payoff instead of as
  trivia. Also deleted a stale aside there ("the next slide is the roadmap" — that
  slide was cut long ago).
- [x] **4 · `RUN pip` now mirrors the `RUN apt-get` slide, hub for hub.** Its right
  column was hand-written Starlark; it is now two transclusions in the same
  extension-then-layer order as the apt slide, so the two slides read as siblings
  and the audience learns the frame once. New regions: `#region pip_hub` in
  `MODULE.bazel` (`pip.parse`, with `use_repo` deliberately *outside* it, matching
  what `#region apt_ext` does) and `#region pip_layer` in
  `samples/python/BUILD.bazel` (`py_binary` → `pkg_tar`). The latter needed
  `py_test(name = "app_test")` moved **below** `pkg_tar` — declaration order is
  irrelevant to Bazel and it is what lets the whole chain be one live block.
  - **The slide overflowed twice before it fit**, and the fix is worth reusing: with
    two stacked code blocks the right column runs ~22 lines, and no amount of
    caption-trimming buys that back. What worked was moving the takeaway **into the
    left column's dead space** under the 4-line Dockerfile block (`.xlate-top`
    switches the grid from `align-items: center` to `start`). Trimming the region
    comments and dropping `use_repo` from the region were necessary but not
    sufficient; a `maxHeight` scroll was rejected because a scrolled block truncates
    in the PDF export.
  - Verified the regions resolve **inside the sandbox**, not just in dev: `hub_name`
    and `include_runfiles` both appear in `//slides:build` output. A missing region
    renders an empty code block rather than failing, so grep, don't assume.
- [x] **5 · "The whole translation" says Bazel, and names every package.** The
  right-hand header was `rules_img`, which is wrong on two of four rows. Now
  `Dockerfile | Bazel | package · what does it`, with the third column naming the
  ruleset per row (`.xlate-recap` re-cut to 30/32/38 with the third column quieter).
  The "five rulesets" paragraph became the **commands** half — `bazel build`,
  `run …:image_load`, `run …:push`, `bazel test …:image_structure_test` — since
  that is what a table of directives cannot carry. `content.md` now makes the point
  explicitly: the honest answer to "so I just need `rules_img`?" is *no*, read the
  third column.
- [x] **6 · The "Docker tax" slide gets art.** It closed an eight-slide code run
  with nothing to look at. New `docker-tax.png` prompt in `PROMPTS.md` under
  `## Diagrams`, food-first per the house rule: a kitchen pass blocked by a tin
  money box with a coin going in per plate, beside a second pass the same plate
  walks straight through; labels capped to `docker build` / `bazel test` /
  `per edit`, with the numerals-clock-chart ban made explicit (the slide already
  has the numbers). **Not generated yet** — the slide carries a captioned
  `img-slot` and the `<!-- IMAGE: … -->` marker, so it is not blocked, and
  `content.md` tells the presenter to say the line either way.
- [x] **7 · Narrate every metaphor.** `content.md` pointed at art in three places
  out of eleven plates, which is why the pictures felt loose. Every illustrated
  slide now has an `*(On screen: … — say it out loud: "…")*` cue naming the file and
  the sentence: `bechamel-to-sandwich`, `fridge-sandwich` (＋ `rotten-tomato` as its
  sharpened form), `sandwich-layers`, `bench-to-plate`, `catering-vs-onepot`,
  `docker-lifecycle`, `one-base-n-images`, `without-bytes`, `remote-cache-rbe`.
  `croque-shared-layers` was already narrated verbatim and was the model.
  - Fixed the stale script titles found in passing, so the script can be followed
    against the deck: "Catering vs the lasagna sandwich" → "the one-pot bake",
    "Building multiple images: dedup" → "Two services, one shared blob", "The
    'black box' build" → "Black-box builds", plus the Module 4 paragraphs
    **reordered** to the deck's order (One base, N images → Building Without Bytes
    → the pantry), which had been inverted.
- [x] **8 · "Why there's no `RUN` to run" → Appendix.** *(Judgement call.)* Hard to
  explain and off Module 2's spine, which is layer strategy rather than apt
  mechanics. **Moved rather than cut** — the content is good, it just should not be
  on the critical path of a 17-minute module; it now sits between the structure-test
  lab and the comparison table, where it answers "but where did `RUN` go?" on
  demand. Its one load-bearing sentence moved into the **distroless** lede
  (`apt.install` already resolved `dot` at load time into content-addressed layers,
  so there is no `RUN` left that needs an OS underneath), so Module 2's argument
  still stands. The slide's own "the next two slides" pointer was rewritten — in the
  appendix there is no next two slides.
  - The alternative was deleting it and splitting its halves onto the apt and
    distroless slides. Rejected: the apt slide is already the densest in Module 1.
- [x] **9 + 10 · Module 3's push slides recut, so eager is read before lazy.** These
  were one seam. The old pair described **lazy** in a symmetric column *before*
  eager had been run, while lazy's own demo (Experiment 2) is in the appendix — so
  the audience met the harder strategy first. Now:
  **A · "Push — daemonless, to any registry"** — the pantry framing, `image_push`,
  and Experiment 1's commands moved up onto it. One thing happens, and it is the
  thing the room runs.
  **B · "Optimizing the push"** — the optimization slide note 9 asks for, in payoff
  order: only-missing-blobs go up (Module 2's dedup spent as bandwidth), then
  `strategy = "eager"` (*what we just ran*), then `strategy = "lazy"` as a **one-line
  forward pointer** to Module 4 and the appendix rather than a symmetric column.
  - Note 9 read as "state it as an optimization and group the three together". If it
    meant "trim it", B is the slide to trim — the dedup line plus the rule of thumb
    would survive alone.
  - `content.md` keeps the precision that always gets asked: lazy needs a remote
    **cache** and that is all — `img` speaks REAPI ByteStream to the CAS; it does
    **not** need remote execution.
- [x] **11 · `without-bytes.png` de-cluttered by cropping, not re-rolling.** The
  plate spent ~12% of its height on a ribbon banner reading "THE CULINARY FLOW & CAS
  PROVENANCE REPOSITORY DIGEST PLATE." over "EST. 1888" — unreadable at `max-h-48`
  and pure noise, exactly as the review said. Pure-PIL fix, no generation pass
  needed: crop at `y=141` (just under the ribbon's lower rule), clear the leftover
  ornaments in the new top band, and redraw the frame's top rule.
  - **The crop could not be a straight horizontal cut.** "EST. 1888" and its
    flourishes sit at `y≈159–195`, but the tilted `digest` card starts at `y≈167`
    and the cook's hat at `y≈150` — cropping low enough to lose the text would have
    clipped the word "digest" off the card. So: crop high (at the rule), then clear
    the band `141..204` **only outside** three x-ranges measured off an ink-density
    scan (`710–900` cook+whisk, `945–1160` the card, `1980–2100` book+quill). The
    cream is tiled from rows `192..214`, a clean gap that runs the full width.
  - The frame is a plain ~3px near-black rule with one antialias row, so redrawing
    it is four `putpixel` rows sampled off the surviving left edge (`(2,0,0)` then
    `(140,129,122)`). Tiling from those rows also preserves the **side** borders for
    free, since the border runs the full height.
  - `3172×1207 → 3172×1066`, aspect `2.63 → 2.98`. **Stayed at `max-h-48`:**
    `max-h-52` was tried and left only ~15px to the footer.
  - TASK §13's "superseded prompt, re-roll when convenient" still stands — a re-roll
    would also fix the repeated digests and the mangled incidental labels. This was
    the cheap 90% of it.
- [x] **12 · `remote-cache-rbe.png` relabelled so the plate explains itself.** The
  lettering was kitchen-only (`domestic cook`, `hotel kitchen pass`, `the
  commissary — …`), so the slide's framing line had to recite the mapping in prose.
  - **The labels sit directly on the keyed-out field** (alpha 0 around them), so
    this was an alpha-erase plus a redraw — no inpainting, no re-key. Peak stroke
    alpha is 255 at `≈(20,0,0)`, i.e. the ink is effectively black.
  - Sizing recipe worth reusing: binary-search the font size so
    `LiberationSerif-Italic` renders **the original string** at the measured ink
    width, then draw the **new** string at that size with `anchor='ls'`, offsetting
    the origin so the baselines coincide. That is what makes the replacement sit in
    the plate rather than on it.
  - `domestic cook` → `your laptop` · `hotel kitchen pass` → `CI — the hotel pass`
    (and the now-redundant small `CI` by the ticket rail erased) · `the commissary —
    one content-addressed pantry` → `the remote cache — one content-addressed
    pantry`.
  - **`line cooks — RBE workers` was deliberately left alone**, against the plan:
    it already carries the computing term *and* the metaphor, and it is drawn on an
    arc that straight PIL text cannot match. Same reasoning spared the small `CI`
    label's twin. Relabel only what is misleading.
  - The slide's framing line lost the recited mapping; `content.md` now says the
    plate labels itself and tells the presenter to trace the leader lines instead.
- [x] **13 · Takeaways rewritten to track the modules.** The five old lines predated
  the current structure and led with framing. Now one line per module, mechanics
  first: declare-don't-script *(1)* · split by volatility — **in parallel**, dedupe,
  thin *(2)* · daemonless *(1–3)* · share the pantry — remote cache ＋ RBE, and
  push/pull move only missing blobs *(3–4)* · build without bytes *(4)* ·
  Slide-as-Code. Each is one line at export width. `content.md` mirrors it and keeps
  its **Mental model** and **Point at the labs** directives.

**Ordering note:** notes 11 and 12 edited `without-bytes.png` and
`remote-cache-rbe.png` in place, ahead of §13's still-pending WebP batch, so that
pass converts the fixed art. Originals backed up outside the tree before the edit —
`remote-cache-rbe.png` was untracked at the time, so git could not have recovered it.

**Verified:** `//slides:build` (both new regions present in the sandboxed output),
`bazel build //samples/...`, `//samples/python:app_test`, and `//slides:export_pdf`
— 46 pages, every touched slide eyeballed. Deck order is now Module 1 = lineage →
payload → meet → the four directives → recap → build → run → tax.

---

## 15. Review pass — inspection & the `rules_img` delta (2026-09-09)

Three review notes, all answered. They were really one gap: the deck taught how to
*build* an image and never how to *look inside one*.

1. **"The slides do not explain what is `rules_img` feature only compared to
   `rules_oci` features."** — [x] New **last** appendix slide, "Coming from
   `rules_oci`?". Deliberately **migration**-framed (two short columns, "carries
   over" vs "new in `rules_img`") rather than a feature matrix: the deck teaches
   `rules_img` only (§11), and a comparison table would re-centre a ruleset removed
   on purpose. This also closes a live script↔deck inconsistency — `content.md`
   promised "the full comparison is at the end" after that table had been cut.
   It names the trade-offs honestly too (`os`/`architecture` not settable,
   `exposed_ports`/`volumes` → `config_fragment`), and records that daemonless push
   is **not** a differentiator, since `content.md` already calls eager push "much
   like `rules_oci`".
   → This also closes the §12 open item "map each ruleset's impact across build/push/run
   … turn it into a comparison table": the decision is **no matrix**, for the reason above.
2. **"How would you inspect the content from a container generated from bazel if the
   generated image is broken?"** — [x] New **main-flow** slide at the end of Module 2,
   "When the image won't run". Carries the repo's best war story, which until now
   lived only in a `MODULE.bazel` comment: merged-`/usr`, where layering a real
   directory over the base's `/lib` symlink **replaces** it and amputates `/usr/lib`.
   New `#region mergedusr` in `MODULE.bazel` so the slide transcludes the real thing.
   Two probes, both daemonless: `tar tf` on the layer tar, and `//labs:explain`.
   The load-bearing sentence is from `labs.yml` — `container_structure_test` `lstat`s
   paths in an unpacked tar and never **execs** anything, so it was **green** on
   images that could not run a single binary.
   → Also discharges most of §12's "`container_structure_test` explainer" without
   spending a slide on it.
3. **"How can I use any tool to inspect the layer outside bazel? How to deal with the
   symlinks to ensure a OCI folder?"** — [x] New appendix slide, "Inspecting a layer
   outside Bazel". The reviewer's premise was exactly right and the reason is
   specific: the **default** on-disk shape is a ***sparse*** OCI layout
   (`sparse-oci-layout` not `oci-layout`, `root.descriptor.json` not `index.json`,
   layers as `<digest>.descriptor.json` stubs), which is why `skopeo`/`dive` bounce
   off it. New `//samples/python:image.oci` + `:image.oci.tar` filegroups
   (`#region oci_layout`) surface the `oci_layout` / `oci_tarball` output groups.

### The symlink answer, measured

"Symlinks" is ambiguous and **both** readings are real, so the deck answers both:
symlinks *inside* the image (merged-`/usr`, note 2) and symlinks *around* the output
(note 3). For the latter, verified in this repo:

- `image.oci` **is** spec-compliant — `index.json` + `oci-layout`, and every blob's
  content hashes to its own filename.
- But every blob is a **symlink into the execroot**: `du -sh` reads **60K**,
  `du -shL` reads **325M**. Copy with `cp -rL`, or use `image.oci.tar` (608 MB, real
  bytes, zero symlinks, zeroed timestamps).
- `crane export … | tar tf -` flattens the image to **8692 paths** with no `bin/dot`
  — the deck's payload story, proven without starting a container.
- Under `--remote_download_minimal` the bytes were never fetched at all
  (`labs/remote/README.md`: 258 MB → 177 KB). A layout is dangling links until you ask.

### Blocked on the pinned ruleset — rules_img 0.3.12

The obvious probe for note 2 is the **`mtree` output group** (the whole merged
filesystem as one text file), plus the native **`image_structure_test`** (mtree +
config, no daemon, no tar). **Neither exists in 0.3.12** — the pinned ruleset ships
no `img/test.bzl` and no mtree anywhere; the available output groups are exactly
`descriptor`, `digest`, `oci_layout`, `oci_tarball`, `root_blob`, `sparse_oci_layout`.
Both landed upstream after 0.3.12; latest release is **v0.3.21**.

- [ ] **Bump `rules_img` 0.3.12 → 0.3.21** (MODULE.bazel line 5 already states
      "Requirement #8: track latest rules_img", so this is a standing intent, not new
      scope). Payoff: `--output_groups=mtree` becomes the single best answer to note 2,
      and `image_structure_test` lets the labs drop the `image_load` → `tarball` →
      `container_structure_test` detour. Risk: nine minor versions of drift across the
      samples, all three labs, and CI — needs a full `bazel test //...` and probably
      lockfile churn. Left out of this pass on purpose: the slides are written against
      what the repo actually pins today.

### Bugs found while verifying, and fixed

- **`ci.yml`'s reproducibility check was vacuously green.** It hashed
  `bazel-bin/samples/python/image/index.json` — a path `rules_img` never writes. So
  `sha256sum` failed to stderr, both vars were empty, and `test "" = ""` passed no
  matter what. Now reads the **`digest` output group** (`image_digest`) and asserts
  the value is non-empty. Slide "Same artifact, two philosophies" cites this check as
  "measured, not asserted", so it needed to actually measure something.
- **Slide "Assemble, don't run" showed a directory that doesn't exist**
  (`bazel-bin/samples/python/image/`). Corrected to `image_manifest.json` /
  `image_config.json`.
- **`samples/python/BUILD.bazel`'s lazy-push comment was stale** — still said "needs
  remote execution + a remote cache". Commit `6e35794` fixed this on the slides but
  missed the BUILD file. Now says a remote **cache** is enough, over REAPI ByteStream.
- **`//tools:crane` is an `alias` onto a `filegroup`**, so it can't be `bazel run`.
  Added `//tools:crane_cli` (an `sh_binary` wrapper, same `$(rlocationpath)` idiom as
  `local_registry`) so the appendix slide's commands are real. Verified: `-- version`
  prints `0.22.1`.

### Budget

40 main ＋ 8 appendix, ~79.5 min of the 90 (was 39 ＋ 6, ~78 min) — **+90 s**, leaving
~10.5 min of slack. `//slides:export_pdf` confirms **48 pages, up from 45** — exactly
the three new slides. (§14's "46 pages" was stale; the committed PDF is 45.) Only the debugging slide went into the main flow; the two whose
explanation bottoms out in "the bytes aren't local" went to the appendix, which
already sits after Module 4, so that prerequisite is paid by construction.

## 16. Dependency bumps — the seven Dependabot security PRs (2026-09-11)

Dependabot had seven PRs open against `main` (#1–#7). Every one was a **security**
update, each matching an open alert. Rather than merge them one at a time, all seven
were lifted in a single pass here, because merging them would not actually have fixed
the build (see below).

| package | was | now | advisory fixed in |
|---|---|---|---|
| `linkify-it` | 5.0.1 | 5.0.2 | 5.0.2 (high) |
| `valibot` | 1.4.1 | 1.5.0 | 1.4.2 (medium) |
| `postcss` | 8.5.15 | 8.5.28 | 8.5.18 / 8.5.23 (high, medium) |
| `mermaid` | 11.15.0 | 11.17.2 | 11.16.1 (medium ×3, low) |
| `nanoid` | 3.3.15 | 3.3.19 | 3.3.16 / 3.3.18 (high ×2) |
| `browserslist` | 4.28.4 | 4.28.9 | 4.28.7 (high ×2) |
| `baseline-browser-mapping` | 2.10.38 | 2.11.22 | 2.11.0 (medium) |

All seven are **transitive** — none are in `slides/package.json`, and every parent
range is a caret that already admitted the target, so no `overrides` were needed. Some
landed above Dependabot's target because `npm update` takes the newest in-range.

### Why merging the PRs would not have been enough

Dependabot only ever updates `slides/package-lock.json`. But that file drives only the
`npm ci` paths (`ci.yml`, `pages.yml`, `pdf.yml`); **`npm_translate_lock` builds from
the committed `slides/pnpm-lock.yaml`**, which Dependabot cannot update — it has no
pnpm ecosystem entry, and the file does not even exist on `main`. Merging #1–#7 would
have left `bazel build //slides:build` compiling the vulnerable versions with every
check green. Nothing asserted the two locks agreed.

`ci.yml`'s `slides` job now has a **"The two lockfiles must agree"** step that
re-derives the pnpm lock and fails on any diff, so this cannot recur silently.

### The re-lock procedure (the `--dir` form in §13 was broken)

```bash
cd slides && npm update --package-lock-only <packages…>   # or: npm install --package-lock-only
cd .. && bazel run -- @pnpm//:pnpm --dir "$PWD/slides" import
```

The path must be **absolute**. `bazel run` leaves cwd inside the runfiles tree, so the
`--dir=slides` spelling recorded in §13 fails with `ENOENT` on
`…/pnpm.runfiles/_main/slides`. Corrected in the `MODULE.bazel` comment too.

**Re-lock with the same npm major CI uses.** `actions/setup-node` with `node-version: 24`
currently ships **npm 11.19**, and the two npms disagree about optional *peer* deps of
`cpu: wasm32` packages (`@emnapi/core`, `@emnapi/runtime`, pulled in by the wasm32-wasi
bindings of `rolldown` / `oxc-parser`). A lock written by an older npm makes CI's
`npm ci` fail with `EUSAGE … Missing: @emnapi/core@… from lock file` — which is exactly
how this branch broke, and why `e8d4d12` had to regenerate the lock afterwards. If the
local `npm -v` is behind, re-lock through `npx npm@<ci-version> install --package-lock-only`.

### Still outstanding — not fixable by a bump

Three alerts survive, all transitively pinned by a parent, all build-time-only deps of
the deck (no runtime attack surface):

| package | at | why stuck |
|---|---|---|
| `dompurify` | 3.2.7 under `monaco-editor` | parent pins it; the root copy is already 3.4.11 |
| `js-yaml` | 3.14.2 under `gray-matter` | parent pins 3.x; the root copy is already 4.2.0 |
| `image-size` | 1.2.1 | no fix published (`first_patched_version: none`) |

These need a `monaco-editor` / `gray-matter` release upstream; forcing them with
`overrides` would cross a major boundary and is not worth it for a slide deck.

### Verification

`npm ci` ＋ `npx slidev build` pass; `bazel build //slides:build` passes and visibly
extracts `mermaid@11.17.2`, confirming the bump reached the hermetic path. `npm audit`
now reports 9 advisories, all of them in the three packages above — none in the seven
bumped here. The deck uses **no mermaid diagrams** (graphs
are graphviz under `slides/graphs/`), so the only minor-version bump carries no visual
risk.

## 17. Review pass — Johan's deck feedback (2026-09-30)

Slide numbers are as Johan saw them (the export's numbering).

- **Slide 17: `images.pull(...)` dimmed to unreadable.** Slidev's `{N}` line highlight
  sets every other line to `opacity: 0.3`. New `.code-pin` wrapper (`slides/style.css`):
  every line stays at full strength, the highlighted line gets a lime band, and an
  optional `--pin` string adds a callout ("◀ the pin: bytes, not a tag"). Slide 8
  (Dockerfile `{4-6}`) had the same dimming and uses `.code-pin` too (band only).
- **Slide 29: clipped on the right, white strip at the bottom.** There were two causes:
  - One long code line gave the `two-cols-header` grid a min-content width wider
    than the canvas. Fixed globally with `min-width: 0` on `.col-left`/`.col-right`.
  - The `mergedusr` block's `maxHeight` made Slidev scroll the highlighted line into
    view. That scroll moved the whole slide up 15px, which exposed the white strip.
    The block now fits without `maxHeight`: `code-sm`, a 3fr/2fr split, and the note
    moved into `::bottom::` on one line.
  - Slide 28 was also overflowing (its right column ran off the edge). It is now
    2fr/1fr plus `code-sm`.
  - A DOM sweep of all slides shows no layout overflow.
- **Slides 36/37: tiny text in the plates.**
  - 37 (`remote-cache-rbe.png`): its four labels carry the meaning, so they were
    cleared from the PNG (alpha → 0; the brace over the line cooks is kept) and
    re-set as live HTML text over the image (`.plate-labels`, positioned in percent).
    Image `max-h-60` → `max-h-64`.
  - 36 (`without-bytes.png`): image `max-h-48` → `max-h-56`, with the "Lazy pulls"
    bullet cut to one line to make room. Johan was fine with the digests staying
    unreadable.
- **Audit of the other plates. Still small, not changed yet:**
  - slide 10 `sandwich-layers` (app code / deps / runtime / base OS) is the one most
    worth fixing: the labels *are* the lesson.
  - slide 11 `croque-shared-layers` (bread / gruyère / ham / béchamel, "shared", "this
    differs") is readable-ish at about 9px.
  - slides 26 `catering-vs-onepot`, 31 `docker-lifecycle` and 35 `one-base-n-images`
    have labels that the slide text or caption already repeats.
  - These plates are mostly opaque, so moving the labels to HTML means painting over
    the baked text, not just clearing alpha. Otherwise, regenerate them without text
    (`PROMPTS.md`).
- `remote-cache-rbe.png` is still a 6.8 MB PNG and goes through the §13 WebP batch.

## 18. Naive-student proof-read + slimmer layers (2026-10-02)

Every lab README was walked as a beginner, starting from an empty `HOME` and a fresh
clone. The setup was red and left about 14 GB on disk (it filled a 39 GB disk partway
through), and the structure tests took 23–141 s. Root cause: each Python app layer was
**~560 MB**, of which 559 MB was the interpreter. The python-build-standalone archive is
unstripped (libpython 218 MB, python3.12 102 MB), and `pkg_tar(include_runfiles)` copies
the binary again for each of the `python` and `python3` symlinks.

### Done (branch `slim-layers`)

- `MODULE.bazel`: a `python.single_version_platform_override` that pulls the
  `install_only_stripped` build of the same 3.12.13 / 20260414 release.
- `optimize = True` on every app layer's `layer_from_tar`, plus
  `build --@rules_img//img/settings:compress=zstd` in `.bazelrc`. The duplicate binaries
  become tar hardlinks, and the layer was stored uncompressed before (`.tar` maps to
  "none") and is now zstd.
- `.bazelrc`: `test --build_tests_only`, so ~6 GB of `image_load` tars that no test reads
  are no longer built, and `--experimental_disk_cache_gc_max_size=5G`.
- `samples/python:image_structure_test`: `size` small → medium. It hit the 60 s timeout
  during a cold, loaded setup.

| | Before | After |
|---|---|---|
| cold `bazel test //samples/... //labs/... //tools/...` | 256 s, 1 TIMEOUT | 34 s, 17/17 |
| bazel-out + disk cache (apparent) | ~12 + ~11 GB | 3.5 + 3.4 GB |
| Python app layer blob | 560 MB (`tar`) | 36–53 MB (`tar+zstd`) |
| `docker images` level0 / 2 / 3 / playground | ~1.1 GB each | 175 / 219 / 688 / 81 MB |
| structure tests (cold, in parallel) | 70–141 s | 10–14 s (5 s alone) |

How it was verified:
- The ci.yml reproducible-digest check passes, with no disk cache.
- The structure tests, `docker load` + `run` of every solution, the push (7 blobs, then
  2), and `crane manifest` / `export` all read zstd.
- The docs now carry the new numbers: remote §1 380 / 260, §2 82 MB / 742 KB (110×),
  image.oci 12K / 78M, image.oci.tar 78 MB, "~8 GB free disk". The crane export count
  (8692 paths) is unchanged.

### Next: an extra lab, "one interpreter, N images" (closes the §9 / volatility-gap item)

Make this an **optional extra lab** (e.g. `labs/level4_shared/`), not a rewrite of the
deck. The main path keeps teaching "`pkg_tar(include_runfiles)` → one layer". The extra
lab then shows the price of that, which is the same interpreter shipped nine times, and
the fix.

- [x] **Built as `labs/level4_shared/`.** `defs.bzl` holds `py_layered_binary`, which splits
  a py_binary's runfiles into interpreter / third_party / app groups via `RunfilesGroupInfo`.
  `layer_from_binary` turns those into shared layers: api and worker share base + 35.7 MB
  interpreter + 5.2 MB wheel and differ by a few KB of app. `groups_test` checks that
  nothing is lost; it caught the generated empty `__init__.py` files, hence
  `legacy_create_init = 0`. Wired into `:tasks`, progress, labs_ci (LABS/STRETCH/walk)
  and labs.yml.
- [x] Spike first: split the interpreter, deps and app into separate layers with rules_img
  `layer_from_binary` (`runfiles_sharing_mode = "shared"`). Lab shape:
  - two py_binaries
  - `samples/shared_layers/digests.sh`-style proof that their interpreter layer digests match
  - a structure test
  - It needs a small wrapper rule that gives the `py_binary` a `RunfilesGroupInfo`.
    rules_runfiles_group is already in the graph via rules_img; rules_python 2.0.2
    doesn't provide one.
  - Gain: one ~36 MB interpreter blob shared by every image, instead of 9 copies.
    Structure-test time doesn't change.
  - Touch points, only if the main deck later adopts the split:
    - slides.md :457–597 ("one tar → one layer") and the hand-typed `image_manifest` at :510–519
    - content.md :285–311
    - the level0–3 READMEs
    - `layer_test.py`, which would pass vacuously once wheels leave `app_layer.tar`
    - the `labs_ci.py` literal edits (:303–309, :363–367, :414) and its base-layer lines `{2,3,4,5}`
- [x] The apt layers students write (`layer_from_tar(src = "@x//:flat")`) stay
  uncompressed in the answers. Each lab now has an optional ★ "shrink the layer" stretch
  that adds `optimize = True`, measured as graphviz 94 → 38 MB, tesseract 130 → 58 MB and
  POCL 589 → 180 MB, with the structure tests green and `docker run` OK.

### Open proof-read findings (Levels 0–1; Levels 2–3, playground and remote still being walked)

- [x] `labs/level0_graphviz/README.md:39`: the ★ row has `docker run` with no
  `image_load`, so a student runs a stale image or gets "pull access denied".
- [ ] `labs/README.md`:
  - [ ] It says "Three helper commands", but the table has four.
  - [ ] `bazel test -k //labs:tasks` gives one line per *test*, not per task, and
    re-runs every red structure test each time.
  - [ ] "under a second (Level 1)": the first `image_layer_test` builds the app layer.
- [ ] `labs/level1_buildtime/README.md`:
  - [ ] :33 says `ModuleNotFoundError: cryptography`; the real text is
    `No module named 'cryptography'`.
  - [ ] :61: `grep _rust` matches 33 `.pyi` lines. Use `grep _rust.abi3.so`.
  - [ ] The ★ sdist stretch has no command and no file to edit.
- [ ] `labs/explain.py`:
  - [ ] It shows stale results until a test is re-run. Print the log's age.
  - [ ] Its py_test tail is mostly sandbox paths; the error is on the last line.
- [ ] The `diff … solution/BUILD.bazel` stuck aid is about half noise (headers,
  `exports_files`, `tags = ["manual"]`). Make the skeleton and the solution
  identical outside the TODOs.
- [ ] `labs_ci.py`:
  - [ ] `image_load >/dev/null` hides a rootless/rootful Docker mismatch
    (load into one daemon, `docker run` against the other).
  - [ ] `answers` modes: `--all` and `--changed FILE` are undocumented.

## 19. Expert-audience review — Alex Eagle / Malte lens (2026-10-02)

§18 read the labs as a beginner. This pass reads the deck and labs as a Bazel +
containers expert, someone like Alex Eagle (Aspect: rules_oci, rules_py,
rules_distroless) or Malte (rules_img). The question: would they stay engaged?

**Verdict:** they'd enjoy roughly the last third of the deck and the appendix. Today the
labs offer them nothing *open*, because every task has a known answer in `solution/`.
Hence the expert stretch tasks below. They're for discussion, not grading.

- **Where they'd go quiet** (by design, the main path is for newcomers):
  - Modules 0–1 and Levels 0–2 are their own docs read back to them.
  - Three spots invite pushback:
    - [ ] **"Coming from `rules_oci`?"**: check every claim against *current* rules_oci,
      especially "never staged into runfiles" and "eager push is much like rules_oci".
    - [ ] **"Docker tax"** (0.8 s vs 2.2 s): write down how the Dockerfile baseline was
      tuned (BuildKit cache mounts, `uv`, layer order) before someone calls it a
      strawman.
    - [x] **Level 4 vs `py_image_layer`**: the README now credits aspect_rules_py and
      points at the sharing difference.
- **Where they'd lean in:**
  - the §18 story (a 560 MB layer that was 559 MB unstripped interpreter);
  - the hidden-host-requirements appendix;
  - lazy push over ByteStream, shallow pulls, BwoB, local RBE;
  - the postinst / `mergedusr` traps.
- **Decisions:**
  - **No GPU/CUDA content.** It needs specialized hardware and matching drivers. Level 3
    stays CPU-only.
  - **rules_python stays; no swap to aspect_rules_py.**
    - rules_py builds on rules_python's interpreter toolchain anyway.
    - The main path and Level 4 are built on `py_binary` runfiles.
    - `py_image_layer`'s per-binary tar paths would break Level 4's sharing.
    - A swap weeks before the workshop would mean re-testing every lab.

### Expert stretch tasks — validated against the pinned versions, not yet run

Validated by reading the code (Bazel 9.1.1, rules_img 0.3.12, rules_python 2.0.2,
rules_distroless 0.8.0) plus BCR and GitHub. **Nothing has been built yet; each one
needs a dry run before it's published.** Ranked by conversation value.

- [ ] **E1 · Multi-arch index** (✅ feasible with caveats, ½–1 day). One `image_index` for
  amd64 + arm64. Real problem: Apple-silicon laptops and Graviton fleets.
  - `image_index(platforms=…)` uses a split transition (`rules_img+/img/private/index.bzl:303`).
    The pulled base already lists arm64.
  - The apt yamls already lock `archs: [amd64, arm64]`, and the aarch64 stripped
    interpreter is pinned (`MODULE.bazel:113`).
  - `gawk` is `cfg="exec"`, so no cross C compiler is needed.
  - `tar`-driver structure tests run fine on amd64.
  - Missing: `target_platforms = ["linux_x86_64", "linux_aarch64"]` on the `labs_pypi`
    `pip.parse` (wheel selection is host-only today), plus `platform()` targets.
  - Cost: every layer is built twice, which presses on the 5 GB disk-cache cap.
    *Running* arm64 needs qemu, so it's out of scope.
- [ ] **E3 · Stamp, sign, attest without killing the cache** (✅ caveats, 1½–2 h).
  Real problem: supply-chain requirements (SLSA).
  - rules_img `stamp` + Go templates cover labels, annotations and env
    (`manifest.bzl:428`) and push tags (`push.bzl:70`). Layers never change.
  - **Trap:** a global `--stamp` also stamps every `py_binary` (`stamp=-1`), so the app
    layer changes every commit. Answer: `stamp="force"` on `image_push` only, with a
    `{{.STABLE_GIT_SHA}}` tag.
  - There's no workspace_status script yet.
  - **SBOM:** no ruleset emits one. The apt `*.lock.json` and `requirements_lock.txt`
    have every field needed (a stdlib converter of ~60–80 lines). rules_img can attach
    the SBOM as an OCI referrer (`subject` / `artifact_type` / `referrers`); support in
    crane serve is unverified.
  - **cosign:** pin v2.6.1 via `http_file` and use a local key with `--tlog-upload=false
    --allow-insecure-registry`. v3 may also need `--use-signing-config=false`. Sign the
    `digest` output group of `image_manifest`, because push returns no digest.
- [ ] **E5 · Level 4 with aspect_rules_py** (✅ caveats, 2–4 h). Real question: do I need a
  custom rule at all?
  - Use rules_py **1.12.1**: 2.0.0-alpha rejects rules_python's `py_binary`. It forces no
    version bumps.
  - Risk: it registers its own 3.13 interpreters, so check with cquery that 3.12 still
    wins.
  - Output is three plain bsdtar tars (gzip). Wrap them in `layer_from_tar(optimize=True)`.
  - **Expected: `shared_layers_test` stays red.** The tar paths embed `api.runfiles/`
    vs `worker.runfiles/`, while `layer_from_binary` uses `/app/.shared_runfiles/`.
    That contrast is the lesson. The macro is marked EXPERIMENTAL.
- [ ] **E2 · Base-image CVE bump** (✅, ½ day). Real problem: weekly patching across N
  services.
  - The digest is pinned once (`MODULE.bazel:186`); the `#base_pull` transclusion must
    stay 10 lines.
  - **Gotcha:** re-locking apt changes nothing. The yamls pin a Debian snapshot
    (`20240210T223313Z`), and bumping that is what brings in CVE fixes.
  - A base bump leaves app-layer digests unchanged (`digests.py` shows it).
  - There's no scanner on BCR (only `rules_syft`). Fetch grype by `http_archive`, then
    choose between a pinned DB (`GRYPE_DB_AUTO_UPDATE=false`, stale) and a
    `requires-network` test (not hermetic). That trade-off is the conversation.
  - `crane rebase` is redundant under Bazel; mention it only for comparison.
- [ ] **E4 · The postinst gap, `ca-certificates` on scratch** (✅, ~1 h).
  - `dpkg_status.sh` only writes `/var/lib/dpkg/status`.
  - Level 0 ★ already covers `dot -c`, so use `samples/distroless` instead. The
    python-slim base already ships a CA bundle, so it can't show the break.
  - Fix with rules_distroless `cacerts` + `SSL_CERT_FILE`.
  - Test offline with `fileExistenceTests` and a `py_test` counting `get_ca_certs()`.
  - Dropped: ldconfig and alternatives, because nothing visibly breaks.
- [ ] **E6 · Break reproducibility on purpose** (⚠ mostly exists, 1–2 h).
  - `ci.yml:57-73` already compares builds before and after `bazel clean`;
    `ci.yml:109-121` already compares host gcc vs `hermetic-cc`.
  - Reframe as: read those checks, break them (non-zero mtime, a different compression
    level), explain the diff.
  - Optional RBE digest leg: needs Docker; the worker is pinned by tag, not digest; add
    `--remote_download_outputs=toplevel`.
  - diffoscope needs zstd/libmagic, and `crane export` + `digests.py` cover most of it.

Where they'd live, if they're published: a `labs/expert/README.md` of open problems
with no tests, framed clearly as *discussion*. That's because "`bazel test` tells you
when you're done" doesn't hold for them.

### Speaker prep — questions to expect

- **E1:** Is it a transition or a build per arch? How are native wheels for the other arch
  picked? How do you test arm64 on an amd64 runner? Is the apt lock per arch?
- **E2:** How many blobs does a base bump push across N services? Who bumps the digest
  (Renovate on `MODULE.bazel`)? Rebase vs rebuild? Should scanning happen in the build
  graph or in the registry?
- **E3:** Does `--stamp` change the digest and kill the cache? Where does signing live,
  given it needs credentials and isn't hermetic? Which SBOM do you trust: one from lock
  files or one from the image?
- **E4:** Which packages break silently? Can a structure test catch it? Should
  rules_distroless run a safe subset of postinst?
- **E5:** Same interpreter-layer digest? Does rules_py's venv layout change the entrypoint
  or `sys.path`? Should rules_python provide `RunfilesGroupInfo` itself?
- **E6:** What still leaks (timestamps, compiler paths, locale)? Should CI fail on a digest
  diff between configs?
- **Deck:** Why rules_img over rules_oci *today*, and can you migrate incrementally (OCI
  layout in and out)? Is the Docker baseline tuned? What does BwoB cost when a test needs
  the bytes?

## 20. Lost inputs under the disk cache (2026-10-12)

- [x] **Default builds no longer lose inputs.** `bazel build //...` failed once with
  `Lost inputs no longer available remotely: samples/python/push_lazy.configuration.json`
  (it passed on Bazel's automatic retry). Cause: Bazel 9 treats disk-cache hits like
  remote ones, so with the default `--remote_download_outputs=toplevel` it doesn't write
  intermediate outputs to `bazel-out`. The 5 GB `--experimental_disk_cache_gc_max_size`
  then evicted one mid-build. Fix: `build --remote_download_outputs=all` in `.bazelrc`.
  The `*-bwb` / `local-rbe` configs still set `--remote_download_minimal` after it.
- [x] **Remote lab ★ "when the cache forgets"** (`labs/remote/README.md` §2): delete
  the blob by hand, fail with retries=0, recover three ways (retry, `--rewind_lost_inputs`,
  `=all`). Run end to end on 9.1.1. Two traps found while writing it: `no-remote-cache`
  does **not** keep the disk cache away (`no-cache` does), and if the cache already lacks
  the blob, Bazel quietly re-runs the producer instead of failing (hence the warm-up build).
  - [ ] Not in `labs_ci.py`: STRETCH only holds docker smoke checks for the levels. Add a
    `remote` leg if this stretch should be guarded against Bazel bumps.
