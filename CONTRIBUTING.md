# Contributing to ai-lipsync-video-generator

Thanks for wanting to push the tater. This repo is a plugin host for
lip-sync pipelines — the host stays small, the muscle lives in plugins.

## Ground rules

- Python 3.11+. We use `match` statements and `tomllib` from stdlib.
- One plugin = one folder under `plugins/`. No cross-plugin imports.
- Every plugin implements `plugins/contracts.py::LipSyncPlugin`.
- Media I/O goes through `services/media_io.py`. Never touch `cv2.VideoWriter`
  directly from a plugin — the host owns the writer so frame pacing stays
  consistent across plugins.
- Config schema changes require a bump in `config/schema.py::SCHEMA_VERSION`
  and a migration note in the PR description.

## Dev setup

```bash
git clone https://github.com/<you>/ai-lipsync-video-generator
cd ai-lipsync-video-generator
python -m venv .venv
.venv\Scripts\activate      # Windows
pip install -e ".[dev]"
pytest -q
python -m lipsync_host --list-plugins
```

## Adding a plugin

1. Copy `plugins/example_phoneme_driver/` to `plugins/<your_plugin>/`.
2. Rename the class, bump `PLUGIN_API` if you need new host hooks (rare —
   talk to maintainers first).
3. Register it in `plugins/registry.py` — the loader auto-discovers, but the
   registry keeps an explicit allowlist for sandboxed builds.
4. Add a fixture under `tests/fixtures/` and a test in `tests/`.

## Style

- `ruff` + `black`, line length 100.
- Types required on all public callables. `mypy --strict` on `core/`.
- Docstrings on modules and public classes. Inline comments only for
  constraints the code can't express.

## Reporting issues

Include: Windows build (10/11), Python version, GPU + driver, the plugin
that misbehaved, and the tail of `logs/host.log`. Renders that produce
desync are worth a 3-second clip — attach it.