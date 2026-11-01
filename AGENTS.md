# Agent instructions

## Project

This repository is a Home Assistant custom integration that exposes GitHub Copilot quota usage as diagnostic sensors. Integration code lives in `custom_components/github_copilot_usage/`.

## Working in this repository

- Read `README.md` before changing setup, authentication, or quota handling. The integration uses GitHub's undocumented Copilot usage endpoint, which may change.
- Keep the config flow, coordinator, sensors, and user-facing strings consistent. Update `strings.json` and translations when changing config-flow text.
- Before changing CI, check [pschmitt/ci-workflows](https://github.com/pschmitt/ci-workflows) for reusable components and preserve this repository's existing checks.

## Validation

- Run `uvx ruff check .` and `uvx ruff format --check .` for Python changes.
- CI runs Hassfest and the same Ruff checks. This repository currently has no test suite.
