"""Render this repo's *first-party* Bazel dependency graph to a PNG via `dot`.

A utility `bazel run` target (NOT hermetic): it shells out to `bazel query`
and the `dot` binary, and writes into the source tree. That is the point of
the live demo — `bazel run //tools:render_graph -- //tools:render_graph`
draws a graph that contains its own node.

The query is scoped to `intersect //...` so the graph shows only this repo's
own targets (a clean, slide-sized picture) rather than the thousands of
external dependency nodes.

The nested `bazel query` uses a separate `--output_base` so it does not block
on the lock held by the outer `bazel run` server.
"""

from __future__ import annotations

import os
import subprocess
import sys
import tempfile


def main(argv: list[str]) -> int:
    target = argv[1] if len(argv) > 1 else "//..."

    ws = os.environ.get("BUILD_WORKSPACE_DIRECTORY")
    if not ws:
        sys.stderr.write("must be run via `bazel run //tools:render_graph`\n")
        return 2

    out_dir = os.path.join(ws, "slides", "graphs")
    os.makedirs(out_dir, exist_ok=True)
    safe = target.strip("/").replace("/", "_").replace(":", "-").replace(".", "all") or "graph"
    dot_path = os.path.join(out_dir, f"{safe}.dot")
    png_path = os.path.join(out_dir, f"{safe}.png")

    with tempfile.TemporaryDirectory(prefix="render-graph-ob-") as output_base:
        query = subprocess.run(
            ["bazel", f"--output_base={output_base}", "query",
             f"deps({target}) intersect //...", "--output=graph", "--noshow_progress"],
            cwd=ws, text=True, capture_output=True,
        )
    if query.returncode != 0:
        sys.stderr.write(query.stderr)
        return query.returncode

    with open(dot_path, "w") as fh:
        fh.write(query.stdout)

    render = subprocess.run(
        ["dot", "-Tpng", "-Gbgcolor=transparent", "-Granksep=0.5",
         "-Nshape=box", "-Nstyle=rounded", "-Nfontname=Helvetica",
         dot_path, "-o", png_path],
        text=True, capture_output=True)
    if render.returncode != 0:
        sys.stderr.write("`dot` failed (is graphviz installed?)\n")
        sys.stderr.write(render.stderr)
        return render.returncode

    rel = os.path.relpath(png_path, ws)
    print(f"wrote {rel} (+ .dot) for deps({target})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
