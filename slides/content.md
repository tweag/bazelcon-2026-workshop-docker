# Building Without Bytes — 90-Minute Workshop Script

Full facilitator script for the BazelCon 2026 workshop **"Building Without
Bytes: High-Velocity Image Composition at Scale."**
**9:00–10:30 · Instructor: Rafael Lima · Sponsored by Tweag by Modus Create.**

This is the source of truth for what the workshop *says and does*;
[`slides.md`](slides.md) is the projected deck. The whole talk is told as **one
story — cooking a sandwich**: software is the *secret sauce*, a container image is
a *sandwich of tar layers*, a `Dockerfile` is a *fridge sandwich* (tasty once,
never reproducible), and Bazel is the *precise kitchen* you can build the
cookware inside of. Source outline: [`../ref/draft.md`](../ref/draft.md) ·
Proposal: [`../PROPOSAL.md`](../PROPOSAL.md).

> **Abstract.** In modern CI/CD the traditional `docker build` is often the
> slowest link: imperative, sequential Dockerfiles struggle with cache
> invalidation and lack the fine-grained dependency tracking large monorepos
> need. This workshop takes a **graph-based** approach — with Bazel and
> `rules_img` we treat container layers as pure, declarative
> artifacts, assembling images in seconds, independent of a local Docker
> daemon. Attendees move from legacy "black box" builds to a transparent,
> content-addressable architecture so that **what you build in CI is
> byte-for-byte identical to what runs in production**.

**Format:** ~90 min, 5 modules + wrap-up, each = short concept + a Lab.
Attendees clone the repo and run real targets. An early **agenda ("The menu")**
slide projects this run-sheet, a **lab card** slide right after it gives the two
ways to follow along (the README setup on a laptop, or fork + PR with GitHub
Actions doing the building), and each module closes on its own **Lab** slide.

**Budget:** the deck is **44 main slides ＋ 10 appendix**, retimed to **~79.5 min of
content in the 90-min slot** — the remaining ~10.5 min is deliberate slack for
questions, a slow laptop, and a demo that misbehaves. Don't spend it in advance.

**Run sheet**

The deck has **two halves**. Modules **0–2** are **local** operations — `build`
and `run`, everything on the attendee's own machine. Modules **3–4** are
**delivery** — `push` and `pull`, out to a registry. The menu slide and every
section divider carry that label, and "Two halves of the loop" (Docker's four
verbs) sits at the Module 3 divider as the pivot between them.

| # | Module | Half | Talk | Lab | Total |
|---|--------|------|------|-----|-------|
| — | Cover · slide-as-artifact · menu · lab card | — | 4m | — | 4m |
| 0 | Mise en Place — what a container image is | local | 10m | 4m — clone + `bazel build //samples/...` | 14m |
| 1 | Deterministic image builds | local | 12m | 6m — build/run the image vs the Dockerfile | 18m |
| 2 | Software catering (layers) | local | 7m | 10m — layer split, dedup, distroless | 17m |
| 3 | Shipping software | delivery | 6m | 8m — push to a registry | 14m |
| 4 | Cooking at scale | delivery | 5m | — (concept) | 5m |
| — | Wrap-up + Q&A | — | 6m | — | 6m |
| — | **Content total** | | | | **78m** |
| A | Appendix — validation · lazy push · comparison table | — | if time | daemonless structure tests | — |

**Lab 0 is the schedule risk.** `bazel build //...` pulls the Node/Slidev
toolchain, `@pypi`, the 162-deb `@graphviz_apt` and (via `//labs/...`)
`@tesseract_apt`/`@pocl_apt` — 10–20 min on conference wifi. The lab card says
`bazel test //samples/... //labs/... //tools/...` instead (the README's setup line),
and the README asks attendees to run it **before they arrive**. Anyone who can't
install Bazel takes the card's other column: fork (public), enable Actions, edit in
github.dev, and open a PR into their own fork's `main`. The labs workflow posts a
per-task table in the run's Summary. Say "into **your** fork, not upstream" out loud:
upstream runs the maintainers' checks. If the room is cold anyway, keep talking through Module 0
while it downloads; don't wait on it.

---

# Module 0 — Mise en Place: what a container image is (14m)

*Mise en place* — "everything in its place" — is the chef's disciplined prep
before the first pan goes on the heat. It's also exactly what determinism buys
you. This module builds the foundation: what an image is, the OCI format, and
where the `Dockerfile` model breaks down.

**Software: the secret sauce.** "Software is never *just* the code. Like a
béchamel, it's bound to the **pan it's cooked in** — the build — **and the dish
it's served in** — the runtime. Get the build slightly wrong and the sauce won't
set the same way twice. Every system today is deeply integrated, so the sauce has
to travel with everything it needs to be made *and* served."

**The secret sauce, in code.** "Our recipe is pure Python — but it names its own
pan. Three ingredients: app source, pip deps, and a **system layer**: the `dot`
binary. `pip` will never install `dot` for you. That system dependency — shelled
out to at runtime — is the 'special pan,' and it's the reason the rest of this
workshop exists. Which is the whole pitch for containers: don't hand someone a
jar of sauce and a shopping list — hand them the **microwavable dish**.
Everything it takes to make it *and* to serve it, sealed in one tray you can
reheat anywhere and get the same result. That tray is a container image — a stack
of **layers**." (On screen: `../samples/python/app.py#recipe`.)

*(The slide before this one carries `bechamel-to-sandwich.png` — béchamel setting
in a pan on the left, a finished sandwich plated on the right. **Say the metaphor
as you move between them**: "the sauce is the software; the pan it was made in is
the build, and the dish it's served in is the runtime — you ship all three." Two
sentences, then move on; it's the deck's opening image and it only has to plant
the sauce.)*

**Building an image with a Dockerfile.** "I can make a sandwich from whatever's in
the fridge between two slices. Tasty, maybe — but never reproducible. A
`Dockerfile` is that fridge sandwich: the `RUN apt-get` line grabs *today's*
ingredients." (On screen: `../samples/python/Dockerfile#dockerfile`, RUN
highlighted.)

*(On screen beside the code: `fridge-sandwich.png` — a sandwich built from random
leftovers. **Name it out loud**, because the picture is the argument: "tasty once,
and you could never make it twice." The `rotten-tomato.png` on the next slide is
the same joke sharpened — a hand plucking one bad tomato out of the crate — so
say "and this is the tomato you get tomorrow" as you advance.)*

