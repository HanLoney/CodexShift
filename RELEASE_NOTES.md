# CodexShift 1.9.1

本版在 Provider 切换与 Codex 历史任务索引维护的基础上，加入第三方 API 的 Codex Desktop 兼容配置。切换旧配置时也会自动更新；切回原生官方账号时会清除当前配置中嵌入的第三方 Key。

## 更新

- 第三方 Provider 自动设置 `requires_openai_auth = false` 与 `x-openai-actor-authorization = codex-desktop`，并使用所选配置的 API Key。
- 保留自定义请求头和 TokenDance 的 `X-App-URL: app://codexshift` 归因；内置 TokenDance 一键授权仍可使用。
- 切换时继续同步历史任务的 Provider 引用、修复索引，并在修改前备份、失败时回滚。

兼容请求头并不能保证第三方网关支持所有 Codex 工具，尤其是依赖官方账号或模型能力的功能。启用后当前 API Key 也会以明文写入 Codex 的 `config.toml`，请保护该文件及备份；CodexShift 保存的 Provider 凭据仍使用系统密钥服务加密。

## 下载

- Windows：`CodexShift-v1.9.1-Windows-x64.exe`
- macOS：`CodexShift-v1.9.1-macOS-Universal.zip`

Windows 与 macOS 应用均未使用商业开发者证书签名，请仅从本仓库 Releases 下载。

> CodexShift 是独立社区项目，不是 OpenAI 官方产品，与 OpenAI 没有隶属或背书关系。
