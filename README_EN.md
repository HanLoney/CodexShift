# CodexShift

<p align="center">
  <img src="assets/codexshift-logo.png" alt="CodexShift logo" width="160">
</p>

<p align="center">
  <strong>Safely switch between a native Codex account and third-party APIs, with automatic history reindexing.</strong>
</p>

<p align="center">
  <a href="https://github.com/HanLoney/CodexShift/releases/latest">Download</a> ·
  <a href="README.md">简体中文</a> ·
  <a href="https://github.com/HanLoney/CodexShift/issues">Report an issue</a>
</p>

CodexShift is an independent desktop application. It does not depend on, read data from, or modify any other Provider switching tool.

> [!IMPORTANT]
> CodexShift is a community project. It is not an official OpenAI product and is not affiliated with or endorsed by OpenAI.

## Features

- Built-in native OpenAI account profile, with saved credential recovery and the original sign-in flow.
- Create, edit, and delete third-party API profiles.
- Test API connectivity and credentials, and discover models from OpenAI-compatible `/models` endpoints.
- Switch configuration and authentication data while removing conflicting account fields.
- Automatically detect `CODEX_HOME` / `~/.codex`, with an editable path setting.
- Synchronize rollout files and `state_5.sqlite`, including missing root task indexes.
- Automatic backups and rollback on failure; the latest three backups are retained by default.
- Simplified Chinese, English, Japanese, and Korean UI.
- Per-user secret protection using Windows DPAPI or macOS Keychain.

## Download and use

Download the appropriate file from [Releases](https://github.com/HanLoney/CodexShift/releases/latest):

| Platform | File |
| --- | --- |
| Windows 10/11 x64 | `CodexShift-v1.7.0-Windows-x64.exe` |
| macOS | `CodexShift-v1.7.0-macOS-Universal.zip` |

Open CodexShift, verify the detected Codex Home, choose or create a Provider, optionally test its API, then click the switch button. Codex must close during the operation. Backups are stored in `~/.codex/switcher_backups`.

Unsigned Windows builds may trigger SmartScreen. The macOS build is ad-hoc signed; on first launch, right-click the app in Finder and choose **Open**.

## Build from source

Python 3.11+ and Tkinter are required.

```bash
python -m unittest discover -s tests -v
python codex_switcher.py
```

Use `build.ps1` on Windows or `build_macos.sh` on macOS to create a packaged application.

## Security and privacy

- API keys, account tokens, configuration, and history never leave your device.
- Full secrets are not printed in application logs.
- Changes are backed up before being written and rolled back on failure.
- Never share or commit Codex's `auth.json` file.
- See [SECURITY.md](SECURITY.md) for reporting instructions.

## License

[MIT License](LICENSE)