**Black-box builds.** "`RUN apt-get install …` is grabbing a **random
tomato**: perfect today, rotten — or silently *different* — tomorrow. Three ways
it hurts: **non-deterministic** (`apt-get` today ≠ tomorrow; a security update can
change your base out from under you), **coarse cache invalidation** (one early
edit busts every layer below), and **the Docker socket** (`/var/run/docker.sock`:
security surface + CI bottleneck)."

**A sandwich of tars.** "Open the tray. We've been saying *layer* for a couple of
slides now — here's what one actually is. A container image is a **stack of tar
layers** plus a small JSON **image manifest** and config. That stack — and the shared agreement on
how to read it — is the **OCI standard**, the open format every registry and
runtime speaks. Each layer is an ingredient: base OS, runtime, deps, your code.
Your software is one ingredient; the image is the whole sandwich that carries it —
shipped together, not a sauce in a jar the customer has to assemble. And because
they're stacked *in order*: same ingredients, same order, and two sandwiches that
start the same **are** the same, right up to where they differ."

*(On screen: `sandwich-layers.png`, an exploded panino — app code as the top
bread, deps as the basil, runtime as the tomato and mozzarella, base OS as the
bottom slice. **Take the stack apart with your hand as you say it**; this is the
one picture the whole deck's vocabulary rests on, so it is worth naming every
layer aloud rather than gesturing at it.)*

**The same layer, only once.** "And that shared start has a name. Each layer ships
as a **blob**, and its name is the `sha256` **digest of its own bytes** — same
bytes, same digest, so it's stored, moved, and cached once. Think of a registry as
a **hash table**: the digest is the key, the blob is the value — that's
**content-addressed storage**, CAS, the acronym you'll see for the rest of the
talk. The **image manifest** is just the ordered list of keys — the layers, plus
a *config* that carries env and entrypoint. The **OCI standard** is every
registry and every
runtime agreeing on them. On screen: a croque monsieur and a croque madame — same
bread, béchamel, ham and gruyère, drawn once and shared; only the egg differs.
That one idea is what powers dedup, caching, and 'building without bytes' later.
And it's the hinge into Bazel: **content-addressed** is exactly how Bazel names
*its* outputs too."

*(If asked, going deeper — deliberately kept off the slide: a layer's digest is
taken over the **compressed** blob as it ships, while the config's
`rootfs.diff_ids` are digests of the **uncompressed** tars; and a multi-platform
**index** can sit above the manifest, pointing at one manifest per platform. Spec:
`github.com/opencontainers/image-spec`.)*

**Cooking containers with Bazel [Q1][Q2]** *(the "what is Bazel" beat is folded
in here as one sentence rather than its own slide — this is a BazelCon room)*.
"**Bazel** is a build system: it assembles artifacts from declared inputs,
reproducibly and at scale — you declare *what goes where* instead of scripting
steps, and it caches the rest. That trades the fridge-raid for a precise recipe.
"Bazel's pitch is **{Fast,
Correct} — choose two**, and *correct* means **hermetic**: no external influence,
so identical inputs → identical outputs. There are two *different* guarantees here
and you want both — but only one of them is 'hermeticity.' **Docker** gives you
**runtime isolation / self-contained delivery** — it bundles deps so the artifact
runs the same everywhere — but `docker build` itself is **not** hermetic
(`RUN apt-get` is networked, timestamped, order-sensitive). **Bazel** gives
**build hermeticity**: only declared inputs are visible; outputs are
content-addressed. Careful with the word: *hermetic* is a build-time property, so
Docker isolates the **plate** while Bazel makes the **kitchen** reproducible."

*(On screen: `bench-to-plate.png` — a cook's bench, a rack of knives and whisks
over rows of prepped bowls and stoppered jars, every one of them leader-lined down
onto a single finished plate. **Say the metaphor out loud** — "everything that goes
into the dish is on the bench before the cooking starts; nothing gets fetched
mid-recipe" — because that *is* declared inputs, and the picture is doing the work
the paragraph used to.)*

*(Staging: the slide is deliberately shorter than this — the opening "what is
Bazel" sentence shrank to a two-line lede, and the plate now takes the whole left
column at `max-h-80` with the Bazel and Docker blocks stacked beside it. You still
**say** the whole paragraph above. The keywords that left the paragraph landed in
the columns — "declared inputs" and "caches the rest" on the Bazel side — and
"two different guarantees, and you want both" now opens the footer, since the new
title no longer carries that thesis.)*

> **Lab 0 (4m):** `git clone … && bazel test //samples/... //labs/... //tools/...` — **not** `//...`,
> which drags in the Node toolchain the deck needs. Then note: these very slides
> are a build target — `bazel build //slides:build`. The deck is an artifact of
> the same graph as the images. CI even enforces it
> (`bazel query 'somepath(//slides, //samples/...)'` must be non-empty).
>
> *(On screen: the **Lab 0** slide — the problem, the commands, and a "you're done when" line. Leave it up for the whole lab; it closes Module 0.)*
>
> **The one rough edge: a C compiler.** The apt-layer images build `gawk` from
> source with whatever compiler Bazel finds on the laptop. Someone without one sees
> an error naming `gawk`, `cc` or `cpp:toolchain_type`. Don't debug it with them:
> "re-run with `--config=hermetic-cc`". That swaps in a pinned zig cc, and the
> image digests come out identical. It's opt-in, not the default, only because
> `labs/remote/README.md` §4 needs the host compiler to show what RBE catches.

---

# Module 1 — Deterministic image builds (18m)

**The lineage: three generations.** "This isn't Bazel's first image ruleset —
it's the **third**, and the workshop picks up where those tutorials left off.
**`rules_docker`** was the original; deprecated, drove a daemon. **`rules_oci`**
is the tar-based successor, widely used today. **`rules_img`** is the newer,
tar-in-CAS, daemonless approach — the subject of *this* talk. Both cards on the
slide are real talks and the links work: Alex Eagle's *Bazel and Docker with
`rules_oci`* (Bazel Community Day, 2023) and Malte Poll's *`rules_img`: A
Ground-Up Redesign* (BazelCon 2025), plus Tweag's announcement post. If you're
already on `rules_oci`, the concepts carry straight over; the delta is the
appendix slide **"Coming from `rules_oci`?"** at the very end."

