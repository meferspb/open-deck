# 📚 Open Deck for MSFS Documentation

**Languages:** [English](README.md) · [Русский](ru/README.md) · [Deutsch](de/README.md) · [中文](zh/README.md) · [Español](es/README.md) · [日本語](ja/README.md)


<img src="pic1.jpg" alt="Open Deck for MSFS" width="180" />

This is where all project documents are collected. Start with the README at the
repository root — it gives the big picture and a quick start; this index helps
you find the details.

## Where to start

| If you are… | Read in order |
| --- | --- |
| a pilot setting up the panel "for yourself" | [README](../README.md) → [service.md](service.md) |
| someone who wants to understand how it works | [architecture.md](architecture.md) → [protocol.md](protocol.md) |
| writing a client or an integration | [protocol.md](protocol.md) → [telemetry.md](telemetry.md) |
| changing the code | [development.md](development.md) → [architecture.md](architecture.md) |
| building an aircraft profile | [profile-schema.md](profile-schema.md) → [widgets.md](widgets.md) |
| building the installer/APK | [packaging/windows/README.md](../packaging/windows/README.md) → [android/README.md](../android/README.md) |
| reviewing security | [SECURITY.md](../SECURITY.md) |

## Documents

| Document | What it covers | Audience |
| --- | --- | --- |
| [service.md](service.md) | Full service description: purpose, operating model, telemetry, profiles, clients, network, authentication, assist, API, installation, diagnostics, security, license | everyone |
| [architecture.md](architecture.md) | Internal design: modules, data flows, WASM bridge, key decisions, and MVP boundaries | developers |
| [protocol.md](protocol.md) | HTTP REST, WebSocket, password and QR login, autodiscovery, error codes, and examples | integrators |
| [telemetry.md](telemetry.md) | Catalog of all variables: types, units, SimVar, events, `custom.*` — generated from code | client and profile developers |
| [widgets.md](widgets.md) | Instrument catalog: required bindings, `command`, options, JSON examples — generated from code | profile authors |
| [profile-schema.md](profile-schema.md) | JSON profile schema: fields, layouts, validation, compatibility, complete example | profile authors |
| [development.md](development.md) | How to change the code: module map, adding a variable/instrument/profile/provider/page, tests, release | contributors |
| [pricing.md](pricing.md) | Comparison of "connected services vs local equivalents" for an air-gapped scenario | those choosing the stack |
| [../android/README.md](../android/README.md) | Android client: build, architecture, login, debugging | Android developers |
| [../packaging/windows/README.md](../packaging/windows/README.md) | Installer: contents, build, shortcuts, uninstall, silent flags | release engineers |
| [../CONTRIBUTING.md](../CONTRIBUTING.md) | How to participate: style, tests, profiles, PRs | contributors |
| [../SECURITY.md](../SECURITY.md) | Threat model, what is protected, how to report a vulnerability | everyone |
| [../CHANGELOG.md](../CHANGELOG.md) | Version history | everyone |

## Screenshots

`docs/screenshots/` — the panel on a phone and tablet, six-pack, editor, login
page, and assist. Used in the README and in the service description.

## Keeping docs current

Two documents are **generated from code** and checked by a test:

```powershell
python -m msfs_gateway.docsgen --check   # telemetry.md and widgets.md
python -m msfs_gateway.docsgen --write   # update after changing registries
```

If you changed `telemetry.py`, `profiles.py`, or web instruments — update the
documentation and run `pwsh -File scripts/check.ps1`.

## How to write documentation

- Write in English, in short paragraphs, with JSON/command examples.
- Links are relative so they work both on GitHub and locally.
- Do not duplicate the schema: profile — in `profile-schema.md`, variables — in
  `telemetry.md`, instruments — in `widgets.md`, network — in `protocol.md`.
- If you change behavior, update the README/service description and `CHANGELOG.md`.
