# CodexShift

<p align="center">
  <img src="assets/codexshift-logo.png" alt="CodexShift logo" width="160">
</p>

<p align="center">
  <strong>在 Codex 官方账号与第三方 API 之间安全切换，并自动修复历史索引。</strong>
</p>

<p align="center">
  <a href="https://github.com/HanLoney/CodexShift/releases/latest">下载最新版</a> ·
  <a href="README_EN.md">English</a> ·
  <a href="https://github.com/HanLoney/CodexShift/issues">问题反馈</a>
</p>

<p align="center">
  <a href="https://github.com/HanLoney/CodexShift/actions/workflows/release.yml"><img src="https://github.com/HanLoney/CodexShift/actions/workflows/release.yml/badge.svg" alt="Build"></a>
  <a href="https://github.com/HanLoney/CodexShift/releases"><img src="https://img.shields.io/github/v/release/HanLoney/CodexShift" alt="Release"></a>
  <a href="LICENSE"><img src="https://img.shields.io/github/license/HanLoney/CodexShift" alt="License"></a>
</p>

CodexShift 是一个独立的桌面切换器，不依赖其他 Provider 管理工具，也不会读取或修改它们的数据。

> [!IMPORTANT]
> CodexShift 是社区项目，不是 OpenAI 官方产品，与 OpenAI 没有隶属或背书关系。

## 功能

- 内置“OpenAI 官方账号（原生）”入口，可恢复已保存的官方登录凭据，或回到原生登录流程。
- 新建、编辑、删除第三方 API 配置。
- 检测 API Key 与接口连通性，并从 OpenAI 兼容的 `/models` 接口自动发现模型。
- 切换配置与认证凭据，自动清理冲突的账号字段。
- 自动识别当前用户的 `CODEX_HOME` / `~/.codex`，也支持手动选择路径。
- 同步 rollout 文件与 `state_5.sqlite` 中的 `model_provider`，补齐遗漏的历史任务索引。
- 切换前自动备份，失败时自动回滚；默认保留最近 3 份备份。
- 简体中文、English、日本語、한국어界面与提示。
- Windows 使用 DPAPI、macOS 使用 Keychain 加密本地 Provider 凭据。

## 下载与使用

前往 [Releases](https://github.com/HanLoney/CodexShift/releases/latest) 下载：

| 系统 | 文件 |
| --- | --- |
| Windows 10/11 x64 | `CodexShift-v1.7.0-Windows-x64.exe` |
| macOS | `CodexShift-v1.7.0-macOS-Universal.zip` |

1. 打开 CodexShift，确认顶部显示的 Codex Home 路径正确。
2. 选择内置官方账号，或新建一个第三方 API 配置。
3. 可先点击“检测 API”，确认接口、密钥和模型可用。
4. 选择目标 Provider，点击“切换到选中 Provider”。

切换时 Codex 需要退出。建议保留“自动关闭 Codex”和“完成后重新打开”。备份目录位于 `~/.codex/switcher_backups`。

### 首次启动提示

- Windows 未签名版本可能触发 SmartScreen，可选择“更多信息”后确认运行。
- macOS 版本使用临时签名，首次打开可在 Finder 中右键应用并选择“打开”。
- 请只从本仓库的 Releases 页面下载。

## 官方账号说明

浏览器中的 Google / ChatGPT 登录 Cookie 不等于 Codex 的 `auth.json` 凭据。若本机没有可恢复的 Codex 官方凭据，切回官方模式后仍需在 Codex 中选择“使用 ChatGPT 登录”，再使用原来的 Google 账号完成授权。

## 从源码运行

需要 Python 3.11+ 和 Tkinter。

```powershell
python codex_switcher.py
```

运行测试：

```powershell
python -m unittest discover -s tests -v
```

构建 Windows：

```powershell
.\build.ps1
```

构建 macOS：

```bash
chmod +x build_macos.sh
./build_macos.sh
```

## 安全与隐私

- 不会上传 API Key、账号令牌、配置或历史记录。
- 不会在日志中输出完整密钥或令牌。
- 所有修改都在本机完成，并在写入前创建备份。
- `auth.json` 本身包含敏感凭据，请勿分享或提交到仓库。
- 安全问题请参阅 [SECURITY.md](SECURITY.md)。

## 许可证

[MIT License](LICENSE)