**The payload: more than an interpreter.** "Our app needs more than Python on the
shelf — it needs the `dot` **system binary**. `graphviz` is a thin wrapper that
shells out to it. On the left is the actual guard in `app.py`; on the right, what
the app actually prints when `dot` isn't there. Note it doesn't *crash* — it
degrades to a `[skip]` and tells you which ingredient is missing. `pip` is blind
to `dot`; leave the daemon behind and that ghost has to become an **explicit
layer** — the special pan we now pack."

*(One extra beat, if the room is with you: `dot` is only one of graphviz's layout
**engines** — `neato`, `circo`, `twopi`, `fdp`, `sfdp`, `osage` draw the same
graph very differently — and each is its own system binary, with output-format
support coming from graphviz's plugin registry. That registry is the `config6`
caveat the distroless slide hits in Module 2. The sample deliberately keeps one
hardcoded `format="png"`; there is no `--engine` flag to demo.)*

**Meet `rules_img`.** One idea, in Malte's own framing: "**Build time produces
metadata; run time moves bytes.** Two consequences, and they're the two reasons to
care. **No daemon** — no socket, nothing privileged, nothing to keep running. And
it is **built for a remote cache and remote execution**: a layer is an ordinary
Bazel action, so it builds on **RBE** workers and lands in the **shared cache** —
built once, never rebuilt or re-downloaded anywhere. That's Module 4, and it's
where the whole design pays off."

*(Deliberately **do not** unpack the mechanics here — how big the manifest pull is,
what a descriptor is, what stays in CAS. It was on this slide and it bought
nothing: the audience has no use for it yet, and Module 4 ("Building Without
Bytes") is where the same facts land as a payoff instead of as trivia. The code is
on the "Assemble, don't run" slide a few beats later.)*

### Translating the Dockerfile — a six-slide walk

*(One directive per slide, then a recap. Roughly 20–30s each. Each slide's title
states the takeaway; a coloured kicker above it names the directive, so the
audience always knows which of the four we're on. Don't rush the `RUN apt-get` or
`ENTRYPOINT` slides — those are the two that draw questions.)*

*(The separate roadmap slide was cut — the four directives were being shown three
times over, as roadmap → four slides → recap. Its framing line now opens the
`FROM` slide: "four directives, one at a time — imperative steps that run become
declarative artifacts that assemble." "The whole translation" still closes the
walk.)*

**`FROM` · "A base is a digest, not a tag."** "`FROM python:3.12-slim-bookworm`
becomes an `images.pull` up in `MODULE.bazel` — that whole block is the repo's
real one, transcluded — and one line in the BUILD file that consumes it,
`base = image("python_base_img")`. Read the `digest` line out loud: that's the
point. It names *bytes*, not a tag, and it resolves **once when the module graph
loads**, never again at build time." *(If asked about `layer_handling = "lazy"`:
it's the non-default, and it's a live preview of Module 4's lazy-pull story — the
base's blobs are fetched only when something actually needs them. Here that's the
docker-save tarball the daemonless structure test reads.)*

**`RUN apt-get` · "The system dep becomes pinned bytes."** *(Say this — it came
off the slide to make room: `apt.install` is not a Bazel command, it's a **tag
class on a module extension** shipped by `rules_distroless`. In the loading phase
it reads `graphviz.yaml` — Debian snapshot ＋ arch ＋ package list — resolves it
against `graphviz.lock.json`, and generates the `@graphviz_apt` repo whose `:flat`
target is a tar of the resolved `.deb`s. Re-lock with
`bazel run @graphviz_apt//:lock`.)*
"The ghost ingredient
from Module 0 — here's where it stops being a ghost. Two halves, both
transcluded from real files. In `MODULE.bazel`, `apt.install` names the package
and points at `graphviz.lock.json`. Say what `apt.install` actually *is*, because
nobody guesses it: **not a Bazel command — a tag class on a module extension**
shipped by `rules_distroless`. It runs in the **loading** phase, reads
`graphviz.yaml` (Debian snapshot ＋ arch ＋ package list), resolves against the
lockfile, and generates the `@graphviz_apt` repo whose `:flat` target is a tar of
the resolved `.deb`s. Re-lock with `bazel run @graphviz_apt//:lock`. Then in the
BUILD file, `layer_from_tar` over `@graphviz_apt//:flat` turns those `.deb`s into
**one content-addressed layer**. So: **no build action needs the network**, and the
layer has a digest — which is what makes it cacheable and dedupable." *(Expect
"wait, where does it download then?" — the answer is the loading phase, and the
lockfile is what makes that safe. **Module 2** shows this same layer carrying a
whole image `FROM scratch`.)*

*(**"Couldn't I just pin APT in the Dockerfile instead?"** — the aside on the
slide, and the question that always comes. Full answer: **you already are** — and
it still isn't the same thing. `graphviz.yaml` pins `bullseye main` to the Debian
snapshot `20240210T223313Z`, and `graphviz.lock.json` pins all 162 `.deb`s by
name ＋ version ＋ sha256. What a Dockerfile can't give you is that guarantee:
even with pinned versions, `RUN apt-get` still **executes at build time, over the
network, with apt's own resolver making choices**. You pin a *command*; you don't
pin *bytes*. `rules_distroless` moves the resolution to the loading phase and
hands the build a lockfile plus a content-addressed tar.)*

**`RUN pip` · `COPY` · "Four steps, one layer."** *(Presenter: this slide is now
built to be read **against the previous one** — same two-block shape, same
`MODULE.bazel`-then-`BUILD.bazel` order, both halves transcluded. Say "same shape,
one package manager over" and let the audience notice the symmetry themselves;
that is the whole reason the layout was changed.)*
"Four imperative steps — copy the lock, pip install, `WORKDIR`, copy the source —
collapse into two rules, and they arrive the *same way the apt packages did*.
`pip.parse` is `rules_python`'s module extension: in the **loading** phase it
reads `requirements_lock.txt` and generates a **hub repo** — that's what
`hub_name = "pypi"` names, and it's the exact counterpart of `apt.install`
generating `@graphviz_apt`. So `requirement("graphviz")` is just a tidier way of
writing `@pypi//graphviz`. From there: `py_binary.deps` → **runfiles**, which is
the hermetic 3.12 interpreter ＋ the graphviz wheel ＋ `app.py` →
`include_runfiles = True` → **one tar → one layer**. And the same punchline as apt:
nothing is networked in a build action, because the resolution already happened at
load time — against the lockfile."

*(If someone asks what a "hub" is: one generated repo that fronts N per-wheel
repos, so BUILD files depend on a stable label instead of on version-mangled repo
names. Both `@pypi` and `@graphviz_apt` are hubs; that's the pattern, not a
rules_python quirk.)*

