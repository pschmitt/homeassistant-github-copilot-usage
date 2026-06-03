# Home Assistant GitHub Copilot Usage

Home Assistant custom integration that exposes GitHub Copilot quota usage as sensors.

It polls `https://api.github.com/copilot_internal/user` with a GitHub personal access token and creates one diagnostic sensor per quota bucket returned by GitHub, such as `premium_interactions`, `chat`, and `completions`.

## Features

- Config flow based setup
- PAT authentication
- Polling coordinator with configurable scan interval
- Diagnostic sensors for each Copilot quota bucket
- HACS-compatible repository layout

## Installation

### HACS

[![Open your Home Assistant instance and open a repository inside the Home Assistant Community Store.](https://my.home-assistant.io/badges/hacs_repository.svg)](https://my.home-assistant.io/redirect/hacs_repository/?owner=pschmitt&repository=homeassistant-github-copilot-usage&category=integration)

1. Click the badge above, or open HACS and add `https://github.com/pschmitt/homeassistant-github-copilot-usage` as a custom repository of type **Integration**.
2. Install **GitHub Copilot Usage**.
3. Restart Home Assistant.

### Manual

Copy `custom_components/github_copilot_usage` from this repository into:

```text
custom_components/github_copilot_usage
```

Restart Home Assistant.

## Setup

1. Create a GitHub personal access token that can access your Copilot account data.
2. Add the integration in Home Assistant.
3. Enter the token and, optionally, a display name.

### Experimental device flow

The integration also includes an experimental GitHub device-flow path.

This requires:

1. Your own GitHub OAuth app
2. Device flow enabled for that app
3. The OAuth app client ID

Even with a successful device login, GitHub may still reject the resulting OAuth token for the undocumented `copilot_internal/user` endpoint. PAT authentication is the known-working path.

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
- Repository branding assets use GitHub Copilot logos sourced from GitHub-owned public assets. GitHub, GitHub Copilot, and related marks are trademarks of GitHub, Inc. The integration code is GPL-3.0, but the bundled third-party logos are not relicensed under GPL.
