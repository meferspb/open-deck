# Windows Installer

A single file `OpenDeck-Setup-<version>.exe`: double-click → "Next" →
done. Administrator rights are not required, and Python and the internet are not needed.

## What happens during installation

| | |
|---|---|
| Directory | `%LOCALAPPDATA%\OpenDeck` (in the user profile, no UAC) |
| Inside | `OpenDeck.exe` — the gateway with embedded Python 3.13 and the standard library |
| | `web/` — the web client (panel and editor), `profiles/` — aircraft profiles |
| | `config/donation.json` — the author's details, `integrity/` — the integrity manifest |
| | `android/` — the Android sources and, after a build, the ready APK (`android/dist/OpenDeck-Android-<version>.apk`), `config/android-build.json` — APK build settings |
| | `docs/` — full documentation (service, protocol, variables, instruments, profile schema) |
| Shortcuts | desktop, Start menu (launch, panel in the browser, build Android APK, "Set password", uninstall) |
| Uninstall | "Programs and Features" or the "Uninstall" shortcut |

Data lives next to the `.exe`, so profiles and details can be edited
without reinstalling (after editing protected files, the manifest must be rebuilt,
see the root README).

## Building (on the developer machine, internet needed once)

Requirements:

- Python 3.11+ and PyInstaller: `python -m pip install pyinstaller`
- NSIS 3.x: `makensis.exe` in `PATH`, or `NSIS_HOME`, or `-NsisPath`

```powershell
# from the repository root
pwsh -File scripts/build-installer.ps1 -Version 0.1.0 -NsisPath "C:\Program Files (x86)\NSIS"
```

The script step by step: rebuilds the integrity manifest → runs the tests →
builds `build/pyinstaller/dist/OpenDeck` (PyInstaller, onedir) →
copies `web/`, `profiles/`, `config/`, `integrity/` next to it → verifies that the
`.exe` starts (`--help`) → compiles the installer into
`dist/OpenDeck-Setup-<version>.exe`.

Flags: `-SkipTests`, `-NsisPath <directory>`, `-Version 0.2.0`.

The script also verifies that the installer was built and prints the final path and
size. A full list of steps is at the top of `scripts/build-installer.ps1`.

Password login: the "Set password" shortcut runs
`OpenDeck.exe --set-password` and prompts for the password in the console;
the hash is saved to `config/auth.json` next to the `.exe`. Deleting the file
reopens access without login.

## Before publishing

1. Check `config/donation.json`: author Viktor Krasnikov, Donation
   link — `https://taps.uz/open_deck_fs`.
2. Rebuild the manifest: `python -m msfs_gateway.integrity --write`
   (the build script does this itself, but it does not hurt to check).
3. Run the installer on a clean machine: installation without admin, launch,
   access to the panel from a phone on the same network, uninstall.

## Silent installation / deployment

```bat
OpenDeck-Setup-0.1.0.exe /S /D=C:\Tools\OpenDeck
Uninstall.exe /S
```

`/D=` must come last and without quotes (an NSIS limitation).

## Limitations

- The installer is unsigned: SmartScreen may warn "unknown
  publisher" — "More info" → "Run anyway". A release needs a
  code-signing certificate (EV/OV).
- No firewall rule is added (administrator rights are required). On first
  launch Windows will ask about network access — allow it for private networks,
  otherwise clients will not connect.
- Per-user installation: the app is visible only to the current user.
- Registry entries/shortcuts are created in `HKCU` — on machines with strict policies
  (AppLocker, writes to the profile disallowed), installation may be blocked;
  in that case, use the portable variant: unpack the
  `build/pyinstaller/dist/OpenDeck` directory and run the `.exe` from there.
