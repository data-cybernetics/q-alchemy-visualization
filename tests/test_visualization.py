import json

import pytest

from q_alchemy.visualization import (
    DIAGRAM_SCHEMA_VERSION,
    ExperimentConnection,
    ExperimentDiagram,
    ExperimentStep,
    ExperimentStepStatus,
)


def _branched_diagram():
    return ExperimentDiagram(
        "WORKFLOW",
        (
            ExperimentStep("START", key="start"),
            ExperimentStep("LEFT", ("training",), ExperimentStepStatus.RUN, key="left"),
            ExperimentStep("RIGHT", ("validation",), key="right"),
            ExperimentStep("END", key="end"),
        ),
        (
            ExperimentConnection("start", "left"),
            ExperimentConnection("start", "right"),
            ExperimentConnection("left", "end"),
            ExperimentConnection("right", "end"),
        ),
    )


def test_wire_round_trip_preserves_payload():
    original = _branched_diagram()
    payload = original.to_dict()
    restored = ExperimentDiagram.from_dict(payload)

    assert payload["schema_version"] == DIAGRAM_SCHEMA_VERSION
    assert payload["kind"] == "experiment-diagram"
    assert restored.to_dict() == payload
    assert restored.draw(output="text") == original.draw(output="text")


def test_json_round_trip_preserves_payload():
    original = _branched_diagram()
    restored = ExperimentDiagram.from_json(original.to_json(indent=2))
    assert restored.to_dict() == original.to_dict()


def test_linear_wire_format_assigns_stable_ids():
    diagram = ExperimentDiagram("LINEAR", (ExperimentStep("A"), ExperimentStep("B")))
    payload = diagram.to_dict()
    assert [node["id"] for node in payload["nodes"]] == ["step-0", "step-1"]
    assert ExperimentDiagram.from_dict(payload).to_dict() == payload


def test_unknown_schema_version_is_rejected():
    payload = _branched_diagram().to_dict()
    payload["schema_version"] = 999
    with pytest.raises(ValueError, match="schema_version"):
        ExperimentDiagram.from_dict(payload)


def test_unknown_kind_is_rejected():
    payload = _branched_diagram().to_dict()
    payload["kind"] = "other"
    with pytest.raises(ValueError, match="diagram kind"):
        ExperimentDiagram.from_dict(payload)


def test_unknown_edge_endpoint_is_rejected():
    with pytest.raises(ValueError, match="unknown connection target"):
        ExperimentDiagram(
            "BROKEN",
            (ExperimentStep("A", key="a"),),
            (ExperimentConnection("a", "missing"),),
        )


def test_title_is_hidden_by_default_in_text():
    diagram = ExperimentDiagram("TITLE", (ExperimentStep("STEP"),))
    assert "TITLE" not in diagram.draw(output="text")
    assert "TITLE" in diagram.draw(output="text", show_title=True)


def test_mpl_round_trip_renders_same_node_count():
    matplotlib = pytest.importorskip("matplotlib")
    matplotlib.use("Agg")
    payload = _branched_diagram().to_dict()
    restored = ExperimentDiagram.from_dict(payload)
    figure = restored.draw(output="mpl")
    # One FancyBboxPatch per node; arrow patches are separate patch types.
    boxes = [patch for patch in figure.axes[0].patches if patch.__class__.__name__ == "FancyBboxPatch"]
    assert len(boxes) == len(payload["nodes"])
    assert figure.axes[0].get_title() == ""



def test_wire_status_uses_machine_value_and_accepts_legacy_display_value():
    step = ExperimentStep("RUN", status=ExperimentStepStatus.NOT_NEEDED, key="run")
    payload = step.to_dict()
    assert payload["status"] == "not-needed"
    assert ExperimentStep.from_dict(payload).status is ExperimentStepStatus.NOT_NEEDED

    legacy = dict(payload, status="NOT NEEDED")
    assert ExperimentStep.from_dict(legacy).status is ExperimentStepStatus.NOT_NEEDED


def test_generated_wire_ids_do_not_collide_with_explicit_ids():
    diagram = ExperimentDiagram(
        "IDS",
        (ExperimentStep("A"), ExperimentStep("B", key="step-0")),
    )
    ids = [node["id"] for node in diagram.to_dict()["nodes"]]
    assert ids == ["step-0-1", "step-0"]

def test_cycle_is_rejected_by_wire_model():
    with pytest.raises(ValueError, match="directed acyclic graph"):
        ExperimentDiagram(
            "CYCLE",
            (ExperimentStep("A", key="a"), ExperimentStep("B", key="b")),
            (ExperimentConnection("a", "b"), ExperimentConnection("b", "a")),
        )
