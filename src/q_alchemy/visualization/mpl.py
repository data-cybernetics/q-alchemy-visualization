from __future__ import annotations

import textwrap
from typing import Any

from .schema import ExperimentDiagram, ExperimentStep
from .text import TextExperimentDrawer


class MatplotlibExperimentDrawer:
    """Simple Matplotlib renderer for an :class:`ExperimentDiagram`.

    The graphical drawer intentionally shares the text drawer's graph-layer semantics:
    linear diagrams remain linear, while explicit connections can form the one- and
    two-column split/merge DAGs used by feasibility and state-estimation workflows.
    Matplotlib is imported lazily so text-only users do not need the visualization extra.
    """

    def __init__(self, diagram: ExperimentDiagram, *, show_title: bool = False) -> None:
        self.diagram = diagram
        self.show_title = show_title

    @staticmethod
    def _matplotlib():
        try:
            import matplotlib.pyplot as plt
            from matplotlib.patches import FancyArrowPatch, FancyBboxPatch
        except ImportError as exc:  # pragma: no cover - exercised only without optional dep
            raise ImportError(
                "Matplotlib output requires the optional visualization dependency. "
                "Install it with: pip install 'q-alchemy-visualization[mpl]'"
            ) from exc
        return plt, FancyArrowPatch, FancyBboxPatch

    def _layers(self) -> tuple[list[list[tuple[str, ExperimentStep]]], dict[str, set[str]]]:
        if self.diagram.connections:
            return TextExperimentDrawer(self.diagram)._graph_layers()
        layers = [
            [(step.key or f"step-{index}", step)]
            for index, step in enumerate(self.diagram.steps)
        ]
        outgoing: dict[str, set[str]] = {}
        for index, layer in enumerate(layers):
            key = layer[0][0]
            outgoing.setdefault(key, set())
            if index + 1 < len(layers):
                outgoing[key].add(layers[index + 1][0][0])
        return layers, outgoing

    @staticmethod
    def _node_lines(step: ExperimentStep, *, width: int) -> list[str]:
        status = f" [{step.status.value}]" if step.status is not None else ""
        lines = [step.title + status]
        for detail in step.details:
            lines.extend(
                textwrap.wrap(
                    str(detail),
                    width=width,
                    break_long_words=False,
                    break_on_hyphens=False,
                ) or [""]
            )
        return lines

    def draw(self) -> Any:
        plt, FancyArrowPatch, FancyBboxPatch = self._matplotlib()
        layers, outgoing = self._layers()

        has_branch = any(len(layer) == 2 for layer in layers)
        single_width = 7.8
        branch_width = 5.2
        branch_x = 3.15
        vertical_gap = 1.0

        nodes: dict[str, dict[str, Any]] = {}
        layer_heights: list[float] = []
        for layer in layers:
            layer_height = 0.0
            for key, step in layer:
                wrap_width = 46 if len(layer) == 2 else 70
                lines = self._node_lines(step, width=wrap_width)
                height = max(1.15, 0.46 + 0.29 * len(lines))
                width = branch_width if len(layer) == 2 else single_width
                nodes[key] = {"step": step, "lines": lines, "width": width, "height": height}
                layer_height = max(layer_height, height)
            layer_heights.append(layer_height)

        layer_centers: list[float] = []
        top = 0.0
        for height in layer_heights:
            center = top - height / 2
            layer_centers.append(center)
            top = center - height / 2 - vertical_gap

        for layer_index, layer in enumerate(layers):
            if len(layer) == 1:
                xs = [0.0]
            else:
                xs = [-branch_x, branch_x]
            for (key, _), x in zip(layer, xs):
                nodes[key]["x"] = x
                nodes[key]["y"] = layer_centers[layer_index]
                nodes[key]["layer"] = layer_index

        fig_width = 13.0 if has_branch else 9.5
        fig_height = max(5.0, abs(top) * 0.78 + 1.4)
        fig, ax = plt.subplots(figsize=(fig_width, fig_height))

        # Draw orthogonal connectors behind the nodes.  All currently supported DAG
        # edges connect adjacent layers, matching the text renderer's invariant.
        for layer_index in range(len(layers) - 1):
            source_keys = [key for key, _ in layers[layer_index]]
            target_keys = [key for key, _ in layers[layer_index + 1]]
            edges = [
                (source, target)
                for source in source_keys
                for target in outgoing.get(source, set())
                if target in target_keys
            ]
            if not edges:
                continue
            source_bottoms = {
                key: nodes[key]["y"] - nodes[key]["height"] / 2 for key in source_keys
            }
            target_tops = {
                key: nodes[key]["y"] + nodes[key]["height"] / 2 for key in target_keys
            }
            mid_y = (min(source_bottoms.values()) + max(target_tops.values())) / 2

            for source in {source for source, _ in edges}:
                x = nodes[source]["x"]
                ax.plot([x, x], [source_bottoms[source], mid_y], linewidth=1.2, color="black")

            for source, target in edges:
                sx = nodes[source]["x"]
                tx = nodes[target]["x"]
                if sx != tx:
                    ax.plot([sx, tx], [mid_y, mid_y], linewidth=1.2, color="black")

            for target in {target for _, target in edges}:
                tx = nodes[target]["x"]
                arrow = FancyArrowPatch(
                    (tx, mid_y),
                    (tx, target_tops[target]),
                    arrowstyle="-|>",
                    mutation_scale=12,
                    linewidth=1.2,
                    color="black",
                    shrinkA=0,
                    shrinkB=2,
                )
                ax.add_patch(arrow)

        for key, node in nodes.items():
            x = node["x"]
            y = node["y"]
            width = node["width"]
            height = node["height"]
            box = FancyBboxPatch(
                (x - width / 2, y - height / 2),
                width,
                height,
                boxstyle="round,pad=0.04,rounding_size=0.08",
                fill=False,
                edgecolor="black",
                linewidth=1.2,
            )
            ax.add_patch(box)
            ax.text(
                x,
                y,
                "\n".join(node["lines"]),
                ha="center",
                va="center",
                fontsize=9.5,
                linespacing=1.25,
            )

        if self.show_title:
            ax.set_title(self.diagram.title, fontsize=13, pad=14)
        x_limit = branch_x + branch_width / 2 + 0.6 if has_branch else single_width / 2 + 0.6
        ax.set_xlim(-x_limit, x_limit)
        ax.set_ylim(top + 0.15, 0.55)
        ax.axis("off")
        fig.tight_layout()
        return fig
