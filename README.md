# OpenClaw 影子模型目录

[English README](./README.en.md)

这个仓库现在以 `Shadow Model Registry` 为主，用来处理一种很常见的空窗期问题：

- 新模型已经发布
- OpenClaw 配置层能写
- 但上游 catalog / provider / thinking whitelist / 显示层还没完全跟上

目标不是“手改一堆配置碰碰运气”，而是提供一套可复用的本地前向兼容机制：

1. 用 overrides 统一描述新模型补丁
2. 同步到 `openclaw.json`、agent `models.json`、必要时 `sessions.json`
3. 执行 `config validate`
4. 执行 `models status`
5. 执行真实 `agent healthcheck`
6. 失败自动回滚

## 快速入口

- 主说明：[`./shadow-model-registry/README.md`](./shadow-model-registry/README.md)
- 英文说明：[`./shadow-model-registry/README.en.md`](./shadow-model-registry/README.en.md)
- DeepSeek 下一代模型预检：[`./shadow-model-registry/DeepSeek-next-preflight.md`](./shadow-model-registry/DeepSeek-next-preflight.md)
- 主脚本：[`./shadow-model-registry/openclaw-model-patch.py`](./shadow-model-registry/openclaw-model-patch.py)
- `openai-codex/gpt-5.4` 示例：[`./shadow-model-registry/examples/openai-codex-gpt-5.4.json`](./shadow-model-registry/examples/openai-codex-gpt-5.4.json)

## 为什么单独做这个仓库

- 这套机制不绑定某一个模型供应商
- 不只适用于 OpenAI / Codex，也适用于 Gemini 等“新模型先发布、框架后补支持”的场景
- 它解决的是 OpenClaw 的一个长期问题类型，而不是某一次单点接入

## 当前状态

- `openai-codex/gpt-5.4` 这类“新模型先发布、OpenClaw catalog 后补”的场景，已在本地 OpenClaw `2026.3.7` 上继续验证过
- 运行层前向兼容和显示层 / canonical model facts 仍可能不同步；例如最新 stable 下，`models list --all` 对 config-injected models 仍可能漏项
- 这类显示层 / canonical facts 缺口目前仍以 OpenClaw 上游 issue / PR 跟进，不应把本仓库误解成上游设计缺口的永久替代
- 相关发现已经整理并反馈到 OpenClaw 上游 issues / PR
- 对“可能很快发布、但官方 model id / transport 还没定”的模型，不建议提前伪造可执行补丁；更稳的是先准备 preflight checklist 和 skeleton

## 历史归档

早期这个仓库主要记录 `Gemini 3.1 Pro API` 接入路径。由于官方现已补齐支持，这部分内容不再作为主线维护，已归档到：

- [`./archive/gemini-3.1-pro/README.md`](./archive/gemini-3.1-pro/README.md)

如果你只想直接开始使用影子模型目录，从这里走：

```bash
python3 shadow-model-registry/openclaw-model-patch.py \
  --overrides shadow-model-registry/examples/openai-codex-gpt-5.4.json \
  --dry-run
```
