# Security Policy

## Reporting a vulnerability

Please do not publish credentials or a reproducible exploit in a public issue.

Report security concerns through GitHub's private vulnerability reporting feature for this repository. Include the affected version, platform, impact, and the minimum steps needed to reproduce the issue. Remove API keys, account tokens, `auth.json`, and private history content from all screenshots and logs.

## Credential handling

CodexShift stores Provider snapshots locally. Secrets are protected with Windows DPAPI or macOS Keychain. Codex's own `auth.json` remains sensitive and should never be shared or committed.
