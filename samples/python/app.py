"""Render the workshop's software supply chain as a Graphviz diagram.

This is the dummy payload for the BazelCon talk's Python sample. It exists to
demonstrate a *non-hermetic system dependency*: the `graphviz` Python package
is a thin wrapper that shells out to the `dot` binary (the `graphviz` apt
package). Without `dot` on PATH there is no PNG — which is exactly the layer
we have to package explicitly when we leave the Docker daemon behind.

Two modes so the container is useful with or without the `dot` layer:

* default        -> print the DOT source (pure Python, always works)
* ``--render P`` -> also render a PNG to path ``P`` (needs the `dot` binary)
"""

from __future__ import annotations

import argparse
import shutil
import sys

import graphviz


def build_graph() -> graphviz.Digraph:
    """The supply chain that builds this very talk (the dogfooding loop)."""
    dot = graphviz.Digraph("supply_chain", comment="Building Without Bytes")
    dot.attr(rankdir="LR")
    dot.attr("node", shape="box", style="rounded")

    dot.node("src", "source\n(app.py, BUILD)")
    dot.node("deps", "pip deps\n(graphviz)")
    dot.node("sysdep", "system layer\n(dot binary)", style="rounded,filled", fillcolor="lightyellow")
    dot.node("image", "oci_image")
    dot.node("slides", "slides deck")
    dot.node("registry", "registry")

    dot.edge("src", "image")
    dot.edge("deps", "image")
    dot.edge("sysdep", "image")
    dot.edge("image", "registry")
    dot.edge("src", "slides", label="transclude")  # the deck imports this file
    return dot


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--render",
        metavar="PATH",
        help="render a PNG to PATH (requires the `dot` binary)",
    )
    args = parser.parse_args(argv)

    graph = build_graph()
    sys.stdout.write(graph.source)

    if args.render:
        if shutil.which("dot") is None:
            sys.stderr.write(
                "\n[skip] `dot` not found on PATH; printed DOT source only. "
                "Add the graphviz system layer to render a PNG.\n"
            )
            return 0
        out = graph.render(outfile=args.render, format="png", cleanup=True)
        sys.stderr.write(f"\n[ok] rendered {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