*(If someone asks about `aspect_rules_py` — this repo doesn't use it. It offers a
`py_image_layer` that splits interpreter / deps / source into three layers, which
is the right move for a real service. Here plain `rules_python` ＋ `rules_pkg`
keeps the layer boundary visible in one `pkg_tar`, which is what the slide is
teaching. Module 2 splits layers by hand for the same reason.)*

**`ENTRYPOINT` · "The entrypoint is a launcher."** "Look closely: there's **no
`python`**. It's `["/app/app", "--render", "/tmp/supply_chain.png"]`, not
`["python", "/app/app.py", …]`. `/app/app` is the `py_binary` bootstrap launcher —
at start-up it locates `app.runfiles` and execs the *hermetic* interpreter that
shipped inside the layer, not whatever `python` happens to be on the image's
PATH. `ENV` goes the same way: `env = {…}`, an attribute rather than a step."

*(The question this always draws is "so `rules_img` generates that launcher?" —
**no, and the correction is the point of the slide.** `py_binary` produced
`/app/app`; `pkg_tar(include_runfiles = True)` shipped it plus `app.runfiles/`
into `/app` on the previous slide. `entrypoint` is only a field in the image's
**OCI config JSON** — a pointer at a file that is already sitting in a layer.
`rules_img` writes a pointer; it runs nothing. That's the cleanest statement of
"declare, don't run" in the module, so land it and pause.)*

**The whole translation (recap).** *(The right-hand column says **Bazel**, not
`rules_img`, on purpose: only two of the four rows are actually `rules_img`. The
third column names the package that does the work, so read across.)*
"All four together — and this is where the honest answer to 'so I just need
`rules_img`?' is **no**. Read the third column: **`rules_img`** pulls the base
(`images.pull`), wraps tars (`layer_from_tar`) and declares the image
(`image_manifest`); **`rules_distroless`** does the system packages
(`apt.install`); **`rules_python`** does the Python ones (`pip.parse`, `py_binary`);
**`rules_pkg`** does the tarring (`pkg_tar`); and **`container_structure_test`**
does the validating. Five packages, one graph — nobody ships a monolith here.
Then the commands, because every Docker verb became a **target**:
`bazel build //samples/python:image` assembles, `bazel run …:image_load` runs,
`bazel run …:push` ships, `bazel test …:image_structure_test` validates. And note
the two with no Dockerfile counterpart at all — there is no directive for 'send
this to a registry'; `image_load` and `image_push` are targets, not daemon verbs."

**Assemble, don't run** *(the `build` stage)*. "Here's the real BUILD file —
transcluded, so it can't drift. Two rules: `layer_from_tar` wraps the `pkg_tar`
you just saw, and `image_manifest` declares the image. The `py_binary` and the
`pkg_tar` were on the last two slides; this is the last two rules. `bazel build
//samples/python:image` gives you a directory of **manifest ＋ config JSON** —
the layer blobs stay in the cache. No daemon; each layer's tar is built and
compressed **once**, so an edit re-assembles rather than re-tars."

**Load it like any other image** *(the `run` stage)*. "**Load** into your local
daemon, then `docker run`. Be precise about the loader: against a **containerd**
store it adds only the blobs the store lacks; a classic Docker daemon still takes
a full `docker load`. `bazel run //samples/python:image_load && docker run --rm
bwb/python-graphviz`."

**The "Docker tax" [Q6].** "People reach for Docker to *get* hermeticity — 'just
put it in a container.' Hermeticity's real payoff, though, is **efficiency**. Same
test suite, two ways: `py_test` under Bazel (sandboxed, cached, parallel,
incremental) vs. a `docker build` that pip-installs and runs pytest. Change one
line and re-run — Bazel re-runs only the affected test (**seconds**); Docker
invalidates at `COPY`, reinstalls, re-runs (**minutes**). Numbers are
machine-dependent, so we *measure* live; the point is the **order of magnitude**
per edit."

*(On screen: `docker-tax.png` — a kitchen pass blocked by a tin money box, a coin
going in before each plate may leave, and beside it a second pass the same plate
walks straight through. **Say the metaphor out loud**: "you pay the toll again for
every single plate." This is the first picture in eight slides of code, so give it
a beat and let the room breathe. If the plate has not been generated yet, the slide
shows a captioned slot — say the line anyway.)*

> **Lab 1 (6m):**
> `bazel run //samples/python:image_load && docker run --rm bwb/python-graphviz`
> → prints DOT, reports `dot not found` (the bare base has no `dot`).
> `docker build -t before samples/python && docker run --rm before`
> → the `apt-get`-installed graphviz renders the PNG. **That contrast is the
> workshop:** the system dep hidden in a `RUN` vs. forced into an explicit layer.
> (We make it *hermetic* in Module 2.) Then run
> `bazel run //benchmark/pytest_tax:compare` for the docker-tax timings.
>
> *(On screen: the **Lab 1** slide — the problem, the commands, and a "you're done when" line. Leave it up for the whole lab; it closes Module 1.)*

---

# Module 2 — Software catering (17m)

**Catering vs the one-pot bake.** "Order layers least → most volatile:
**1. base OS** (static) · **2. runtimes/deps** (infrequent) · **3. app code**
(most volatile). Bake everything into one dish — the **one-pot bake** — and
every edit re-cooks the whole thing. Run a **catering line**, each ingredient
prepped once, and you only remake the tray that changed. Bazel re-assembles only
the changed layer; a one-line edit in a multi-GB app is *seconds*, not minutes."

*(On screen: `catering-vs-onepot.png` — left, one fused cast-iron gratin with a
spoon breaking the crust; right, a steam-table line of `base` / `deps` / `app`
trays with only the `app` tray lifted off on a cook's hands. **Narrate the two
halves, don't let the plate sit there**: "to change one thing in the bake you have
to break into the whole dish — on the line you lift out one tray." Point at the
lime `UPDATE:` callout on the swapped tray; that's the incremental rebuild.)*

**Distroless: a sandwich without the bread.** "Take the base OS away, keep only
the filling — just the binary and what it needs, built **from scratch**. Say why
this is even possible, because it's the one line that moved here from a cut slide:
`apt.install` already resolved `dot` at **load** time into content-addressed
layers, so there is no `RUN` left that needs an OS underneath it. Read the
rule for what *isn't* there: there's no `base` at all, and because there's nothing
to inherit os/arch from, `platform` has to be spelled out. No shell, no package
manager, no apt database — nothing to exploit but the binary itself. And it closes
the `dot` gap from Module 0 *hermetically*: the same pinned apt layer from Module
1, now carrying a whole image on `scratch`." (On screen:
`../samples/distroless/BUILD.bazel#distroless`.)

