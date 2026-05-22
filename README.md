# Home Assistant GitHub Copilot Usage

Home Assistant custom integration that exposes GitHub Copilot quota usage as sensors.

It polls `https://api.github.com/copilot_internal/user` with a GitHub personal access token and creates one diagnostic sensor per quota bucket returned by GitHub, such as `premium_interactions`, `chat`, and `completions`.

## Features

- Config flow based setup
- PAT authentication
- Polling coordinator with configurable scan interval
- Diagnostic sensors for each Copilot quota bucket
- HACS-compatible repository layout

## Setup

1. Create a GitHub personal access token that can access your Copilot account data.
2. Add the integration in Home Assistant.
3. Enter the token and, optionally, a display name.

## Sensors

Each returned quota bucket becomes a sensor whose state is the `remaining` value from GitHub.

Useful attributes include:

- `percent_remaining`
- `unlimited`
- `entitlement`
- `quota_remaining`
- `quota_reset_date`
- `copilot_plan`

## Notes

- The underlying endpoint is undocumented/internal and may change.
- OAuth is intentionally not implemented; PAT auth is simpler and works with the endpoint today.
