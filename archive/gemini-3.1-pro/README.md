# Gemini 3.1 Pro 接入归档

[English README](./README.en.md)

这部分内容是该仓库早期主线，保留为历史资料。

之所以归档，不是因为它无效，而是因为这个问题类型现在已经不再需要单独占据仓库主线：OpenClaw 官方对 Gemini 3.1 Pro 的支持已经补齐，后续维护重心转向更通用的 Shadow Model Registry。

## 适用范围

- OpenClaw：`2026.2.19-2`（及相近版本）
- 系统：macOS（其他系统命令同理）
- 目标模型：`gemini-3.1-pro-preview`
- 更新时间：2026-02-20

## 最小配置片段

参考：[`./examples/openclaw.snippet.json`](./examples/openclaw.snippet.json)

核心思路：

1. 在 `agents.defaults.models` 放行 `google/gemini-3.1-pro-preview`
2. 在 `models.providers.google` 注册 provider 与模型目录
3. 新建 `gemini` agent（主模型 3.1，回退 3.0）
4. 可选绑定 Discord 频道到 `gemini`

## 验证方式

```bash
openclaw models status --json --agent gemini
openclaw agent --local --agent gemini --message '只回复 OK' --json --timeout 45
```

成功时应看到：

- `resolvedDefault = google/gemini-3.1-pro-preview`
- 返回正文 `OK`
- `meta.agentMeta.provider = google`
- `meta.agentMeta.model = gemini-3.1-pro-preview`

## 备注

- 如果你今天碰到的是“新模型已经上线，但 OpenClaw 还没完全纳入”的问题，不建议再从这条单模型教程出发。
- 新的主线入口是根目录的 Shadow Model Registry：
  - [`../../shadow-model-registry/README.md`](../../shadow-model-registry/README.md)
