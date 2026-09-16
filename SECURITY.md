# Security Policy

## Reporting a vulnerability

Please do not publish credentials or a reproducible exploit in a public issue.

Report security concerns through GitHub's private vulnerability reporting feature for this repository. Include the affected version, platform, impact, and the minimum steps needed to reproduce the issue. Remove API keys, account tokens, `auth.json`, and private history content from all screenshots and logs.

## Credential handling

CodexShift stores Provider snapshots locally. Saved profiles are protected with Windows DPAPI or macOS Keychain. While a third-party Provider is active, Codex's `config.toml` contains its API Key in `experimental_bearer_token` so Codex can authenticate without OpenAI login. `auth.json`, `config.toml`, and switch backups are sensitive and should never be shared or committed. Switching to the native account removes the active third-party bearer token from `config.toml`.
