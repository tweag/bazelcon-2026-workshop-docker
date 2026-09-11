"""Why is my rung red?   bazel run //labs:explain

`container_structure_test` reports through a JUnit XML file, so a failure shows
in the Bazel console as a bare `level=fatal msg=FAIL` with no detail at all.
The per-check reason lives in `bazel-testlogs/<pkg>/<target>/test.xml`; this
prints it, for every lab test you have run.

    bazel run //labs:explain             # every failed lab test
    bazel run //labs:explain -- level2   # only targets matching "level2"
"""

import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

RULE = "─" * 70


def label_for(xml_path: Path, testlogs: Path) -> str:
    rel = xml_path.parent.relative_to(testlogs)  # e.g. labs/level2_ghost/image_structure_test
    return "//%s:%s" % (rel.parent.as_posix(), rel.name)


def failures(xml_path: Path):
    try:
        root = ET.parse(xml_path).getroot()
    except ET.ParseError:
        return []
    out = []
    for case in root.iter("testcase"):
        for kind in ("failure", "error"):
            node = case.find(kind)
            if node is not None:
                msg = (node.text or node.get("message") or "").strip()
                out.append((case.get("name", "?"), msg))
    return out


def main(argv) -> int:
    workspace = Path(os.environ.get("BUILD_WORKSPACE_DIRECTORY", "."))
    testlogs = workspace / "bazel-testlogs"
    needle = argv[0] if argv else ""

    if not (testlogs / "labs").is_dir():
        print("No lab test results yet. Run a rung first, e.g.:")
        print("    bazel test //labs/level2_ghost:image_structure_test")
        return 0

    found = False
    for xml_path in sorted((testlogs / "labs").rglob("test.xml")):
        label = label_for(xml_path, testlogs)
        if needle and needle not in label:
            continue
        fails = failures(xml_path)
        if not fails:
            continue
        found = True
        print("\n%s\n  %s\n%s" % (RULE, label, RULE))
        for name, msg in fails:
            # py_test failures land here as a bare "exited with error code 1";
            # the real traceback is in the plain-text log next to the XML.
            if msg.startswith("exited with error code"):
                print("  ✗ test process failed — full output in:")
                print("      %s" % (xml_path.parent / "test.log"))
                continue
            print("  ✗ %s" % name)
            for line in msg.splitlines():
                print("      %s" % line)

    if not found:
        suffix = ' matching "%s"' % needle if needle else ""
        print("No failing lab tests recorded%s." % suffix)
        print("(Only rungs you have actually run show up here.)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
