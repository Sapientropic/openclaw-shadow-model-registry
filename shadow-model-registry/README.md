# OpenClaw 影子模型目录

[English README](./README.en.md)

当新模型已经上线，但 OpenClaw / `pi-ai` catalog 还没跟上时，可以先用一层“影子模型目录”补丁把它接进来。

这套做法的目标不是“强行改配置”，而是：

1. 同步补丁到 `~/.openclaw/openclaw.json`
2. 同步补丁到对应 agent 的 `models.json`
3. 必要时同步 `sessions.json`
4. 做 `config validate`
5. 做 `models status`
6. 做真实 `agent healthcheck`
7. 失败就自动回滚

## 文件

- 主脚本：[`./openclaw-model-patch.py`](./openclaw-model-patch.py)
- 空白 overrides：[`./examples/openclaw-model-overrides.json`](./examples/openclaw-model-overrides.json)
- OpenAI Codex `gpt-5.4` 示例：[`./examples/openai-codex-gpt-5.4.json`](./examples/openai-codex-gpt-5.4.json)
- OpenAI Codex 稳态回退示例：[`./examples/openai-codex-stable.json`](./examples/openai-codex-stable.json)

## 适用场景

- OpenAI / Codex 新模型刚发布，但 OpenClaw 还没收录
- Gemini 新版本或命名变化先出来，OpenClaw 还没同步
- 你想给某个 agent 快速试切新模型，但不想长期手改线上配置

## 使用方式

先 dry-run：

```bash
python3 shadow-model-registry/openclaw-model-patch.py \
  --overrides shadow-model-registry/examples/openai-codex-gpt-5.4.json \
  --dry-run
```

正式执行：

```bash
python3 shadow-model-registry/openclaw-model-patch.py \
  --overrides shadow-model-registry/examples/openai-codex-gpt-5.4.json
```

## 经验要点

- 不要把 `config validate` 当成模型可用性的证明
- 不要只改 allowlist，provider/model registry 也要补
- `models status` 很重要，但最后仍然必须做真实 agent 调用
- 对 `openai-codex` 这类 OAuth provider，`baseUrl` 和 `api` 必须对齐 OpenClaw 内置语义

## 这次实战里踩过的坑

以 `openai-codex/gpt-5.4` 为例：

- 错误写法：`baseUrl=https://api.openai.com/v1`
- 正确写法：`baseUrl=https://chatgpt.com/backend-api`
- 正确 API：`openai-codex-responses`

`gpt-5.4` 在 OpenAI 官方 API 平台存在，不代表 OpenClaw 的 `openai-codex` OAuth 通道就能直接走普通 OpenAI API endpoint。

## 已知限制

- 当前 healthcheck 仍会写入真实 session transcript
- 截至 OpenClaw `2026.3.7`，有些展示层命令仍可能比运行层更新慢，例如 `models list --all` 不一定马上列出你补进去的 config-injected model
- 某些 thinking 白名单仍可能需要单独补 OpenClaw 上游
