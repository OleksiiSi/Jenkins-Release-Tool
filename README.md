# Jenkins Release & Promote Tool

A Windows desktop app for triggering Jenkins release builds across multiple
jobs and tickets at once, then promoting the successful builds to one or more
test environments, with automatic retries and desktop/Teams notifications.
Built for a single-user QA workflow, to replace manually clicking through the
Jenkins UI for repetitive release/promote work.

## Requirements

- Windows
- Python 3.11–3.14
- [Poetry](https://python-poetry.org/) for dependency management
- A Jenkins instance with the [Promoted Builds Plugin](https://plugins.jenkins.io/promoted-builds/)
  installed, and a Manual Promotion condition configured on each promotion
  process you intend to use
- An MS Teams channel with a Workflows webhook (not the legacy "Incoming
  Webhook" connector, which Microsoft retired)

## Install dependencies

```powershell
poetry install
```

## Run in dev mode

```powershell
poetry run python app/main.py
```

On first run, open the **Settings** tab and fill in:

- Jenkins base URL, username, and API token (token is saved to Windows
  Credential Manager via `keyring`, never written to disk)
- MS Teams webhook URL
- Jobs and environments matching your Jenkins setup

`app/settings.json` ships with placeholder values (`jenkins.example.com`,
etc.) so the app starts without crashing before you configure it — replace
them with real values via the Settings tab, not by hand-editing the file.

## Build the installer

```powershell
.\packaging\build.ps1
```

This runs PyInstaller (`--onedir`) to produce `packaging/dist/ReleaseTool/`,
then compiles it into a versioned installer at
`packaging/installer_output/ReleaseTool-Setup-<version>.exe` using
[Inno Setup 6](https://jrsoftware.org/isinfo.php) (`ISCC.exe` must be on
`PATH` or in a default install location). The version number is read
automatically from `pyproject.toml`.

Pass `-SkipInstaller` to produce just the PyInstaller app folder without
building the installer:

```powershell
.\packaging\build.ps1 -SkipInstaller
```

## Project layout

- `app/core/` — business logic (Jenkins/Teams clients, run orchestration,
  validation, settings).
- `app/api.py` — the `pywebview` JS bridge; the only file that connects the
  UI to `core/`.
- `app/ui/` — the HTML/CSS/JS frontend.
- `packaging/` — PyInstaller + Inno Setup build scripts and output.
