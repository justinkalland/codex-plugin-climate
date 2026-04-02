# Climate Plugin for Codex

Take climate action from Codex. This plugin lets you make climate purchases through supported providers and track them in your repo with a managed `CLIMATE.md`.

V1 (MVP) supports:

- Ecologi as the first provider
- tree planting
- carbon avoidance
- carbon removal
- repo climate tracking via `CLIMATE.md`
- a stubbed repo-emissions estimate command

V2 plans:

- more providers
- Machine Payments Protocol (MPP) instead of needing a provider account and API key
- carbon output estimations for repos or actions

## How It Works

The plugin is packaged as a repo-local Codex plugin with:

- a plugin manifest at `plugins/climate/.codex-plugin/plugin.json`
- a repo marketplace entry at `.agents/plugins/marketplace.json`
- one umbrella skill at `plugins/climate/skills/climate/SKILL.md`
- Python helper scripts under `plugins/climate/scripts`

Calls stay non-live unless you explicitly confirm a live action. Confirmed live actions can update `CLIMATE.md`.

## Install In Codex

### Requirements
- For this MVP, Python 3.10 or newer is required

1. Clone this repo:

```bash
git clone https://github.com/justinkalland/codex-plugin-climate
cd codex-plugin-climate
```

2. Run the installer:

```bash
sh scripts/install-climate-plugin
```

On Windows:

```bat
scripts\install-climate-plugin.cmd
```

3. In Codex, open Plugins.

4. Choose the `Local Plugins` marketplace.

5. Install `Climate`.

The installer stages the plugin into your user Codex directory and wires the user-level marketplace for you. Run it again after pulling updates if you want to refresh the installed source copy.

## Use In Codex

Once installed, you can invoke the plugin with `@climate`.

Examples:

- `Set up Ecologi for this repo using @climate`
- `Plant 1 tree using @climate`
- `Use @climate to buy 100 kg carbon avoidance`
- `Buy 50 kg carbon removal with @climate`
- `Initialize climate tracking in this repo with @climate`
- `Estimate this repo using @climate`
- `Confirm live and plant 1 tree in this repo using @climate`

### Behavior

- Calls are non-mutating for repo files unless you explicitly confirm a live action.
- Live purchases require explicit confirmation.
- If no `CLIMATE.md` exists, Climate can create a managed one.
- If `README.md` exists when Climate creates a brand-new managed `CLIMATE.md`, it can append a managed `## Climate Action` section.
- If `CLIMATE.md` already exists and is not managed by Climate, the plugin will not edit `CLIMATE.md` or `README.md`.

## What `CLIMATE.md` Tracks

Managed `CLIMATE.md` files include:

- lifetime totals for trees planted
- lifetime totals for carbon avoidance purchased
- lifetime totals for carbon removal purchased
- a light log of live purchases only
- a placeholder section for repo footprint estimation

## Local Development

For workspace-local install, testing, and development notes, see [CONTRIBUTING.md](CONTRIBUTING.md).

## Current Limitations

- Ecologi is the only provider implemented in v1.
- Local trees and habitat restoration are not wired up yet.
- Repo emissions estimation is intentionally stubbed and does not calculate anything yet.
- Networked purchase flows may still require Codex approval depending on your sandbox and permissions settings.
