from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import json
from typing import Any, Mapping

DIAGRAM_SCHEMA_VERSION = 1

class ExperimentStepStatus(str, Enum):
    """Execution state displayed by experiment diagram renderers."""

    RUN = "RUN"
    SKIPPED = "SKIPPED"
    NOT_NEEDED = "NOT NEEDED"
    UNAVAILABLE = "UNAVAILABLE"
    FAILED = "FAILED"
    PENDING = "PENDING"
    NOT_RUN = "NOT RUN"


@dataclass(frozen=True)
class ExperimentStep:
    title: str
    details: tuple[str, ...] = ()
    status: ExperimentStepStatus | None = None
    key: str | None = None

    def to_dict(self, *, fallback_key: str | None = None) -> dict[str, Any]:
        key = self.key if self.key is not None else fallback_key
        if key is None:
            raise ValueError("an experiment step needs a key for wire serialization")
        return {
            "id": key,
            "title": self.title,
            "details": list(self.details),
            "status": (
                self.status.name.lower().replace("_", "-")
                if self.status is not None
                else None
            ),
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExperimentStep":
        status = data.get("status")
        parsed_status = None
        if status is not None:
            raw_status = str(status)
            member_name = raw_status.upper().replace("-", "_").replace(" ", "_")
            try:
                parsed_status = ExperimentStepStatus[member_name]
            except KeyError:
                # Accept the pre-wire display values for compatibility with callers
                # that may have persisted an early local ExperimentDiagram payload.
                parsed_status = ExperimentStepStatus(raw_status)
        return cls(
            title=str(data["title"]),
            details=tuple(str(item) for item in data.get("details", ())),
            status=parsed_status,
            key=str(data["id"]),
        )


@dataclass(frozen=True)
class ExperimentConnection:
    """Directed data/control-flow connection between two named experiment steps."""

    source: str
    target: str
    label: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "source": self.source,
            "target": self.target,
            "label": self.label,
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExperimentConnection":
        label = data.get("label")
        return cls(
            source=str(data["source"]),
            target=str(data["target"]),
            label=str(label) if label is not None else None,
        )


@dataclass(frozen=True)
class ExperimentDiagram:
    """Renderer-neutral experiment flow shared by text and graphical renderers.

    With no ``connections`` the steps are rendered as the original vertical sequence.
    Supplying connections turns the diagram into an explicit directed acyclic graph.  The
    first text renderer supports one- and two-column layers, which is enough to show the
    principal feasibility and state-estimation branches without baking workflow semantics
    into the renderer.
    """

    title: str
    steps: tuple[ExperimentStep, ...]
    connections: tuple[ExperimentConnection, ...] = ()

    def __post_init__(self) -> None:
        explicit_keys = [step.key for step in self.steps if step.key is not None]
        if len(explicit_keys) != len(set(explicit_keys)):
            raise ValueError("experiment step keys must be unique")
        known = set(explicit_keys)
        outgoing = {key: set() for key in known}
        incoming_count = {key: 0 for key in known}
        for connection in self.connections:
            if connection.source not in known:
                raise ValueError(f"unknown connection source: {connection.source!r}")
            if connection.target not in known:
                raise ValueError(f"unknown connection target: {connection.target!r}")
            if connection.target not in outgoing[connection.source]:
                outgoing[connection.source].add(connection.target)
                incoming_count[connection.target] += 1

        if self.connections:
            ready = [key for key, count in incoming_count.items() if count == 0]
            visited = 0
            while ready:
                key = ready.pop()
                visited += 1
                for target in outgoing[key]:
                    incoming_count[target] -= 1
                    if incoming_count[target] == 0:
                        ready.append(target)
            if visited != len(known):
                raise ValueError("experiment diagram connections must form a directed acyclic graph")

    def to_dict(self) -> dict[str, Any]:
        used_ids = {step.key for step in self.steps if step.key is not None}
        node_payloads: list[dict[str, Any]] = []
        for index, step in enumerate(self.steps):
            fallback = None
            if step.key is None:
                fallback = f"step-{index}"
                suffix = 1
                while fallback in used_ids:
                    fallback = f"step-{index}-{suffix}"
                    suffix += 1
                used_ids.add(fallback)
            node_payloads.append(step.to_dict(fallback_key=fallback))
        return {
            "schema_version": DIAGRAM_SCHEMA_VERSION,
            "kind": "experiment-diagram",
            "title": self.title,
            "nodes": node_payloads,
            "edges": [connection.to_dict() for connection in self.connections],
        }

    @classmethod
    def from_dict(cls, data: Mapping[str, Any]) -> "ExperimentDiagram":
        schema_version = int(data.get("schema_version", 0))
        if schema_version != DIAGRAM_SCHEMA_VERSION:
            raise ValueError(
                f"unsupported experiment diagram schema_version: {schema_version}"
            )
        kind = str(data.get("kind", ""))
        if kind != "experiment-diagram":
            raise ValueError(f"unsupported diagram kind: {kind!r}")
        return cls(
            title=str(data.get("title", "")),
            steps=tuple(ExperimentStep.from_dict(item) for item in data.get("nodes", ())),
            connections=tuple(
                ExperimentConnection.from_dict(item) for item in data.get("edges", ())
            ),
        )

    def to_json(self, *, indent: int | None = None) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True)

    @classmethod
    def from_json(cls, payload: str) -> "ExperimentDiagram":
        data = json.loads(payload)
        if not isinstance(data, Mapping):
            raise TypeError("experiment diagram JSON must decode to an object")
        return cls.from_dict(data)

    def draw(self, *, output: str = "text", show_title: bool = False) -> Any:
        if output == "text":
            from .text import TextExperimentDrawer

            return TextExperimentDrawer(self, show_title=show_title).draw()
        if output == "mpl":
            from .mpl import MatplotlibExperimentDrawer

            return MatplotlibExperimentDrawer(self, show_title=show_title).draw()
        raise ValueError("supported outputs are 'text' and 'mpl'")
