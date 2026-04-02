---
name: climate
description: Preview or confirm climate actions through Ecologi, store the provider key safely outside the repo, and maintain a managed CLIMATE.md file for the current project.
---

# Climate

Use this skill when the user wants to set up the Climate plugin, preview a climate action, confirm a live purchase, initialize repo climate tracking, or ask about the current climate tracking files.

## Helper CLI

This plugin's helper CLI lives at `plugins/climate/scripts/climate.py` in a repo-local install.

Prefer the launcher wrapper instead of calling Python directly:

- macOS, Linux, or WSL: `sh plugins/climate/scripts/climate`
- Windows native: `plugins\climate\scripts\climate.cmd`

The current runtime requires Python 3.10 or newer.

## Supported Provider

- `ecologi`

## Supported Actions

- `plant-tree`
- `carbon-avoidance`
- `carbon-removal`
- repo initialization
- stubbed repo estimate

## Setup Flow

1. Point the user to Ecologi signup and API key pages:
   - `https://ecologi.com/pay-as-you-go`
   - `https://ecologi.com/impact-api`
2. Ask for the API key.
3. Prefer storing the key with:

```bash
sh plugins/climate/scripts/climate configure-ecologi --read-key-stdin
```

4. Do not put the API key in repo files.
5. Avoid `--api-key` on the command line unless the user explicitly accepts exposing the key in command history.
6. For local development without network calls, the special credential value `SIMULATE` is valid and should behave like a normal provider run using fixed example USD pricing.

## Preview Flow

Preview before any live purchase:

```bash
sh plugins/climate/scripts/climate purchase \
  --provider ecologi \
  --action <plant-tree|carbon-avoidance|carbon-removal> \
  --quantity <value> \
  --units <kg|tonnes-if-needed> \
  --mode preview
```

- Show the user only the returned amount and currency for previews.
- Never modify repo files during preview mode.
- Do not say "Previewed" or explain preview mode unless the user asks.
- Frame preview responses like a quote for the requested action, then ask for confirmation.
- Preferred pattern for tree planting: `Planting \`10 trees\` with @climate will cost \`USD $8.00\`. Would you like to confirm this?`
- Preferred pattern for carbon avoidance: `Funding \`100 kg CO2e\` of carbon avoidance with @climate will cost \`USD $1.25\`. Would you like to confirm this?`
- Preferred pattern for carbon removal: `Funding \`50 kg CO2e\` of carbon removal with @climate will cost \`USD $14.00\`. Would you like to confirm this?`
- Keep the confirmation prompt short: `Would you like to confirm this?`

## Live Purchase Flow

Only run a live purchase when the user explicitly confirms with wording like "confirm live" or "run live".

```bash
sh plugins/climate/scripts/climate purchase \
  --provider ecologi \
  --action <plant-tree|carbon-avoidance|carbon-removal> \
  --quantity <value> \
  --units <kg|tonnes-if-needed> \
  --mode live \
  --confirm-live \
  --repo-root .
```

- Live purchases should update `CLIMATE.md` if the file is managed by Climate or does not exist yet.
- If `CLIMATE.md` already exists and is not managed by Climate, do not edit it and do not edit `README.md`.
- When `CLIMATE.md` is created for the first time and `README.md` exists, the helper may append a managed `## Climate Action` section.
- If the configured credential is `SIMULATE`, still speak about the result like a normal completed Climate action. Do not mention `SIMULATE`, simulation mode, test mode, or whether the provider call was skipped unless the user explicitly asks about configuration, debugging, or whether it was a real external purchase.
- Do not run the repo's test suite, linters, build, or other unrelated verification steps for normal climate purchases or repo initialization.
- Do not mention tests, verification commands, or development tooling in a normal purchase response unless the user explicitly asked for that verification or you changed plugin source code in the current thread.
- After the main live purchase summary, if `projectDetails` is present, add one short line using the first project only: `Project funded was [<name>](<projectUrl>).`
- If `treeUrl` or `tileUrl` is present, add a final line: `[View your impact here](<url>)`
- Prefix the main live purchase success sentence with `🌍` and end that same sentence with `🌱`

## Repo Initialization

When the user explicitly wants to initialize climate tracking for the current repo:

```bash
sh plugins/climate/scripts/climate init-repo --repo-root .
```

- On successful repo initialization, use one leading `🌱` in the main success sentence.

## Estimate Stub

Use the estimate stub when the user asks for repo emissions estimation:

```bash
sh plugins/climate/scripts/climate estimate --repo-root .
```

- Be explicit that repo estimation is not implemented yet.

## Output Expectations

- If the helper reports `skipped-unmanaged-existing`, tell the user `CLIMATE.md` already exists and is not managed by Climate, so it was left unchanged.
- Prefer concise summaries over raw JSON.
- For preview purchases, use natural action phrasing plus cost, not mechanical tool phrasing.
- For live purchases, include the amount, currency, and whether `CLIMATE.md` was created or updated.
- Never volunteer the configured credential value in normal user-facing responses.
- Keep purchase responses focused on the climate action and repo tracking outcome only.
- Preferred live response shape:
  `🌍 10 trees were planted with @climate for USD $8.00, and CLIMATE.md was updated. 🌱`
  `The repo total is now 21 trees planted, alongside 10 kg CO2e of carbon removal.`
  `Project funded was [Forest restoration in Kenya](https://ecologi.com/projects/forest-restoration-in-kenya).`
  `[View your impact here](https://ecologi.com/test?tree=604a74856345f7001caff578)`
- Preferred repo init success shape:
  `🌱 Climate tracking is now set up for this repo.`
