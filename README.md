# Q-Alchemy Visualization

`q-alchemy-visualization` provides a small, renderer-neutral model for experiment
flow diagrams, plus text and Matplotlib renderers. It is designed for reports
produced by Q-Alchemy libraries, but the diagram model can be used independently.

The package contains no service client, credentials, feasibility decisions, or
quantum execution logic. Text rendering has no runtime dependencies. Matplotlib
is optional and imported only when graphical output is requested.

> **Project status:** Alpha. The versioned wire format is stable within schema
> version 1, but renderer features may expand in later releases.

## Installation

Install the dependency-free text renderer from PyPI:

```bash
python -m pip install q-alchemy-visualization
```

Install graphical rendering support with:

```bash
python -m pip install "q-alchemy-visualization[mpl]"
```

Python 3.11 and newer are supported.

## Quick start

```python
from q_alchemy.visualization import (
    ExperimentConnection,
    ExperimentDiagram,
    ExperimentStep,
    ExperimentStepStatus,
)

diagram = ExperimentDiagram(
    title="EXPERIMENT EXECUTION",
    steps=(
        ExperimentStep("PREPARE", status=ExperimentStepStatus.RUN, key="prepare"),
        ExperimentStep(
            "CLASSICAL",
            details=("Assessment: feasible",),
            status=ExperimentStepStatus.RUN,
            key="classical",
        ),
        ExperimentStep(
            "QUANTUM",
            details=("Assessment: compared",),
            status=ExperimentStepStatus.RUN,
            key="quantum",
        ),
    ),
    connections=(
        ExperimentConnection("prepare", "classical"),
        ExperimentConnection("classical", "quantum"),
    ),
)

print(diagram.draw(output="text", show_title=True))

# Requires the `mpl` extra. The caller owns the returned Figure.
figure = diagram.draw(output="mpl", show_title=True)
figure.savefig("experiment.png", bbox_inches="tight")
```

## Wire format

Diagrams serialize to a versioned JSON-compatible representation so producers
and renderers do not need to share workflow-specific code:

```python
payload = diagram.to_dict()
restored = ExperimentDiagram.from_dict(payload)

encoded = diagram.to_json(indent=2)
restored_from_json = ExperimentDiagram.from_json(encoded)
```

Schema version 1 uses this structure:

```json
{
  "schema_version": 1,
  "kind": "experiment-diagram",
  "title": "EXPERIMENT EXECUTION",
  "nodes": [
    {
      "id": "classical",
      "title": "CLASSICAL",
      "details": ["Assessment: feasible"],
      "status": "run"
    }
  ],
  "edges": []
}
```

The wire representation contains no renderer coordinates, Matplotlib objects,
ASCII layout, or Q-Alchemy feasibility rules. Explicit connections must form a
directed acyclic graph. The current compact text layout supports at most two
nodes per layer and connections between adjacent layers.

Titles are hidden by default. Pass `show_title=True` to either renderer to show
the diagram title.

## Public API

The top-level package exports:

- `ExperimentDiagram`
- `ExperimentStep`
- `ExperimentStepStatus`
- `ExperimentConnection`
- `TextExperimentDrawer`
- `MatplotlibExperimentDrawer`
- `DIAGRAM_SCHEMA_VERSION`

## Development

Clone the repository, create an environment, and run the tests:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
.venv/bin/python -m pytest
```

Build and validate the distributions before proposing a release:

```bash
.venv/bin/python -m build
.venv/bin/python -m twine check dist/*
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for contribution and release guidance.

## License

Licensed under the [Apache License 2.0](LICENSE).
