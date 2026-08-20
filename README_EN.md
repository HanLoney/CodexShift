# CodexShift

<p align="center">
  <img src="assets/codexshift-logo.png" alt="CodexShift logo" width="160">
</p>

<p align="center">
  <strong>A Provider switcher and Codex historical task index repair tool</strong>
</p>

<p align="center">
  <a href="https://github.com/HanLoney/CodexShift/releases/latest">Download</a> ·
  <a href="README.md">简体中文</a> ·
  <a href="https://github.com/HanLoney/CodexShift/issues">Report an issue</a>
</p>

CodexShift is an independent Codex data migration and index maintenance tool. When you switch between the native account and a third-party API, it also synchronizes Provider references in historical tasks so old sessions do not become orphaned, duplicated, or disappear from the history list. It does not depend on, read data from, or modify any other Provider switching tool.

> [!IMPORTANT]
> CodexShift is a community project. It is not an official OpenAI product and is not affiliated with or endorsed by OpenAI.

## Why CodexShift

Many tools can replace an API endpoint. Codex history also depends on Provider values in rollout files and task indexes in `state_5.sqlite`. Replacing only the configuration can leave old sessions missing, duplicated, or impossible to reopen.

CodexShift's core flow is:

```text
Switch Provider → Back up Codex data → Sync historical task Providers → Repair root indexes → Finish
```

It cares not only where new requests go, but also whether previous tasks remain discoverable, openable, and usable.

## Features

- Built-in native OpenAI account profile, with saved credential recovery and the original sign-in flow.
- Create, edit, and delete third-party API profiles.
- Test API connectivity and credentials, and discover models from OpenAI-compatible `/models` endpoints.
- Switch configuration and authentication data while removing conflicting account fields.
- Automatically detect `CODEX_HOME` / `~/.codex`, with an editable path setting.
- **Historical task index synchronization (the core feature):** scan rollout files, normalize their `model_provider` values, update `state_5.sqlite`, and restore missing root task indexes so historical sessions remain visible and openable after a switch.
- Repair historical indexes independently, without changing the active Provider.
- **Cross-Harness project and session migration**: choose a project, multi-select sessions, and move selected content between Codex and DeepSeek Harness. Codex → DSH restores user and assistant turns as native messages instead of one Markdown archive, without invoking a model or consuming tokens.
- Migration shows live percentage, current-item status, and a scrollable execution log while work runs in the background.
- Automatic backups and rollback on failure; the latest three backups are retained by default.
- Simplified Chinese, English, Japanese, and Korean UI.
- Per-user secret protection using Windows DPAPI or macOS Keychain.

## Download and use

Download the appropriate file from [Releases](https://github.com/HanLoney/CodexShift/releases/latest):

| Platform | File |
| --- | --- |
| Windows 10/11 x64 | `CodexShift-v1.8.0-Windows-x64.exe` |
| macOS | `CodexShift-v1.8.0-macOS-Universal.zip` |

Open CodexShift, verify the detected Codex Home, choose or create a Provider, optionally test its API, then click the switch button. CodexShift backs up the data and synchronizes historical task indexes as part of the switch. Codex must close during the operation. Backups are stored in `~/.codex/switcher_backups`.

### Bidirectional Codex ↔ DeepSeek Harness migration

Open “Migrate projects & sessions”, choose a source and the DeepSeek Harness URL (default `http://127.0.0.1:3080`), select one project, multi-select the sessions to move, then preview or import the selected items.

- Codex → DeepSeek Harness creates or reuses the matching Workspace and creates one new Session per selected conversation.
- DeepSeek Harness → Codex converts selected sessions into indexable Codex rollouts and rebuilds `state_5.sqlite`.
- “Compact context” imports recent messages individually, “Complete chat history” restores as much user/assistant history as possible as native messages, and “Projects only” creates only the project entry. Neither message mode invokes a model.
- CodexShift closes Codex automatically before importing, backs up the database, rolls back newly created rollouts on failure, and reopens Codex afterward.

Migration restores visible messages and project membership, but not model KV cache, live shell state, in-progress tool calls, approval state, or other Harness-internal runtime state. DeepSeek Harness APIs and local session formats may change while it remains in developer preview.

### What happens to history

During a switch, CodexShift updates Provider references in rollout history files and repairs the task-discovery records and root thread entries in `state_5.sqlite`. Every change is backed up first; failed synchronization or database validation triggers an automatic rollback.

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
