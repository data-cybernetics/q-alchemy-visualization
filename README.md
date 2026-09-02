# q-alchemy-visualization

Shared renderer-neutral experiment-diagram schema and renderers for Q-Alchemy.

The package deliberately contains no feasibility, Quantum I/O, or SDK decision logic. A producer
creates an `ExperimentDiagram`, serializes it to the versioned wire representation, and a client
can deserialize and render the same graph as text or Matplotlib.

```python
from q_alchemy.visualization import ExperimentDiagram

diagram = ExperimentDiagram.from_dict(payload["experiment_diagram"])
print(diagram.draw(output="text"))

# Optional Matplotlib support:
figure = diagram.draw(output="mpl")
```

Install Matplotlib support with:

```bash
pip install "q-alchemy-visualization[mpl]"
```

## Wire format

Schema version 1 is an `experiment-diagram` object with a title, renderer-neutral nodes and directed
edges. It contains no coordinates, Matplotlib objects, ASCII layout, SVG, or feasibility-specific
decision rules.

```json
{
  "schema_version": 1,
  "kind": "experiment-diagram",
  "title": "EXPERIMENT EXECUTION DIAGRAM",
  "nodes": [
    {
      "id": "classical",
      "title": "CLASSICAL EXECUTION",
      "details": ["Assessment: feasible"],
      "status": "run"
    }
  ],
  "edges": []
}
```

Titles are hidden by default when rendering. Pass `show_title=True` to either renderer to display
them.
