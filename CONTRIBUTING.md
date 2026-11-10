# Contributing

Thanks for wanting to help! The project is small and intentionally simple: Python
without dependencies, vanilla JS without a bundler, Android on the bare SDK/Kotlin.

## Quick start for developers

```powershell
# 1. Clone the repository
git clone https://github.com/meferspb/open-deck.git
cd open-deck

# 2. Start the gateway in demo mode (MSFS is not required)
python -m msfs_gateway --sim mock

# 3. Open http://127.0.0.1:8760/
```

Requirements: **Python 3.11+**. For the client tests — **Node.js 20+**.
To build the Android APK — **JDK 17**, **Android SDK**, and **Gradle 8.x**.

## Checks before a PR

```powershell
pwsh -File scripts/check.ps1
```

The script runs:

- `ruff check` and `ruff format --check` for Python;
- `python -m unittest discover -s tests` (252 tests);
- `node --test "tests/web/*.test.mjs"` (29 tests), if Node.js is installed.

To install the linter tools: `python -m pip install ruff`.

## Code style

- **Python**: PEP 8, `ruff format` formatting, line length 100.
  Standard library only — we do not add new dependencies.
- **JS**: ES modules, no frameworks and no external CDNs. Syntax check —
  `node --check`, tests — `node --test`.
- **Kotlin**: only the Android SDK and Kotlin stdlib, no AndroidX or third-party
  libraries.
- Comments and documentation in Russian; names in code in English.
- All user-facing strings must work **offline**: no external fonts, images, or
  APIs.

## What can be improved

See [`README.md`](README.md#roadmap) and
[`docs/architecture.md`](docs/architecture.md). Good directions:

- new aircraft profiles (`profiles/*.json`) — welcome;
- new instrument types (`web/js/widgets/`, registry `registry.js`) and their
  registration in `msfs_gateway/profiles.py` (`WIDGET_TYPES`,
  `REQUIRED_BINDINGS`);
- tests: pure logic (instrument geometry, profiles, protocol) — first
  priority;
- documentation: discrepancies between the code and `docs/` count as bugs.

## Aircraft profiles

1. Copy an existing profile from `profiles/` and change `id`, `name`,
   `sim.match`.
2. Check validation: `python -c "from msfs_gateway.profiles import ProfileStore; ..."` —
   or simply start the gateway: broken profiles are skipped with a warning.
3. Take bindings from `GET /api/telemetry/variables` (the editor shows them as a
   list).
4. In the PR, describe which add-on you tested with.

## Commits and PRs

- Atomic commits, imperative message: `add A320 profile`, `fix QR mask`.
- In the PR — what changed, why, and how it was tested (tests/screenshots).
- For interface changes, attach a screenshot in `docs/screenshots/`.

## Contribution license

By submitting a PR you agree that your contribution is distributed under the
project license ([LICENSE](LICENSE)). Do not remove or replace the author support
block and the integrity check — this is a license condition.
