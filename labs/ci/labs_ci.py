#!/usr/bin/env python3
"""Lab checks, for CI and for anyone doing the labs.

    python3 labs/ci/labs_ci.py answers [--changed FILE] [--base REV] [--all]
        Run every lab's tasks and report which are done. With --changed (a
        list of edited paths) or --all, exit 1 if a lab you worked on is red.
        With --base, edits to a lab's own tests are reset to REV first, so a
        task is graded by the test as shipped.
    python3 labs/ci/labs_ci.py walkthrough level0|level1|level2|level3|level4|playground
        Maintainers: replay a lab README on the skeleton. Starts red, each
        README answer turns its task green, the stretch commands work. Every
        command and answer used here must appear verbatim in that README.
    python3 labs/ci/labs_ci.py linux-images [--simulate-mac]
        Every solution, playground and sample image is Linux on this machine's
        CPU, down to the ELF bytes of the interpreter and a wheel. With
        --simulate-mac, a Linux machine builds them as an Apple-silicon Mac would.
    python3 labs/ci/labs_ci.py readme
        Every Bazel target and relative link in the lab READMEs exists.
    python3 labs/ci/labs_ci.py slides [--run]
        Every Bazel target and --config the deck names exists. With --run,
        every command in its ```bash blocks runs, in slide order, and exits 0.

Uses the host python3, bazel and (for image checks) docker. Run from anywhere
inside the repo; edits made by `walkthrough` are always reverted.
"""

import argparse
import os
import re
import shutil
import subprocess
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "labs"))
import explain  # noqa: E402  (reuse its JUnit parsing)

BAZEL = "bazel"
ANSI = re.compile(r"\x1b\[[0-9;]*[A-Za-z]")
STATUS = re.compile(
    r"^(//\S+)\s+.*?(PASSED|FAILED TO BUILD|FAILED|NO STATUS|TIMEOUT|FLAKY)", re.M
)

# task -> which checks prove it. A key of None means "the whole test target".
LABS = {
    "level0": {
        "dir": "labs/level0_graphviz",
        "title": "Level 0 · Dockerfile → rules_img",
        "tasks": {
            "//labs/level0_graphviz:image_structure_test": {
                "the python base is underneath": "1",
                "Metadata Test": "1",
                "the dot binary is bundled": "2",
            },
        },
    },
    "level1": {
        "dir": "labs/level1_buildtime",
        "title": "Level 1 · Build-Time Trap",
        "tasks": {
            "//labs/level1_buildtime:app_test": {None: "1"},
            "//labs/level1_buildtime:image_layer_test": {None: "2"},
        },
    },
    "level2": {
        "dir": "labs/level2_ghost",
        "title": "Level 2 · Ghost",
        "tasks": {
            "//labs/level2_ghost:image_structure_test": {
                "tesseract engine binary is bundled": "1",
                "english language data is bundled": "1",
                "Metadata Test": "2",
            },
        },
    },
    "level3": {
        "dir": "labs/level3_hardware",
        "title": "Level 3 · Hardware Wall",
        "tasks": {
            "//labs/level3_hardware:image_structure_test": {
                "POCL CPU device": "1",
                "POCL CPU ICD is registered": "1",
            },
        },
    },
    "level4": {
        "dir": "labs/level4_shared",
        "title": "Level 4 · One interpreter, N images",
        "tasks": {
            "//labs/level4_shared:groups_test": {None: "0"},
            "//labs/level4_shared:shared_layers_test": {None: "1"},
        },
    },
    "playground": {
        "dir": "labs/playground",
        "title": "Playground",
        "tasks": {
            "//labs/playground:app_test": {None: "tests"},
            "//labs/playground:image_structure_test": {None: "tests"},
        },
    },
}

# Image smoke checks for `answers`, run only once a lab's tasks are green.
# (label, shell command, regex meaning "done", regex meaning "runs but not yet")
STRETCH = {
    "level0": [
        ("image runs", "{bazel} run //labs/level0_graphviz:image_load >/dev/null && "
         "docker run --rm bwb/level0-graphviz", r"rendered|layout engine", None),
        ("★ PNG renders with no runtime step", "docker run --rm bwb/level0-graphviz",
         r"\[ok\] rendered", r"layout engine"),
    ],
    "level2": [
        ("image runs", "{bazel} run //labs/level2_ghost:image_load >/dev/null && "
         "docker run --rm bwb/level2-ghost", r"^tesseract 5", None),
        ("★ OCR runs", "docker run --rm --network=none bwb/level2-ghost --ocr /app/sample.png",
         r"HERMETIC OCR", None),
    ],
    "level3": [
        ("★ kernel runs on CPU", "{bazel} run //labs/level3_hardware:image_load >/dev/null && "
         "docker run --rm --network=none bwb/level3-hardware", r"vector_add on OpenCL OK", None),
    ],
    "level4": [
        ("★ both services run", "{bazel} run //labs/level4_shared:api_load >/dev/null && "
         "{bazel} run //labs/level4_shared:worker_load >/dev/null && "
         "docker run --rm bwb/level4-api && docker run --rm bwb/level4-worker",
         r"worker: ticket OK", None),
    ],
}


