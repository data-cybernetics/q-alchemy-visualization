from __future__ import annotations

import textwrap

from .schema import ExperimentConnection, ExperimentDiagram, ExperimentStep


class TextExperimentDrawer:
    """Unicode box-and-arrow renderer inspired by Qiskit's terminal drawings."""

    def __init__(
        self,
        diagram: ExperimentDiagram,
        *,
        width: int = 76,
        show_title: bool = False,
    ) -> None:
        self.diagram = diagram
        self.width = max(48, int(width))
        self.show_title = show_title

    @staticmethod
    def _put(chars: list[str], position: int, value: str) -> None:
        if 0 <= position < len(chars):
            chars[position] = value

    def _box(self, step: ExperimentStep, *, width: int | None = None) -> list[str]:
        width = self.width if width is None else max(32, int(width))
        inner = width - 2
        status = f" [{step.status.value}]" if step.status is not None else ""
        title_width = max(8, inner - len(status) - 1)
        title = step.title[:title_width]
        header = title + status.rjust(inner - len(title))

        lines = ["┌" + "─" * inner + "┐", "│" + header.ljust(inner) + "│"]
        for detail in step.details:
            wrapped = textwrap.wrap(
                str(detail),
                width=max(8, inner - 2),
                break_long_words=False,
                break_on_hyphens=False,
            ) or [""]
            for item in wrapped:
                lines.append("│ " + item.ljust(inner - 1) + "│")
        lines.append("└" + "─" * inner + "┘")
        return lines

    def _draw_linear(self) -> str:
        lines: list[str] = []
        if self.show_title:
            lines.extend([self.diagram.title, "=" * len(self.diagram.title), ""])
        center = self.width // 2
        for index, step in enumerate(self.diagram.steps):
            lines.extend(self._box(step))
            if index != len(self.diagram.steps) - 1:
                lines.append(" " * center + "│")
                lines.append(" " * center + "▼")
        return "\n".join(lines)

    def _graph_layers(self) -> tuple[list[list[tuple[str, ExperimentStep]]], dict[str, set[str]]]:
        keyed: list[tuple[str, ExperimentStep]] = []
        steps_by_key: dict[str, ExperimentStep] = {}
        for index, step in enumerate(self.diagram.steps):
            key = step.key or f"step-{index}"
            if key in steps_by_key:
                raise ValueError(f"duplicate experiment step key: {key!r}")
            steps_by_key[key] = step
            keyed.append((key, step))

        outgoing = {key: set() for key in steps_by_key}
        incoming = {key: set() for key in steps_by_key}
        for connection in self.diagram.connections:
            if connection.source not in steps_by_key:
                raise ValueError(f"unknown connection source: {connection.source!r}")
            if connection.target not in steps_by_key:
                raise ValueError(f"unknown connection target: {connection.target!r}")
            outgoing[connection.source].add(connection.target)
            incoming[connection.target].add(connection.source)

        order = {key: index for index, (key, _) in enumerate(keyed)}
        ready = sorted((key for key in steps_by_key if not incoming[key]), key=order.get)
        levels: dict[str, int] = {}
        visited: list[str] = []
        remaining_incoming = {key: set(values) for key, values in incoming.items()}
        while ready:
            key = ready.pop(0)
            visited.append(key)
            levels[key] = max((levels[parent] + 1 for parent in incoming[key]), default=0)
            for target in sorted(outgoing[key], key=order.get):
                remaining_incoming[target].discard(key)
                if not remaining_incoming[target] and target not in visited and target not in ready:
                    ready.append(target)
                    ready.sort(key=order.get)

        if len(visited) != len(steps_by_key):
            raise ValueError("experiment diagram connections must form a directed acyclic graph")

        layer_count = max(levels.values(), default=0) + 1
        layers: list[list[tuple[str, ExperimentStep]]] = [[] for _ in range(layer_count)]
        for key, step in keyed:
            layers[levels[key]].append((key, step))
        if any(len(layer) > 2 for layer in layers):
            raise ValueError("the text experiment drawer currently supports at most two steps per graph layer")

        # The compact split/merge drawer deliberately handles connections only between
        # adjacent layers.  Model a branch that must remain visible by carrying it through
        # an explicit step (for example, HELD OUT FROM FIT).
        for source, targets in outgoing.items():
            for target in targets:
                if levels[target] != levels[source] + 1:
                    raise ValueError(
                        "the text experiment drawer requires graph connections between adjacent layers"
                    )
        return layers, outgoing

    @staticmethod
    def _row_layout(
        layer: list[tuple[str, ExperimentStep]],
        *,
        canvas_width: int,
        gap: int,
    ) -> tuple[int, list[int], int]:
        if len(layer) == 1:
            box_width = min(76, canvas_width)
            lefts = [(canvas_width - box_width) // 2]
        else:
            box_width = (canvas_width - gap) // 2
            lefts = [0, box_width + gap]
        centers = [left + box_width // 2 for left in lefts]
        return box_width, centers, gap

    def _render_layer(
        self,
        layer: list[tuple[str, ExperimentStep]],
        *,
        canvas_width: int,
        gap: int,
    ) -> tuple[list[str], dict[str, int]]:
        box_width, centers, _ = self._row_layout(layer, canvas_width=canvas_width, gap=gap)
        boxes = [self._box(step, width=box_width) for _, step in layer]
        height = max(len(box) for box in boxes)
        rendered: list[str] = []
        if len(layer) == 1:
            left = (canvas_width - box_width) // 2
            for row in range(height):
                rendered.append(" " * left + boxes[0][row] + " " * (canvas_width - left - box_width))
        else:
            for row in range(height):
                left_line = boxes[0][row] if row < len(boxes[0]) else " " * box_width
                right_line = boxes[1][row] if row < len(boxes[1]) else " " * box_width
                rendered.append(left_line + " " * gap + right_line)
        return rendered, {key: center for (key, _), center in zip(layer, centers)}

    def _render_connector(
        self,
        source_layer: list[tuple[str, ExperimentStep]],
        target_layer: list[tuple[str, ExperimentStep]],
        source_centers: dict[str, int],
        target_centers: dict[str, int],
        outgoing: dict[str, set[str]],
        *,
        canvas_width: int,
    ) -> list[str]:
        edges = {
            (source, target)
            for source, _ in source_layer
            for target in outgoing[source]
            if target in target_centers
        }
        sources = [key for key, _ in source_layer]
        targets = [key for key, _ in target_layer]

        def blank() -> list[str]:
            return [" " for _ in range(canvas_width)]

        if len(sources) == 1 and len(targets) == 1:
            source = source_centers[sources[0]]
            target = target_centers[targets[0]]
            if (sources[0], targets[0]) not in edges:
                return []
            if source != target:
                raise ValueError("unsupported offset single-edge layout in text experiment drawer")
            line1, line2 = blank(), blank()
            self._put(line1, source, "│")
            self._put(line2, target, "▼")
            return ["".join(line1).rstrip(), "".join(line2).rstrip()]

        if len(sources) == 1 and len(targets) == 2:
            source_key = sources[0]
            if edges != {(source_key, targets[0]), (source_key, targets[1])}:
                raise ValueError("unsupported partial split in text experiment drawer")
            source = source_centers[source_key]
            left, right = sorted(target_centers.values())
            line1, line2, line3 = blank(), blank(), blank()
            self._put(line1, source, "│")
            for pos in range(left + 1, right):
                self._put(line2, pos, "─")
            self._put(line2, left, "┌")
            self._put(line2, right, "┐")
            self._put(line2, source, "┴")
            self._put(line3, left, "▼")
            self._put(line3, right, "▼")
            return ["".join(line1).rstrip(), "".join(line2).rstrip(), "".join(line3).rstrip()]

        if len(sources) == 2 and len(targets) == 2:
            expected = {(sources[0], targets[0]), (sources[1], targets[1])}
            if edges != expected:
                raise ValueError("the two-column text drawer currently supports aligned branch continuation only")
            line1, line2 = blank(), blank()
            for source_key, target_key in expected:
                source = source_centers[source_key]
                target = target_centers[target_key]
                if source != target:
                    raise ValueError("unaligned branch continuation is not supported")
                self._put(line1, source, "│")
                self._put(line2, target, "▼")
            return ["".join(line1).rstrip(), "".join(line2).rstrip()]

        if len(sources) == 2 and len(targets) == 1:
            target_key = targets[0]
            expected = {(sources[0], target_key), (sources[1], target_key)}
            if edges != expected:
                raise ValueError("unsupported partial merge in text experiment drawer")
            left, right = sorted(source_centers.values())
            target = target_centers[target_key]
            line1, line2, line3 = blank(), blank(), blank()
            self._put(line1, left, "│")
            self._put(line1, right, "│")
            for pos in range(left + 1, right):
                self._put(line2, pos, "─")
            self._put(line2, left, "└")
            self._put(line2, right, "┘")
            self._put(line2, target, "┬")
            self._put(line3, target, "▼")
            return ["".join(line1).rstrip(), "".join(line2).rstrip(), "".join(line3).rstrip()]

        raise ValueError("unsupported experiment graph shape for the initial text drawer")

    def _draw_graph(self) -> str:
        layers, outgoing = self._graph_layers()
        canvas_width = max(108, self.width)
        gap = 4
        lines: list[str] = []
        if self.show_title:
            lines.extend([self.diagram.title, "=" * len(self.diagram.title), ""])
        previous_layer = None
        previous_centers = None
        for layer in layers:
            rendered, centers = self._render_layer(
                layer, canvas_width=canvas_width, gap=gap
            )
            if previous_layer is not None and previous_centers is not None:
                lines.extend(
                    self._render_connector(
                        previous_layer,
                        layer,
                        previous_centers,
                        centers,
                        outgoing,
                        canvas_width=canvas_width,
                    )
                )
            lines.extend(line.rstrip() for line in rendered)
            previous_layer = layer
            previous_centers = centers
        return "\n".join(lines)

    def draw(self) -> str:
        if self.diagram.connections:
            return self._draw_graph()
        return self._draw_linear()
