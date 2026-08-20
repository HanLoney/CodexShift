# Changelog

All notable changes to CodexShift are documented here.

## 1.8.1

- Fixed repeated automatic snapshots creating extra `custom` Provider profiles when the live model changed.
- Live API settings now update the matching user-created profile instead of creating a duplicate snapshot.
- Preserved user-defined Provider names instead of replacing them with the TOML table name `custom`.
- Expanded the Provider list and added a scrollbar so the built-in official account remains visible alongside saved profiles.

## 1.8.0

- Added bidirectional, project-scoped and session-scoped migration between Codex and DeepSeek Harness.
- Added quick handoff, readable history archive, project-only import, preview, and migration mapping records.
- Added Codex rollout parsing, DSH JSON-RPC integration, conflict checks, Codex process guard, and backup/rollback for DSH → Codex imports.
- Filtered injected workspace instructions from migration titles and previews.
- Changed Codex → DSH history import to native per-message session events, preserving user/assistant order without invoking a model or consuming tokens.
- Added automatic discovery of the running DSH desktop runtime, native-log verification, isolated cleanup on write failure, and post-attach history verification.
- Fixed native import timeouts for histories containing characters outside the Windows system code page, and prevented internal bridge source from appearing in error dialogs.
- Fixed DSH → Codex imports reporting success while remaining hidden: imported threads now use Codex's native source, receive project assignments, and retain useful titles.
- Added automatic repair for DSH imports created by older CodexShift builds; project-only imports no longer create placeholder conversations.
- Fixed imported rollouts being rejected as invalid session metadata by current Codex Desktop; CodexShift now writes and repairs the required `originator` field before rebuilding the thread database.
- Fixed imported DSH conversations opening with an empty transcript: user and assistant messages are now mirrored into Codex Desktop's visible `event_msg` records, while DSH runtime/system snapshots are filtered out.
- Existing empty imported conversations can be rebuilt from their original DSH session through the migration map during history repair, with an offline rollout fallback.
- DSH → Codex imports now close running Codex processes automatically and reopen Codex after both successful imports and rolled-back failures.
- Added a responsive migration progress panel with percentage, per-item status, and a scrollable live log; imports now run in the background so the UI stays responsive.
- Kept Preview, Import, and Cancel actions permanently visible at compact window heights.
- Fixed Windows project-path normalization and folder-name extraction when tests or migrations run on macOS.

## 1.7.0

- Added native OpenAI account and third-party API switching.
- Added local profile creation, editing, deletion, API testing, and model discovery.
- Added automatic Codex Home detection and editable path settings.
- Added rollout and `state_5.sqlite` history synchronization.
- Added automatic backup, rollback, process closing, and Codex restart support.
- Added encrypted credential storage with Windows DPAPI and macOS Keychain.
- Added Simplified Chinese, English, Japanese, and Korean localization.
- Added language-aware dialogs, responsive dialog sizing, and refreshed visual design.
- Added Windows and macOS packaging workflows.