# --- plumbing ----------------------------------------------------------------
def sh(cmd, timeout=3600):
    """Run a shell command at the repo root; return (rc, output)."""
    print("\n$ %s" % cmd, flush=True)
    p = subprocess.run(
        ["bash", "-o", "pipefail", "-c", cmd], cwd=ROOT, text=True,
        stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=timeout,
    )
    out = ANSI.sub("", p.stdout)
    tail = out.strip().splitlines()[-15:]
    print("\n".join("  | " + l for l in tail), flush=True)
    return p.returncode, out


def bazel_test(targets):
    """bazel test, then per-target status straight from Bazel's own summary."""
    rc, out = sh("%s test --keep_going --color=no --curses=no %s" % (BAZEL, " ".join(targets)))
    status = {t: s for t, s in STATUS.findall(out)}
    errors = [l for l in out.splitlines() if l.startswith("ERROR:")]
    return status, errors


def checks(target):
    """{testcase name: passed} from the target's JUnit XML."""
    pkg, name = target[2:].split(":")
    log = ROOT / "bazel-testlogs" / pkg / name / "test.xml"
    if not log.exists():
        return {}
    failed = {n for n, _ in explain.failures(log)}
    try:
        cases = [c.get("name", "?") for c in ET.parse(log).getroot().iter("testcase")]
    except ET.ParseError:
        return {}
    return {c: c not in failed for c in cases}


def failing_checks(target):
    return sorted(n for n, ok in checks(target).items() if not ok)


def norm(text):
    return re.sub(r"\s+", " ", text.replace("\\\n", " ")).strip()


