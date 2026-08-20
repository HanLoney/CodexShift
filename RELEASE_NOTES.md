# CodexShift 1.8.0

本版本加入 Codex 与 DeepSeek Harness 的双向项目/会话迁移，并重点升级了 Codex → DSH 的历史恢复质量。

## 主要功能

- 按项目与独立会话分区浏览，可普通点击累积多选
- Codex ↔ DeepSeek Harness 双向选择性迁移
- Codex → DSH 将用户/助手消息逐条恢复为原生会话，不再拼成单条 Markdown
- 原生历史写入不会触发模型回答，也不会产生额外 API 用量
- 自动发现 DeepSeek Harness 动态端口与桌面运行时
- 修复包含特殊字符、颜文字时的 Windows GBK 导入超时
- 导入前后校验、失败清理及本地 localhost 限制
- 修复 DSH → Codex 提示成功但会话不可见：现在会同步写入 Codex 项目归属和原生来源
- “修复历史索引”可自动找回旧版本已导入但未显示的 DSH 会话
- 修复当前 Codex Desktop 打开导入会话时提示 `does not start with session metadata` 的问题
- 修复项目和会话已显示、但打开后聊天内容为空的问题
- 修复历史索引时优先从原 DSH 会话重建可见对话，并过滤运行时上下文与系统提醒
- 从 DSH 导入 Codex 时自动关闭 Codex，导入完成后自动重新启动；失败回滚后也会恢复启动
- 导入过程改为后台执行，并显示百分比、当前会话、运行阶段和可滚动的实时日志
- 预览、导入和取消按钮固定显示，在较小屏幕或窗口高度下也不会被进度区挤出界面
- 仅导入项目时不再生成占位会话
- 继续支持 Provider 切换、API 检测和 Codex 历史任务索引修复

## 下载

- Windows：`CodexShift-v1.8.0-Windows-x64.exe`
- macOS：`CodexShift-v1.8.0-macOS-Universal.zip`

Windows 和 macOS 应用当前均未使用商业开发者证书签名，首次启动时系统可能显示安全提示。请只从本仓库的 Releases 页面下载。

> CodexShift 是独立社区项目，不是 OpenAI 官方产品，与 OpenAI 没有隶属或背书关系。
