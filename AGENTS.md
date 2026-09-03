# Agent guidelines

This repository is a Home Assistant custom integration over `huckleberry-api`. Keep Firebase access and Huckleberry operations in that library; this repository should contain only Home Assistant adaptation.

- Never guess values from the Huckleberry app or Firebase schema. Before adding or changing keys, enum or state values, modes, units, or options, verify them against `huckleberry-api` types or implementation.
- Keep the Home Assistant model minimal. Add only required entities, states, options, and attributes; do not expose convenience or speculative extras.
- Use precise types wherever possible. Prefer existing `huckleberry-api` and Home Assistant types over `Any`, untyped dictionaries, or duplicate local types.
- Keep platform entry points such as `sensor.py`, `switch.py`, and `calendar.py` limited to entity setup. Put entity behavior in `features/` or shared integration modules.
- Keep `custom_components/huckleberry/manifest.json` and `pyproject.toml` synchronized when changing dependencies.
- Run Python tools through `uv`, including tests, linting, and type checks.
- Follow `RELEASE.md` when preparing and publishing a release.
- Apply the `unslop` skill to PR titles and descriptions.
