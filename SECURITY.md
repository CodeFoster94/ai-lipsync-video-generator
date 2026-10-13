# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.6.x   | yes       |
| 0.5.x   | security fixes only |
| < 0.5   | no        |

## Threat model

`ai-lipsync-video-generator` loads third-party plugins from `plugins/` and
from user-configured `plugin_paths`. Plugins run in-process and can read
the filesystem, spawn subprocesses, and open sockets. Treat any plugin as
trusted code — the host does not sandbox plugin execution.

If you need isolation, run the host inside a Windows Sandbox or a VM with
no host filesystem mount.

## Reporting a vulnerability

Email `security@<project-domain>` (PGP key in `docs/security.asc`) or open
a private advisory on GitHub. Do not file a public issue for anything
that lets a plugin escape the intended media pipeline, exfiltrate user
footage, or crash the host on untrusted input.

We aim to acknowledge within 72 hours and ship a fix or mitigation within
14 days for high-severity issues.

## Known non-issues

- Plugins writing to `artifacts/` and `renders/` — that's the contract.
- Plugins loading arbitrary `.onnx` / `.safetensors` files — user's choice.
- The host reading `config/local.toml` — expected.

## Hardening tips for users

- Only install plugins from sources you trust.
- Keep `plugin_paths` pointed at a folder you own.
- Run with `--no-network` to disable plugins that declare network access.