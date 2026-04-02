# Contributing

## Development Setup

Climate is developed as a local Codex plugin from this repo.

Requirements:

- Python 3.10 or newer

### Workspace-local plugin install

This is the easiest way to iterate on the plugin while working in this repo.

1. Clone the repo:

```bash
git clone https://github.com/justinkalland/codex-plugin-climate
cd codex-plugin-climate
```

2. Open this repo in Codex.

3. In the Codex app, open Plugins.

4. Choose the `Local Workspace Plugins` marketplace.

5. Install `Climate`.

This mode is ideal for development, but the top-level `@Climate` plugin mention is only discoverable from this repo because the marketplace file lives in this repo.

### User-global install for cross-project testing

If you want `@Climate` to show up as a top-level plugin across projects while developing, run the installer from this repo:

```bash
sh scripts/install-climate-plugin
```

On Windows:

```bat
scripts\install-climate-plugin.cmd
```

That writes or updates `~/.agents/plugins/marketplace.json` so Codex can discover this plugin outside the repo too.

## Tests

Run the full test suite with:

```bash
python -m unittest discover -s tests -v
```

## Helpful Commands

```bash
sh plugins/climate/scripts/climate estimate --repo-root .
sh plugins/climate/scripts/climate init-repo --repo-root .
sh plugins/climate/scripts/climate purchase --action plant-tree --quantity 1
sh plugins/climate/scripts/climate configure-ecologi --api-key SIMULATE
```

Use `SIMULATE` as the configured Ecologi credential during local development when you want normal plugin behavior without making any network calls.

The plugin launcher tries `python3` and then `python` on macOS/Linux/WSL. On Windows native, use `plugins\climate\scripts\climate.cmd`, which tries `py -3`, `python3`, and then `python`.
