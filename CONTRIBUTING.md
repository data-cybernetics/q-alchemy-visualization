# Contributing

Thank you for contributing to Q-Alchemy Visualization.

## Development setup

Use Python 3.11 or newer and install the development dependencies:

```bash
python -m venv .venv
.venv/bin/python -m pip install -e ".[dev]"
```

Run the complete test suite before opening a pull request:

```bash
.venv/bin/python -m pytest
```

Changes to the wire model should include round-trip tests. Changes to a renderer
should cover the relevant layout or output behavior. Keep the base package free
of mandatory rendering dependencies; optional renderers must import their
dependencies lazily and provide a useful installation message when unavailable.

## Pull requests

Describe the behavior changed and the validation performed. Keep pull requests
focused, and update the README when public behavior or installation changes.
By submitting a contribution, you agree that it is licensed under the Apache
License 2.0 used by this project.

## Releases

Maintainers should:

1. Update the version in `pyproject.toml` and merge it to `main`.
2. Create a GitHub Release tagged `v<version>`.
3. Confirm that the package-check workflow passes.
4. Publish the GitHub Release. The trusted-publishing workflow verifies the tag
   and uploads the wheel and source distribution to PyPI.