*(On screen under the code: `sandwich-no-bread.png` — a party sub running the full
width of the slide, its roll split lengthwise and both halves lifted clean away,
leaving one unbroken run of filling. **Say it out loud**: "the bread is gone and
the filling is still the whole meal — that is `FROM scratch`." Trace the length of
it with your hand: nothing was taken *out of* the payload, only out from *under*
it.)*

*(This is the deck's one **container image** with **no base** — the sharpest form
of "layers are just artifacts, a base isn't special." Worth the 90 seconds; don't
rush it.)*

*(Caveat kept **off** the slide deliberately: `dot -V` runs, but `-Tpng`/`-Tsvg`
need the plugin registry at `/usr/lib/.../graphviz/config6` that Debian's postinst
normally writes via `dot -c`. Generating it at build time is the documented
follow-up — see the BUILD comment / TASK §8.4. Say it only if asked: it costs two
minutes Module 2 doesn't have, and it deflates the payoff a beat after you land
it.)*

**Two services, one shared blob** *(dedup [Q5])*. "Bazel's action cache keys every action
on **input digests + command + environment**; identical action → built once. Layers
are **content-addressed**, so a shared base/deps layer is built once and reused
across *every* image that references it. `//samples/shared_layers` builds two
images on the same base + a common layer; `bazel run //samples/shared_layers:digests`
prints the shared blob digests — prep once, plate twice. What can be shared? The
**base OS** and any **byte-identical** layer — deps, config. Content-addressing
makes the dedup automatic; nobody has to declare it." (On screen:
`../samples/shared_layers/BUILD.bazel#shared`.)

> **Lab 2 (10m):**
> 1. Edit one line in `app.py`, rebuild → only the app layer rebuilds (watch the
>    cache hits) — the catering line in action.
> 2. `bazel run //samples/distroless:image_load && docker run --rm bwb/distroless`
>    → runs `dot` (graphviz 2.43) from a fully hermetic, pinned layer on scratch.
> 3. `bazel run //samples/shared_layers:digests` → two images, shared base +
>    common layer; the diff prints the shared blob digests (built once).
>
> *(On screen: the **Lab 2** slide — the problem, the commands, and a "you're done when" line. Leave it up for the whole lab; it closes Module 2.)*

---

# Module 3 — Shipping software (14m)

*(The deck turns here. Modules 0–2 were **local** — `build` and `run` on your own
machine. Modules 3–4 are **delivery** — `push` and `pull`, out to a registry. The
section dividers and the menu both carry that split; say it out loud at this
divider so nobody has to infer it.)*

**Two halves of the loop.** "Docker has four verbs, and we've done the local
two — everything so far was `build` and `run` on your machine. The other two leave
the building: **push** (image → registry) is this module, **pull** (registry →
image) is Module 4. And delivery is where content addressing stops being trivia
and starts being **bandwidth**: a registry that already holds a blob doesn't want
it twice." *(This slide used to open Module 0 as a neutral lifecycle map. It works
much better here as the pivot — build/run are dimmed and checked off, push/pull
are what's next.)*

*(On screen: `docker-lifecycle.png` — the *same* sandwich going round a ring of
four kitchen scenes: hands assembling it at a prep bench (**build**), a waiter
setting it before a diner (**run**), a dispatch window handing it out boxed and
wax-sealed (**push**), a delivery cart arriving at another kitchen's back door with
the same box (**pull**). **Walk the ring with your finger and name the four verbs**;
the point the plate makes and the legend can't is that it is one sandwich the whole
way round.)*

**Push — daemonless, to any registry** *(the `push` stage)*. "`rules_img` gives
`image_push`: no Docker daemon, no socket — it talks straight to the registry API.
A registry is a **central pantry** keyed by content: push once, and every kitchen
pulls the exact same ingredient. Then do it — **Experiment 1**, and it needs no
infra at all, because **ttl.sh** is an anonymous, write-open registry: no local
registry, no daemon, no credentials, one-hour TTL. If you'd rather stay on the
machine, `//tools:local_registry` then `:push` gets you the same result."
*(rules_img also has `image_index` for multi-platform images; we don't ship one in
this workshop, so it stays out of the deck — measured, not asserted.)*

*(The standalone "registry: a shared pantry" slide was merged away, so say the
pantry framing once, here at Push — "push once, and every kitchen pulls the exact
same ingredient." The "one shelf, many dishes" bullet moved onto Module 4's
chain-wide pantry slide.)*

**Optimizing the push.** *(This slide was recut in the review pass. It used to be
"eager vs lazy" as two symmetric columns **before** either had been run — which
meant the audience read about lazy, whose demo is in the appendix, before they had
seen eager, whose demo was on the same slide. Now the doing is on the previous
slide and this one is purely the optimizations, in the order they pay off.)*
"Everything from here is about not moving bytes you don't have to. **One:** only
the blobs the registry doesn't already have go up — Module 2's dedup, now spent as
**bandwidth**, so a shared base layer uploads once. Run `push_eager` a second time
and watch it skip. **Two:** that push used `strategy = "eager"` — every blob rides
in the target's runfiles and `bazel run` uploads them. Zero infra, works anywhere,
much like rules_oci; it's what we just ran. **Three:** `strategy = "lazy"` streams
blobs **straight from a remote cache** to the registry, so nothing is staged into
runfiles — the win once images are huge or numerous. That needs infra we haven't
met yet, so it's Module 4, and Experiment 2 in the appendix. Rule of thumb: eager
for laptops and small images, lazy once you have a cache."

*(Precision worth keeping: lazy needs a remote **cache**, and that is all — `img`
talks REAPI ByteStream straight to the CAS. It does **not** need remote execution.
That distinction gets asked about every time.)*

> **Lab 3 (8m):**
> 1. **Zero-infra (Experiment 1 · eager):** `bazel run //samples/python:push_eager`
>    → pushes to `ttl.sh/bwb-graphviz:1h` (anonymous, 1-hour TTL). Run it twice;
>    the second push skips the blobs the registry already has.
> 2. **Local registry:** `bazel run //tools:local_registry` (registry:2 on
>    localhost:5000 — or, with no Docker daemon, a pinned `crane registry serve`
>    on the same port), then `bazel run //samples/python:push`; edit one line in
>    `app.py` and push again — only the changed app blob uploads (dedup by digest;
>    observed 7 → 3 → 2 blob transfers).
>
> *(On screen: the **Lab 3** slide — the problem, the commands, and a "you're done when" line. Leave it up for the whole lab; it closes Module 3.)*