def have_docker():
    return shutil.which("docker") and subprocess.run(
        ["docker", "info"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    ).returncode == 0


# --- answers -----------------------------------------------------------------
# A lab's own checks. The tasks are BUILD.bazel edits, so changes to these are
# set aside before grading. (The playground invites you to edit its tests.)
LAB_TEST = re.compile(r"^labs/level[^/]+/[^/]*(_test\.py|image_test[^/]*\.yaml)$")


def reset_lab_tests(paths, base):
    """git checkout `base` -- every edited lab test; returns the reset paths."""
    reset = []
    for path in sorted(p for p in paths if LAB_TEST.match(p)):
        rc, _ = sh("git checkout %s -- %s" % (base, path))
        if rc == 0:
            reset.append(path)
    return reset


def task_rows(lab, status):
    """[(task, ok, detail)] for one lab."""
    per_task = {}
    for target, mapping in LABS[lab]["tasks"].items():
        st = status.get(target, "NO STATUS")
        results = checks(target) if st in ("PASSED", "FAILED") else {}
        for key, task in mapping.items():
            if st not in ("PASSED", "FAILED"):
                ok, detail = False, "`%s` %s — see Build errors" % (target, st.lower())
            elif key is None:
                ok = st == "PASSED"
                detail = "" if ok else "%s %s" % (target, st.lower())
            else:
                hit = [ok for name, ok in results.items() if key in name]
                ok = st == "PASSED" or (bool(hit) and all(hit))
                detail = "" if ok else "check `%s` is red" % key
            prev = per_task.get(task, (True, []))
            per_task[task] = (prev[0] and ok, prev[1] + ([detail] if detail else []))
    return [(t, ok, "; ".join(d)) for t, (ok, d) in sorted(per_task.items())]


def readme_link(spec):
    base = "%s/%s/blob/%s" % (os.environ.get("GITHUB_SERVER_URL", ""),
                              os.environ.get("GITHUB_REPOSITORY", ""), os.environ.get("GITHUB_SHA", ""))
    if not os.environ.get("GITHUB_REPOSITORY"):
        return "%s (`%s`)" % (spec["title"], spec["dir"])
    return "[%s](%s/%s/README.md)" % (spec["title"], base, spec["dir"])


def cmd_answers(args):
    attempted, paths = set(), []
    if args.changed:
        paths = Path(args.changed).read_text().split()
    if args.all:
        attempted = set(LABS)
    elif args.changed:
        for lab, spec in LABS.items():
            d = spec["dir"] + "/"
            if any(p.startswith(d) and not p.startswith(d + "solution/")
                   and not p.endswith(".md") for p in paths):
                attempted.add(lab)

    reset = reset_lab_tests(paths, args.base) if args.changed and args.base else []

    targets = [t for spec in LABS.values() for t in spec["tasks"]]
    status, errors = bazel_test(targets)

    md = ["## Lab answers", ""]
    if reset:
        md += ["> [!NOTE]", "> These are the labs' own checks, so they were graded as shipped "
               "and your edits to them were set aside: " + ", ".join("`%s`" % p for p in reset), ""]
    if attempted:
        md.append("Labs you changed: " + ", ".join("**%s**" % l for l in sorted(attempted)))
    else:
        md.append("No lab files changed in this run — reporting only.")
    md += ["", "| Lab | Task | Status | Details |", "|---|---|---|---|"]
    red_attempted = set()
    green_labs = set()
    for lab, spec in LABS.items():
        rows = task_rows(lab, status)
        if all(ok for _, ok, _ in rows):
            green_labs.add(lab)
        elif lab in attempted:
            red_attempted.add(lab)
        for task, ok, detail in rows:
            if ok:
                state = "✅ done"
            elif lab in attempted or not (args.changed or args.all):
                state = "🔴 not yet"
            else:
                state, detail = "⚪ not started", ""
            md.append("| %s | %s | %s | %s |" % (readme_link(spec), task, state, detail))

    if have_docker():
        smoke = []
        for lab in sorted(green_labs & set(STRETCH)):
            for label, cmd, done, partial in STRETCH[lab]:
                _, out = sh(cmd.format(bazel=BAZEL), timeout=1800)
                if re.search(done, out, re.M) and not (partial and re.search(partial, out)):
                    state = "✅"
                elif "exec /app/app: no such file or directory" in out:
                    state = "🔴 the image cannot exec its binaries (mergedusr?)"
                elif label.startswith("★"):
                    state = "⚪ not yet (optional — see the README ★)"
                else:
                    state = "🔴 unexpected output: `%s`" % (out.strip().splitlines() or ["(none)"])[-1][:80]
                smoke.append("| %s | %s | %s |" % (LABS[lab]["title"], label, state))
        if smoke:
            md += ["", "### Images (docker run)", "", "| Lab | Check | Status |",
                   "|---|---|---|"] + smoke

    if errors:
        md += ["", "### Build errors", "", "```"] + errors[:20] + ["```"]
    _, why = sh("%s run //labs:explain 2>/dev/null" % BAZEL)
    if "✗" in why:
        md += ["", "<details><summary>Why is it red? (<code>bazel run //labs:explain</code>)"
               "</summary>", "", "```", why.strip(), "```", "</details>"]

    report = "\n".join(md) + "\n"
    print("\n" + report)
    summary = os.environ.get("GITHUB_STEP_SUMMARY")
    if summary:
        with open(summary, "a") as fh:
            fh.write(report)
    return 1 if red_attempted else 0


# --- walkthrough -------------------------------------------------------------
class WalkFailed(Exception):
    pass


class Walk:
    def __init__(self, lab):
        self.lab = lab
        self.dir = ROOT / LABS[lab]["dir"]
        self.readme = norm((self.dir / "README.md").read_text())
        self.backups = {}

    def say(self, msg):
        print("\n=== %s: %s" % (self.lab, msg), flush=True)

    def in_readme(self, *snippets):
        for s in snippets:
            if norm(s) not in self.readme:
                raise WalkFailed("README no longer contains: %r" % s)

    def backup(self, rel):
        path = ROOT / rel
        if rel not in self.backups:
            self.backups[rel] = path.read_bytes() if path.exists() else None
        return path

    def edit(self, rel, old, new, readme=()):
        self.in_readme(*readme)
        path = self.backup(rel)
        text = path.read_text()
        if old not in text:
            raise WalkFailed("%s: expected text not found: %r" % (rel, old))
        path.write_text(text.replace(old, new, 1))

    def write(self, rel, content):
        self.backup(rel).write_text(content)

    def add_layer(self, rel, name, src, readme=()):
        """layer_from_tar before the image, and the layer appended to `layers`."""
        self.edit(rel, "image_manifest(",
                  'layer_from_tar(\n    name = "%s",\n    src = "%s",\n)\n\nimage_manifest(' % (name, src),
                  readme=readme)
        self.edit(rel, '    layers = [":app_layer_img"],',
                  '    layers = [\n        ":app_layer_img",\n        ":%s",\n    ],' % name)

    def run(self, cmd, expect=None, rc=0, verbatim=True, timeout=3600):
        """Run a README command; rc=None accepts any exit code, "fail" needs non-zero."""
        if verbatim:
            self.in_readme(cmd)
        code, out = sh(cmd, timeout=timeout)
        if code == 125 and "extraction snapshot" in out:
            # containerd image store occasionally loses a parent snapshot
            # between `image_load` and `docker run`; the retry is not the lab.
            code, out = sh(cmd, timeout=timeout)
        if rc == "fail" and code == 0:
            raise WalkFailed("expected `%s` to fail, it passed" % cmd)
        if isinstance(rc, int) and code != rc:
            raise WalkFailed("`%s` exited %d (wanted %d)" % (cmd, code, rc))
        if expect and not re.search(expect, out, re.M):
            raise WalkFailed("`%s` output lacks /%s/" % (cmd, expect))
        return out

    def tests(self, **want):
        """want: {target-name: "pass" | [substrings of the checks that must fail]}."""
        pkg = "//" + LABS[self.lab]["dir"]
        targets = {("%s:%s" % (pkg, k)): v for k, v in want.items()}
        status, errors = bazel_test(list(targets))
        for target, expected in targets.items():
            st = status.get(target, "NO STATUS")
            if expected == "pass":
                if st != "PASSED":
                    raise WalkFailed("%s is %s, wanted PASSED\n%s" % (target, st, "\n".join(errors)))
                continue
            if st != "FAILED":
                raise WalkFailed("%s is %s, wanted FAILED" % (target, st))
            actual = failing_checks(target)
            if expected and (len(actual) != len(expected) or
                             not all(any(e in a for a in actual) for e in expected)):
                raise WalkFailed("%s: failing checks %s, wanted %s" % (target, actual, expected))

    def restore(self):
        for rel, data in self.backups.items():
            path = ROOT / rel
            if data is None:
                path.unlink(missing_ok=True)
            else:
                path.write_bytes(data)
        self.backups.clear()


def walk_level0(w):
    b = "labs/level0_graphviz/BUILD.bazel"
    w.say("start: red with three checks")
    w.run("bazel test //labs/level0_graphviz:image_structure_test", rc="fail")
    w.tests(image_structure_test=["python base", "dot binary", "Metadata"])
    w.run("bazel run //labs:explain -- level0", expect="the dot binary is bundled")
    w.say("task 1: FROM + ENTRYPOINT")
    w.edit(b, '    layers = [":app_layer_img"],\n    platform = LINUX,',
           '    base = image("python_base_img"),\n    entrypoint = [\n        "/app/app",\n'
           '        "--render",\n        "/tmp/supply_chain.png",\n    ],\n'
           '    layers = [":app_layer_img"],\n    platform = LINUX,',
           readme=['base = image("python_base_img"),', '"/app/app", "--render", "/tmp/supply_chain.png",'])
    w.tests(image_structure_test=["dot binary"])
    w.say("task 2: the dot layer")
    w.add_layer(b, "graphviz_layer_img", "@graphviz_lab_apt//:flat",
                readme=['name = "graphviz_layer_img", src = "@graphviz_lab_apt//:flat",',
                        '":graphviz_layer_img",'])
    w.tests(image_structure_test="pass")
    if have_docker():
        w.say("stretch: render the PNG")
        w.run("bazel run //labs/level0_graphviz:image_load")
        w.run("docker run --rm bwb/level0-graphviz", expect="no layout engine support", rc=None)
        w.run("docker run --rm --entrypoint sh bwb/level0-graphviz "
              "-c 'dot -c && /app/app --render /tmp/g.png'", expect=r"\[ok\] rendered /tmp/g.png")
        w.run("docker build -t before samples/python && docker run --rm before",
              expect=r"\[ok\] rendered")


def walk_level1(w):
    b = "labs/level1_buildtime/BUILD.bazel"
    w.say("start: both tasks red, the build_test green")
    w.run("bazel test //labs/level1_buildtime:app_test", rc="fail")
    w.run("bazel test //labs/level1_buildtime:image_layer_test", rc="fail")
    w.run("bazel test //labs/level1_buildtime:image_build_test")
    w.run("bazel run //labs:explain -- level1", expect="ModuleNotFoundError")
    w.say("task 1 (and with it task 2): the wheel")
    w.edit(b, "    deps = [],", '    deps = [requirement("cryptography")],',
           readme=['deps = [requirement("cryptography")],'])
    w.tests(app_test="pass", image_layer_test="pass", image_build_test="pass")
    w.run("bazel build //labs/level1_buildtime:app_layer")
    w.run("tar tf bazel-bin/labs/level1_buildtime/app_layer.tar | grep _rust",
          expect=r"_rust\.abi3\.so")


def walk_level2(w):
    b = "labs/level2_ghost/BUILD.bazel"
    w.say("start: task 0 green, three checks red")
    w.run("bazel test //labs/level2_ghost:app_test")
    w.run("bazel test //labs/level2_ghost:image_structure_test", rc="fail")
    w.tests(image_structure_test=["tesseract engine", "english language", "Metadata"])
    w.run("bazel run //labs:explain -- level2", expect="TESSDATA_PREFIX")
    w.say("task 1: the engine layer")
    w.add_layer(b, "tesseract_layer_img", "@tesseract_apt//:flat",
                readme=['name = "tesseract_layer_img", src = "@tesseract_apt//:flat",',
                        '":tesseract_layer_img",'])
    w.tests(image_structure_test=["Metadata"])
    w.say("task 2: TESSDATA_PREFIX")
    w.edit(b, '    entrypoint = ["/app/app"],',
           '    entrypoint = ["/app/app"],\n'
           '    env = {"TESSDATA_PREFIX": "/usr/share/tesseract-ocr/5/tessdata/"},',
           readme=['env = {"TESSDATA_PREFIX": "/usr/share/tesseract-ocr/5/tessdata/"},'])
    w.tests(image_structure_test="pass")
    if not have_docker():
        return
    w.say("stretch A: OCR for real")
    w.edit(b, '    srcs = [":app"],', '    srcs = [\n        ":app",\n        "sample.png",\n    ],',
           readme=["`sample.png`"])
    w.run("bazel run //labs/level2_ghost:image_load")
    w.run("docker run --rm bwb/level2-ghost --ocr /app/sample.png", expect="HERMETIC OCR")
    w.say("stretch B: mergedusr = False passes the test, breaks the image")
    w.edit("MODULE.bazel",
           '    manifest = "//labs/level2_ghost:tesseract.yaml",\n    mergedusr = True,',
           '    manifest = "//labs/level2_ghost:tesseract.yaml",\n    mergedusr = False,',
           readme=["`mergedusr = False`"])
    w.run("bazel test //labs/level2_ghost:image_structure_test")
    w.run("bazel run //labs/level2_ghost:image_load && docker run --rm bwb/level2-ghost",
          expect="exec /app/app: no such file or directory", rc="fail")


def walk_level3(w):
    b = "labs/level3_hardware/BUILD.bazel"
    w.say("start: task 0 green, two checks red")
    w.run("bazel test //labs/level3_hardware:app_test")
    w.run("bazel test //labs/level3_hardware:image_structure_test", rc="fail")
    w.tests(image_structure_test=["POCL CPU device", "POCL CPU ICD"])
    w.run("bazel run //labs:explain -- level3", expect="pocl.icd")
    w.say("task 1: the POCL layer")
    w.add_layer(b, "pocl_layer_img", "@pocl_apt//:flat",
                readme=['name = "pocl_layer_img", src = "@pocl_apt//:flat",', '":pocl_layer_img",'])
    w.tests(image_structure_test="pass")
    if have_docker():
        w.say("stretch: a kernel on the CPU")
        w.run("bazel run //labs/level3_hardware:image_load")
        w.run("docker run --rm bwb/level3-hardware", expect=r"vector_add on OpenCL OK: \[11\.0, 22\.0, 33\.0\]")


def walk_level4(w):
    b = "labs/level4_shared/BUILD.bazel"
    w.say("start: task 0 green, task 1 red")
    w.run("bazel test //labs/level4_shared:groups_test")
    w.run("bazel test //labs/level4_shared:shared_layers_test", rc="fail")
    w.run("bazel run //labs:explain -- level4", expect="layer_from_binary")
    w.say("task 1: one layer per runfiles group")
    w.edit(b, 'load("@rules_img//img:layer.bzl", "layer_from_tar")',
           'load("@rules_img//img:layer.bzl", "layer_from_binary")',
           readme=['load("@rules_img//img:layer.bzl", "layer_from_binary")'])
    for n in ("api", "worker"):
        w.edit(b, 'pkg_tar(\n    name = "%s_layer",\n    srcs = [":%s"],\n    include_runfiles = True,\n'
                  '    package_dir = "/app",\n)\n' % (n, n),
               'layer_from_binary(\n    name = "%s_layers",\n    binary = ":%s_layered",\n    path = "/app/%s",\n)\n' % (n, n, n),
               readme=['binary = ":%s_layered",' % n, 'path = "/app/%s",' % n])
        w.edit(b, 'layer_from_tar(\n    name = "%s_layer_img",\n    src = ":%s_layer",\n    optimize = True,\n)\n\n' % (n, n), "")
        w.edit(b, '    layers = [":%s_layer_img"],' % n, '    layers = [":%s_layers"],' % n,
               readme=['layers = [":%s_layers"],' % n])
    w.tests(groups_test="pass", shared_layers_test="pass")
    w.run("bazel build //labs/level4_shared:image_api //labs/level4_shared:image_worker")
    out = w.run("diff <(grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/level4_shared/image_api_manifest.json) \\\n"
                "     <(grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/level4_shared/image_worker_manifest.json)",
                rc=1, verbatim=False)
    changed = [l for l in out.splitlines() if l.startswith("<")]
    if len(changed) != 2:
        raise WalkFailed("level4: %d manifest lines differ, the README says two" % len(changed))
    if have_docker():
        w.say("stretch: both services run from the shared layers")
        w.run("bazel run //labs/level4_shared:api_load && docker run --rm bwb/level4-api",
              expect=r"api: signed ticket")
        w.run("bazel run //labs/level4_shared:worker_load && docker run --rm bwb/level4-worker",
              expect=r"worker: ticket OK")


def walk_playground(w):
    b = "labs/playground/BUILD.bazel"
    y = "labs/playground/image_test.yaml"
    digests = "grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/playground/image_manifest.json"
    w.say("start")
    w.run("bazel run //labs/playground:app", expect="declared dependencies")
    w.run("bazel test //labs/playground/...")
    docker = have_docker()
    if docker:
        w.run("bazel run //labs/playground:image_load")
        w.run("docker run --rm bwb/playground", expect="hello from a layer")

    w.say("1: manifest + config")
    w.run("bazel build //labs/playground:image")
    w.run("cat bazel-bin/labs/playground/image_manifest.json", expect='"layers"')
    w.run("cat bazel-bin/labs/playground/image_config.json", expect='"Entrypoint"')

    w.say("2: only the config layer moves")
    w.backup("labs/playground/greeting.txt")
    w.run(digests + " > /tmp/before")
    w.run('echo "edited" >> labs/playground/greeting.txt')
    w.run("bazel build //labs/playground:image")
    out = w.run(digests + " | diff /tmp/before -", rc=1)
    if out.count("\n<") + out.startswith("<") != 2:
        raise WalkFailed("task 2: wanted exactly 2 digests to move:\n" + out)
    w.restore()
    w.run("bazel build //labs/playground:image")
    w.run(digests + " | diff /tmp/before -", verbatim=False)  # byte-identical again

    w.say("3: a dependency appears")
    w.edit(b, 'load("@rules_python//python:defs.bzl", "py_binary", "py_test")',
           'load("@rules_python//python:defs.bzl", "py_binary", "py_test")\n'
           'load("@labs_pypi//:requirements.bzl", "requirement")',
           readme=['load("@labs_pypi//:requirements.bzl", "requirement")'])
    w.edit(b, "    deps = [],", '    deps = [requirement("cryptography")],',
           readme=['deps = [requirement("cryptography")],'])
    w.run("bazel run //labs/playground:app", expect=r"cryptography\s+\d")
    w.restore()

    w.say("4 + 5: a file, an env var, and their assertions")
    w.write("labs/playground/extra.txt", "extra\n")
    w.edit(b, '    srcs = ["greeting.txt"],', '    srcs = ["greeting.txt", "extra.txt"],',
           readme=["`config_layer`'s `srcs`"])
    w.edit(b, '    env = {"PLAYGROUND_CONFIG": "/etc/playground/greeting.txt"},',
           '    env = {"PLAYGROUND_CONFIG": "/etc/playground/greeting.txt", "MODE": "demo"},')
    w.edit(y, "\nmetadataTest:", '  - name: "extra file"\n    path: "/etc/playground/extra.txt"\n'
           "    shouldExist: true\n\nmetadataTest:", readme=["`fileExistenceTests`", "`metadataTest`"])
    w.edit(y, '      value: "/etc/playground/greeting.txt"',
           '      value: "/etc/playground/greeting.txt"\n    - key: "MODE"\n      value: "demo"')
    w.run("bazel test //labs/playground:image_structure_test")
    w.restore()

    w.say("6: one base, N images")
    w.run("bazel build //labs/playground:image //labs/level1_buildtime/solution:image")
    out = w.run("diff <(grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/playground/image_manifest.json) "
                "<(grep -o 'sha256:[0-9a-f]*' bazel-bin/labs/level1_buildtime/solution/image_manifest.json)",
                rc=1)
    hunks = re.findall(r"^(\d+)(?:,(\d+))?[acd]", out, re.M)
    touched = {n for a, z in hunks for n in range(int(a), int(z or a) + 1)}
    if touched & {2, 3, 4, 5}:
        raise WalkFailed("task 6: base layer digests differ:\n" + out)
    w.run("bazel run //samples/shared_layers:digests", expect="SHARED")

    w.say("9: look inside a layer")
    w.run("bazel build //labs/playground:app_layer")
    w.run("tar tf bazel-bin/labs/playground/app_layer.tar | head", expect="^app/", rc=None)  # SIGPIPE
    if not docker:
        return

    w.say("7: distroless, then no base")
    w.run("bazel run //samples/distroless:image_load && docker run --rm bwb/distroless",
          expect="dot - graphviz version")
    w.edit(b, '    base = image("python_base_img"),\n', "", readme=["delete `base`"])
    w.run("bazel run //labs/playground:image_load", verbatim=False)
    w.run("docker run --rm bwb/playground", expect="exec /app/app: no such file or directory",
          rc="fail")
    w.restore()

    w.say("8: a system dependency of your own (jq)")
    w.write("labs/playground/jq.yaml", (ROOT / "labs/level2_ghost/tesseract.yaml").read_text()
            .split("packages:")[0] + 'packages:\n  - "jq"\n')
    w.backup("labs/playground/jq.lock.json")
    w.edit("MODULE.bazel", 'use_repo(apt, "pocl_apt")\n', 'use_repo(apt, "pocl_apt")\n\n'
           'apt.install(\n    name = "jq_apt",\n    manifest = "//labs/playground:jq.yaml",\n'
           '    mergedusr = True,\n)\nuse_repo(apt, "jq_apt")\n',
           readme=['name = "jq_apt", manifest = "//labs/playground:jq.yaml", mergedusr = True,'])
    w.run("bazel run @jq_apt//:lock", timeout=1800)
    w.edit("MODULE.bazel", '    name = "jq_apt",\n', '    name = "jq_apt",\n'
           '    lock = "//labs/playground:jq.lock.json",\n',
           readme=['lock = "//labs/playground:jq.lock.json",'])
    w.edit(b, "image_manifest(", 'layer_from_tar(\n    name = "jq_layer_img",\n'
           '    src = "@jq_apt//:flat",\n)\n\nimage_manifest(')
    w.edit(b, '        ":config_layer_img",\n', '        ":config_layer_img",\n        ":jq_layer_img",\n')
    w.run("bazel run //labs/playground:image_load && "
          "docker run --rm --entrypoint /usr/bin/jq bwb/playground --version", expect=r"^jq-")
    w.restore()

    w.say("10: the Docker tax")
    w.run("bazel run //benchmark/pytest_tax:compare", expect="per-edit docker tax")

    w.say("11: push it")
    w.run("bazel run //tools:local_registry", rc=None)
    w.run("curl -fsS http://localhost:5000/v2/", verbatim=False)
    w.edit(b, 'load("@rules_img//img:load.bzl", "image_load")',
           'load("@rules_img//img:load.bzl", "image_load")\n'
           'load("@rules_img//img:push.bzl", "image_push")',
           readme=['load("@rules_img//img:push.bzl", "image_push")'])
    w.backup(b)
    (ROOT / b).write_text((ROOT / b).read_text() + '\nimage_push(\n    name = "push",\n'
                          '    image = ":image",\n    registry = "localhost:5000",\n'
                          '    repository = "bwb/playground",\n    tag = "latest",\n)\n')
    w.in_readme('repository = "bwb/playground",')
    w.run("bazel run //labs/playground:push", expect="localhost:5000/bwb/playground:latest")
    w.run("bazel run //labs/playground:push", expect="blob transfers", verbatim=False)


WALKS = {
    "level0": walk_level0,
    "level1": walk_level1,
    "level2": walk_level2,
    "level3": walk_level3,
    "level4": walk_level4,
    "playground": walk_playground,
}


def cmd_walkthrough(args):
    w = Walk(args.lab)
    try:
        WALKS[args.lab](w)
    except WalkFailed as e:
        print("\n✗ %s walkthrough: %s" % (args.lab, e))
        return 1
    finally:
        w.restore()
        if args.lab == "playground":
            sh("bazel run //tools:local_registry -- stop >/dev/null 2>&1 || true")
    print("\n✓ %s: the README works, start to finish" % args.lab)
    return 0


# --- readme ------------------------------------------------------------------
LABEL = re.compile(r"(?<![\w@/:+])(@[\w-]+)?//[\w/.+-]*(?::[\w.+-]+|/\.\.\.)")
LINK = re.compile(r"\]\(([^)#\s]+)(?:#[^)]*)?\)")
# Targets a README asks you to *create*, so they do not exist yet.
TO_BE_CREATED = {
    "//labs/playground:push",  # task 11
    "//labs/playground:jq.yaml", "//labs/playground:jq.lock.json",  # task 8
    "@jq_apt//:lock", "@jq_apt//:flat",
}


def cmd_readme(_args):
    readmes = sorted((ROOT / "labs").glob("**/README.md"))
    labels, bad = set(), []
    for md in readmes:
        text = md.read_text()
        labels |= {m.group(0) for m in LABEL.finditer(text)}
        for link in LINK.findall(text):
            if not re.match(r"[a-z]+:", link) and not (md.parent / link).exists():
                bad.append("%s: broken link %s" % (md.relative_to(ROOT), link))
    for label in sorted(labels - TO_BE_CREATED):
        rc = subprocess.run([BAZEL, "query", label], cwd=ROOT, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        print("%s %s" % ("ok     " if rc == 0 else "MISSING", label), flush=True)
        if rc != 0:
            bad.append("no such target: %s" % label)
    for b in bad:
        print("::error::%s" % b)
    return 1 if bad else 0


# --- slides ------------------------------------------------------------------
SLIDES = ROOT / "slides" / "slides.md"
FENCE = re.compile(r"^\s*```(\w*)")
RUNNABLE = ("bazel ", "docker ", "tar ")
CD = "cd bazelcon-2026-workshop-docker && "  # we already run in the checkout
# Lines in a ```bash block that are real but must not run here, and why.
SLIDE_SKIP = {
    "git clone ": "CI is already in the checkout",
    "cache.corp": "placeholder endpoint",
}


def slide_commands():
    """(line, command) for every runnable line of the deck's ```bash blocks.

    `$ `-prefixed lines are transcripts (a scenario, not a recipe) and
    ```console blocks are output; both only get the static label check."""
    cmds, lang, pending = [], None, None
    for n, line in enumerate(SLIDES.read_text().splitlines(), 1):
        m = FENCE.match(line)
        if m:
            lang = None if lang is not None else m.group(1)
            continue
        if lang != "bash":
            continue
        text = line.split(" # ")[0].split("   #")[0].strip() if not line.lstrip().startswith("#") else ""
        if pending:
            start, acc = pending
            text = acc + " " + text
        if text.endswith("\\"):
            pending = (pending[0] if pending else n, text[:-1].strip())
            continue
        start = pending[0] if pending else n
        pending = None
        text = text[len(CD):] if text.startswith(CD) else text
        if text.startswith(RUNNABLE) or any(text.startswith(s) for s in SLIDE_SKIP):
            cmds.append((start, text))
    return cmds


def cmd_slides(args):
    text = SLIDES.read_text()
    bad = []
    for label in sorted({m.group(0) for m in LABEL.finditer(text)}):
        rc = subprocess.run([BAZEL, "query", label], cwd=ROOT, stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL).returncode
        print("%s %s" % ("ok     " if rc == 0 else "MISSING", label), flush=True)
        if rc != 0:
            bad.append("slides.md names %s, which does not exist" % label)
    configs = set(re.findall(r"^\w+:([\w-]+)", (ROOT / ".bazelrc").read_text(), re.M))
    for cfg in sorted(set(re.findall(r"--config=([\w-]+)", text)) - configs):
        bad.append("slides.md uses --config=%s, which .bazelrc does not define" % cfg)
    if args.run and not bad:
        # The deck assumes you did README.md's setup, so run exactly that first
        # — it gets tested too. `test --build_tests_only` skips what the tests
        # don't need: a slide that reads bazel-bin must build first.
        setup = next(l.split("#")[0].strip() for l in (ROOT / "README.md").read_text()
                     .splitlines() if l.startswith("bazel test //"))
        try:
            rc, _ = sh(setup, timeout=3600)
            if rc != 0:
                bad.append("README.md setup exits %d: %s" % (rc, setup))
            for n, cmd in slide_commands():
                why = next((w for s, w in SLIDE_SKIP.items() if s in cmd), None)
                if why or "…" in cmd:
                    print("\nskip slides.md:%d  %s  (%s)" % (n, cmd, why or "elided on the slide"))
                    continue
                rc, _ = sh(cmd, timeout=1800)
                if rc != 0:
                    bad.append("slides.md:%d exits %d: %s" % (n, rc, cmd))
        finally:
            sh("bazel run //tools:local_cache -- stop >/dev/null 2>&1 || true")
            sh("bazel run //tools:local_registry -- stop >/dev/null 2>&1 || true")
    for b in bad:
        print("::error file=slides/slides.md::%s" % b)
    print("\n%s slides.md commands" % ("✗" if bad else "✓"))
    return 1 if bad else 0


# --- linux-images ------------------------------------------------------------
ELF_MACHINE = {"amd64": 0x3E, "arm64": 0xB7}  # ELF e_machine


def cmd_linux_images(args):
    """Images are Linux whatever the host: //tools/platforms:defs.bzl's LINUX."""
    import json
    import platform
    import tarfile

    flags = "--platforms=//tools/platforms:macos_aarch64_simulated" if args.simulate_mac else ""
    arch = "arm64" if args.simulate_mac or platform.machine() in ("arm64", "aarch64") else "amd64"
    pkgs = ["//samples/...", "//labs/playground:all"] + [
        "//%s/solution:all" % spec["dir"] for lab, spec in LABS.items() if lab != "playground"]
    _, out = sh("%s query 'kind(image_manifest, %s)'" % (BAZEL, " + ".join(pkgs)))
    images = [l for l in out.splitlines() if l.startswith("//")]
    bad = []
    rc, _ = sh("%s build %s %s" % (BAZEL, flags, " ".join(images)))
    if rc != 0:
        bad.append("the images don't build")
    else:
        # samples/distroless pins linux_amd64 on purpose (scratch: no base to follow).
        pinned = {"//samples/distroless:image": "amd64"}
        for image in images:
            _, out = sh("%s cquery %s --output=files %s 2>/dev/null" % (BAZEL, flags, image))
            cfg = next(l for l in out.splitlines() if l.endswith("_config.json"))
            got = json.loads((ROOT / cfg).read_text())
            want = pinned.get(image, arch)
            if (got["os"], got["architecture"]) != ("linux", want):
                bad.append("%s is %s/%s, wanted linux/%s" % (image, got["os"], got["architecture"], want))
        # The bytes, not just the label: Level 1's interpreter and wheel.
        _, out = sh("%s cquery %s --output=files 'kind(pkg_tar, deps(//labs/level1_buildtime/solution:image))' "
                    "2>/dev/null" % (BAZEL, flags))
        layer = next(l for l in out.splitlines() if l.endswith(".tar"))
        with tarfile.open(ROOT / layer) as tar:
            members = [m for m in tar.getmembers() if m.isfile() and
                       m.name.endswith(("/bin/python3.12", "/_rust.abi3.so"))]
            for m in members:
                head = tar.extractfile(m).read(20)
                if head[:4] != b"\x7fELF" or head[18] != ELF_MACHINE[arch]:
                    bad.append("%s in %s is not a Linux %s binary" % (m.name, layer, arch))
        if len(members) < 2:
            bad.append("%s lacks the interpreter or the cryptography wheel" % layer)
    for b in bad:
        print("::error::%s" % b)
    print("\n%s %d images are linux/%s" % ("✗" if bad else "✓", len(images), arch))
    return 1 if bad else 0


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    sub = ap.add_subparsers(dest="cmd", required=True)
    a = sub.add_parser("answers")
    a.add_argument("--changed", help="file listing changed paths")
    a.add_argument("--all", action="store_true", help="treat every lab as attempted")
    a.add_argument("--base", help="revision to reset edited lab tests to (the fork point)")
    w = sub.add_parser("walkthrough")
    w.add_argument("lab", choices=sorted(WALKS))
    li = sub.add_parser("linux-images")
    li.add_argument("--simulate-mac", action="store_true", help="build as an Apple-silicon Mac would")
    sub.add_parser("readme")
    sl = sub.add_parser("slides")
    sl.add_argument("--run", action="store_true", help="also run every ```bash command")
    args = ap.parse_args()
    return {"answers": cmd_answers, "walkthrough": cmd_walkthrough, "readme": cmd_readme,
            "slides": cmd_slides, "linux-images": cmd_linux_images}[args.cmd](args)


if __name__ == "__main__":
    sys.exit(main())