---

# Module 4 — Cooking at scale (5m, concept)

**One base, N images.** "The `shared_layers` proof, at monorepo scale. Two
services there share a base + a config/lib layer; now imagine N. The base and
shared layers are built, cached, and pushed **once**, and each service adds only
its own app blob — so a 200-service monorepo ships ~200 small app blobs, not 200×
the base. That's what 'at scale' means: the shared bytes are paid for once, no
matter how many images."

*(On screen: `one-base-n-images.png` — one prep tray holding the bread-and-ham
foundation, leader-lined out to five open sandwiches numbered I–V that differ only
in the topping, trailing off to "… N". **Say it, don't just show it**: "same
foundation five times over; the only thing we paid for twice is the topping." The
row deliberately runs off the edge — that's the N.)*

**Building Without Bytes.** "Here's the name of the workshop, finally spelled out.
The whole game is to **compose and ship images by moving *references* — digests —
not layer *bytes*.** Three mechanics make that true: the layer tar lives in CAS
and only its `sha256` descriptor flows through the graph; push and pull move only
the blobs the other side lacks; and lazy pulls (`layer_handling = "lazy"`, already
in our `MODULE.bazel`) materialize a base layer's bytes only when a step needs
them. Most of an image is the base + deps you didn't change — so most of the time
you move *none* of the bytes."

*(On screen: `without-bytes.png` — paper dispatch dockets travelling build →
registry → run across the top, while the heavy provisions (prosciutto, herbs,
béchamel, pickles) sit parked on the CAS vault shelf below and never move. **Say
the metaphor**: "the tickets travel; the ham stays on the shelf." The plate was
re-cropped in the review pass to drop its ornamental title band, so it is tighter
than in older exports.)*

**The pantry, chain-wide: cache + RBE.** "Scale the shared pantry from one
kitchen to a restaurant *chain*. A **remote cache** is one content-addressed
pantry for the whole org — a blob built once is never rebuilt or re-downloaded
anywhere: CI, your laptop, the next PR. **Remote execution (RBE)** adds a brigade
of workers assembling layers in parallel from that same pantry. Content-addressing
is exactly what makes a shared cache *safe*: same digest ⇒ same bytes."

*(On screen: `remote-cache-rbe.png`. **The plate now labels itself** — it was
relabelled in the review pass, so the lettering reads `the remote cache — one
content-addressed pantry` at the centre, `your laptop`, `CI — the hotel pass`, and
`line cooks — RBE workers`. You no longer have to recite the mapping; **do** still
say the metaphor — "one commissary larder, and every kitchen on the chain draws
from it, including the five cooks working in parallel" — and trace the leader lines
from the one green jar out to the three kitchens with your hand.)*

*(Experiment 2 · lazy push lives in the **appendix** — it needs a remote cache to
be interesting, and Module 3's "Optimizing the push" slide points here for it. It
is demoable in the room: `bazel run //tools:local_cache` is a pinned static binary,
no account. Reach for it if someone asks about scale, or if you're running ahead.)*

*(The "Why `rules_img`" table was cut — it repeated the **lineage** slide from
Module 1 almost verbatim. The one line worth keeping is now on Takeaways: "coming
from `rules_oci`? Same declarative model; the win is keeping the bytes out of the
graph." The Dockerfile-vs-Bazel comparison table moved to the appendix.)*

> **Lab 4 (take-home):** the closing slide of Module 4 hands the room
> `labs/remote/README.md` §1. `bazel run //tools:local_cache`, then
> `bazel clean && bazel build --config=local-cache //samples/...` twice. The warm
> run reports a `remote cache hit` for nearly every process, right after a clean.
> No time is budgeted for it in the room: say "this one's homework" and move on
> to Takeaways. It keeps the menu's promise of a Lab in every module.

---

# Wrap-up + Q&A (5m)

**Takeaways.** *(Rewritten in the review pass to track the modules in order, so
each line is something the room actually watched happen rather than a slogan. Read
them as a walk back through the morning.)*
**Declare, don't script** — a layer is a build output, not a step a daemon runs
*(Module 1)* · **split by volatility** — independent layers build **in parallel**,
byte-identical ones **dedupe**, and `scratch` keeps the image thin *(Module 2)* ·
**go daemonless** — assemble, validate and push with no socket, nothing privileged
*(Modules 1–3)* · **share the pantry** — a remote cache (and RBE) means a layer
built once is never rebuilt, and push/pull move only the blobs the other side
lacks *(Modules 3–4)* · **build without bytes** — the tars stay in CAS, only
digests travel *(Module 4)* · **Slide-as-Code**.
**Mental model:** layers are granular, deterministic, cacheable build outputs —
not opaque blobs handed to you by a daemon.
**Point at the labs:** `bazel run //labs:progress` — the self-guided labs through
the three walls (build-time · the ghost · hardware) is the take-home. The deck
never used to mention it, so say it out loud here.

**One last loop (closer).** The Python sample renders *this repo's own dependency
graph* with `dot`, and the deck imports the result — a build action drawing the
graph of the build that produced this very slide.

**(If asked) ship as Docker vs. source-only? [Q7]** A Docker image is
self-contained, immutable, scannable — a **portable, dependency-bundled runtime**;
shipping source pushes a non-hermetic build onto the consumer. With Bazel you
emit **both from one graph** — a hermetic build *and* a self-contained image.
_(Kept as a backup answer to protect the 90-min budget.)_

**Q&A.** Multi-stage builds → layers/intermediate targets · secrets → never in a
cacheable layer; inject at runtime · legacy migration → base+deps split first,
tighten hermeticity incrementally · cross-arch → multi-platform indexes, no QEMU.

---

# Appendix (if time)

_Pulled out of the main flow to protect the 90-min budget; present only if time
allows or in answer to a question. In slide order: **why there's no `RUN` to
run**, **testing without a daemon** (`docker run` as a test? → cheaper tastes →
`container_structure_test` → when the image won't run), **looking inside an
image** (inspecting a layer outside Bazel → or skip the layout), **lazy push**
(Experiment 2; needs a remote cache, see the Module 4 note), the **Dockerfile vs
`rules_img` comparison table**, **what "hermetic" still borrowed**, and
**"Coming from `rules_oci`?"**. The two comparison slides are different, so name
the one you mean._

**`docker run` as a test?** "A test is a **self-verifying requirement** — the dish
that checks its own seasoning. (Toyota calls it *autonomation*: build quality in,
don't inspect it in afterward.) The tempting shortcut is to `docker build` a full
image, `docker run` it, and assert on the output. It works — but you cooked the
**whole dish** just to taste one bite: slow, daemon-bound, serialized. We want the
taste test *without* cooking the whole tray every time."

**Cheaper tastes than a full `docker run`.** *(Was titled "Daemonless validation",
but its second taste needs a daemon.)* "Two cheaper tastes before you cook the
whole dish: **test the entry script directly** with `py_test` (sandboxed, cached,
parallel; no image needed), and a quick **negative test** — `docker run
--network=none …` surfaces undeclared network deps. Handy, but not a proof; the
rigorous validator is Bazel's sandbox: only *declared files* are visible, so a
missing ingredient fails at build time, every time. Host *tools* are the
exception: that's the 'what hermetic still borrowed' slide."

**`container_structure_test` [Q3]** *(the `test` stage)*. "How do you check an image
is correct without a runtime? `container_structure_test` (GoogleContainerTools —
a community project, not an official Google product) with
`driver = "tar"` inspects the image's **files and config directly in the Bazel
sandbox** — no daemon. We assert the launcher + runfiles exist and the entrypoint
metadata (`fileExistenceTests` + `metadataTest`; no `commandTests`, which would
need execution). It runs in CI alongside every other test, and fans out in
parallel." (On screen: `../samples/python/image_test.yaml`.)

> **Lab (8m):** `bazel test //samples/python:image_structure_test` — daemonless
> validation of files + entrypoint metadata. Then break the entrypoint in
> `BUILD.bazel` and re-run to watch the metadata test fail in the sandbox (no
> container ever started).

**When the image won't run.** *(New in the 2026-09-09 review pass, answering
"how would you inspect the contents if the generated image is broken?". Moved
from the end of Module 2 to the appendix in the 2026-10-02 pass: the in-room
Lab 2 never stacks an apt layer on a distro base, so nobody hits `mergedusr`
there, and its real point is the blind spot of the structure test on the slide
before. Reach for it when someone asks "what can `container_structure_test`
actually test?". The failure is **Level 2's ★ Stretch B** (`mergedusr = False`
on purpose); the repo ships `mergedusr = True`, so say that, or people will
think the lab is broken.)*
"This is the module's one war story, and it is the sharpest gotcha in the repo
because it fails **silently**. Debian's `.deb`s still ship files under `/lib`;
a real distro base has `/lib` as a **symlink into `/usr`**. Layer a real
directory over that symlink and it doesn't merge — it **replaces** it, which
amputates the base's `/usr/lib`. Every binary in the image then fails to exec,
and the error you get is the world's least helpful: `no such file or directory`
about a file that is plainly right there. `mergedusr = True` rewrites
`./lib -> ./usr/lib` so the layers compose. (`//samples/distroless` deliberately
does *not* set it: on `scratch` there is no `/usr` symlink to clobber, and the
ELF interpreter has to stay at `/lib64`.)"

*(The **real** lesson, and the reason this slide exists: our
`container_structure_test` was **green** on those images. It `lstat`s paths in an
unpacked tar — it never **execs** anything. So it happily certified an image that
could not run a single binary. That sentence is lifted from
`.github/workflows/labs.yml`, where a `docker run` smoke job now covers the gap.
Say it plainly: a green structure test proves the *files* are there, not that the
**loader** can find them. This is also the shortest honest answer to "what can
`container_structure_test` actually test?" — TASK §12 wanted a whole slide for
that; this clause does the load-bearing part.)*

*(Then the two probes, both daemonless, both needing nothing installed:
`tar tf bazel-bin/labs/level2_ghost/app_layer.tar` answers "what is actually in
this layer?" — the repo already does exactly this in
`labs/level1_buildtime/layer_test.py` — and `bazel run //labs:explain -- level2`
decodes the structure test's bare `FAIL` into the check that failed. Do **not**
mention sparse layouts or lazy pulls here; the next two slides ("Inspecting a
layer outside Bazel", "Or skip the layout entirely") are where they live.)*

**Inspecting a layer outside Bazel.** *(New in the 2026-09-09 review pass,
answering "how can I use any tool to inspect the layer outside Bazel, and how do
I deal with the symlinks to ensure an OCI folder?". It lives in the appendix
because every explanation on it bottoms out in "the bytes aren't local", which is
Module 4 — and the appendix sits after Module 4, so the prerequisite is already
paid.)*
"Reasonable first move: point `skopeo` or `dive` at the image target. It bounces
off. Not a bug — `rules_img`'s **default** on-disk shape isn't an OCI layout at
all, it's a ***sparse*** one: a `sparse-oci-layout` marker where the spec wants
`oci-layout`, a `root.descriptor.json` where it wants `index.json`, and most
layers present only as a `<digest>.descriptor.json` **stub**. That *is* building
without bytes, seen from the filesystem. Your tools want a spec layout and there
isn't one."

*(Two ways out, and the slide shows both because they fail differently.*
***Path A — ask Bazel for a real layout:*** *the `oci_layout` and `oci_tarball`
output groups, surfaced as `//samples/python:image.oci` and `:image.oci.tar`.
Here is the trap, and it is the reviewer's actual question: `image.oci` is
spec-compliant and every blob in it is a **symlink into the execroot**. `du -sh`
reports **12K**; `du -shL` reports **78M**. Anything that copies or ships the
folder without dereferencing hands over a tree of dangling links. So: `cp -rL`,
or just take `image.oci.tar` — 78 MB of real bytes, zero symlinks, zeroed
timestamps. Both were verified in this repo, and every blob's content hashes to
its own filename, so the layout is genuinely valid.*
***Path B — skip the folder:*** *`bazel run //tools:local_registry -- --hermetic`,
push, then `crane manifest` / `crane config` / `crane export … | tar tf -`.
`crane export` flattens every layer into one tar — 8692 paths for our sample —
which is the most direct answer to "what is in this image?" without starting a
container. `grep bin/dot` on that listing comes back empty, which is the deck's
whole payload story, proven.*
*Say the omission out loud: `crane` is a **pinned static binary** (`//tools:crane_cli`),
so neither path needs anything installed. `dive`, `skopeo` and `umoci` are
deliberately **not** vendored — a workshop about hermeticity shouldn't send
people to unpinned host tools. And the last caveat is the honest one: under
`--remote_download_minimal` the bytes were never fetched at all —
`labs/remote/README.md` measured `image.tar` at 82 MB locally and 742 KB remote-only.
A layout is a set of dangling links until you ask for the bytes.)*

**Why there's no `RUN` to run [Q4].** *(Moved here out of Module 2 in the review
pass: it is the module's hardest slide to explain and it sat off the module's spine,
which is layer strategy rather than apt mechanics. The one load-bearing sentence —
packages resolve at load time and land as content-addressed artifacts — now opens
the distroless beat, so Module 2's argument still holds without it. Reach for this
when someone asks "but where did `RUN` go?", which they reliably do.)*
"We already replaced `RUN apt-get` back in Module 1 — `apt.install` plus
`layer_from_tar`. What I skipped was *why* it had to move, and it isn't stylistic.
**A build action shouldn't need the network.** There is no `RUN` to run because
an action isn't supposed to reach out mid-build; deps resolve in the **loading** phase
instead, and a **lockfile** pins exactly which bytes. The consequence is the
interesting part: the packages stop being a *step* and become **artifacts** —
ordinary content-addressed layers, same inputs → same digest. Which is the only
reason dedup and `scratch` work at all: byte-identical layers **dedupe**, and an
image with no base becomes possible. That's the whole trade — give up running
commands at build time, get reproducible bytes you can cache, dedupe, and ship."
*(Do **not** re-show `apt.install` here; Module 1's `RUN apt-get` slide already
has the code. This slide is the why.)*
*(Precision, because someone will check: Bazel's sandbox **allows** network by
default (`--sandbox_default_allow_network` is `true`, and this repo doesn't change
it). So say "shouldn't", not "can't". `--nosandbox_default_allow_network` is the
flag that makes it a rule.)*

**What "hermetic" still borrowed from the laptop.** *(New in the 2026-10-02
pass. Sits right after "Same artifact, two philosophies", whose table says
"Hermetic build: Yes"; this is the honest footnote to that row. Reach for it
when someone asks "is it *really* hermetic?", or right after an attendee hit
the compiler error during setup.)*
"Bazel decides what an action may **see**. It doesn't stop a rule from **using**
a tool that happens to be on your machine. Building this workshop turned up
five. The one that bites: `rules_distroless` builds `gawk` from source to write
`/var/lib/dpkg/status`, the file that lets scanners and `dpkg -l` see the apt
packages, and it compiles it with whatever C compiler it finds. No compiler, no
apt layers; a different gcc on a remote worker, and RBE rejects the action. The
fix ships opt-in: `--config=hermetic-cc`, a pinned zig cc, same image digest.
`python3` we fixed outright: the digest diff is now a `py_binary`. `bash` we
accept. Docker and `dot` are on purpose, they're the runtime and the renderer."
Close on the line that generalises: "remote execution, or a machine with
nothing installed, is how you find the rest."

**Coming from `rules_oci`? (the last appendix slide.)** *(New in the 2026-09-09
review pass, answering "the slides don't explain what is a `rules_img`-only
feature compared to `rules_oci`." It closes a real script↔deck gap: this file
used to promise "the full comparison is at the end" after that table had been
cut. Deliberately **migration**-framed rather than a feature matrix — the deck
teaches `rules_img` only, and a big comparison table would re-centre a ruleset
that was removed on purpose. It is also the last slide for a reason: answer it if
asked, don't lead with it.)*
"Same declarative model — composing layers in a `BUILD` file, bases pinned by
digest, daemonless push, structure tests all carry straight over. Four things are
genuinely new, and they're one idea wearing four hats: **keep the bytes out of
the graph.** Layer tars **stay in CAS** instead of being re-tarred and staged into
runfiles. `strategy = "lazy"` streams blobs from a remote cache over REAPI
ByteStream. Pulls are **shallow** — a base costs a manifest and a config, not its
layers. And the default layout is sparse, which you just saw."

*(**Be honest about how narrow the delta is.** Two slides earlier this script
already says eager push is "much like `rules_oci`" — so daemonless push is* not
*a differentiator, and claiming it would be exactly the unmeasured assertion this
deck otherwise avoids. Same for the trade-offs, which are real: `os` and
`architecture` are* not *yours to set in `rules_img` — the Bazel target platform
decides — and `exposed_ports`/`volumes` move into `config_fragment`. Someone who
relies on those will hit them on day one; better they hear it from you.*
*If the question behind the question is "should we migrate?", the useful answer is
that it doesn't have to be a cutover: the `oci_layout` output group feeds a
`rules_oci` target, and `image_manifest_from_oci_layout` goes the other way, so
the two can coexist in one graph while you move.)*

---

## Appendix — running everything

```bash
bazel build //samples/...                 # just the images — what Lab 0 runs
bazel build //...                         # images, slides, tools (+ Node toolchain)
bazel test  //...                         # unit + structure + invariant tests
bazel run //samples/python:image_load     # rules_img image (no dot) -> Docker
bazel run //samples/distroless:image_load # hermetic, pinned `dot` (scratch)
bazel run //benchmark/pytest_tax:compare  # the "docker tax" delta
bazel run //tools:local_registry          # registry:2 on localhost:5000
bazel run //samples/python:push           # push (only changed blobs) -> localhost:5000
bazel run //samples/python:push_eager     # Experiment 1: eager push -> ttl.sh (no infra)
bazel run //tools:local_cache             # a REAPI cache on localhost (no account)
bazel run //samples/python:push_lazy      # Experiment 2: lazy push (needs the cache)
bazel run //samples/shared_layers:digests # prove two images share layer blobs
bazel build //samples/python:image.oci    # a real OCI layout (blobs are symlinks!)
bazel build //samples/python:image.oci.tar # the same, packed: real bytes, no symlinks
bazel run //tools:crane_cli -- manifest localhost:5000/bwb/python-graphviz:latest
bazel build //samples/python:image --output_groups=digest  # the image digest, alone
bazel run //tools:render_graph -- //...   # draw the dependency graph
bazel run //slides:present                # live preview
bazel run //slides:export_pdf             # -> docs/building-without-bytes.pdf
bazel run //labs:progress                 # the self-guided labs (take-home)
```
