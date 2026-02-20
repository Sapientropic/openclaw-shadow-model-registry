# OpenClaw 接入 Gemini 3.1 Pro（API 路线）

这份教程用于把 OpenClaw 稳定切到 `google/gemini-3.1-pro-preview`，并可选绑定 Discord 专用频道。  
核心思路：不用 OAuth，直接用 `GEMINI_API_KEY`。

## 适用范围

- OpenClaw：`2026.2.19-2`（及相近版本）
- 系统：macOS（其他系统命令同理）
- 目标模型：`gemini-3.1-pro-preview`
- 更新时间：2026-02-20

## 1. 准备 API Key

在 [Google AI Studio](https://aistudio.google.com/) 创建 Gemini API Key，然后写入本地环境文件：

```bash
read -s "GEMINI_API_KEY?粘贴 GEMINI_API_KEY 后回车: "; echo
mkdir -p ~/.openclaw
if rg -q '^GEMINI_API_KEY=' ~/.openclaw/.env 2>/dev/null; then
  sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_API_KEY|" ~/.openclaw/.env
else
  printf '\nGEMINI_API_KEY=%s\n' "$GEMINI_API_KEY" >> ~/.openclaw/.env
fi
unset GEMINI_API_KEY
```

## 2. 更新 `~/.openclaw/openclaw.json`

在配置中加入以下四类内容：

1. `agents.defaults.models` 放行 `google/gemini-3.1-pro-preview`
2. `models.providers.google` 声明 API 路径和模型目录
3. 新建 `gemini` agent（主模型 3.1，回退 3.0）
4. （可选）把指定 Discord 频道绑定到 `gemini` agent

可参考：[`examples/openclaw.snippet.json`](./examples/openclaw.snippet.json)

> 注意：这不是完整配置文件，只是最小片段。请合并到你现有 `openclaw.json` 对应位置。

## 3. 重启网关

```bash
openclaw gateway restart
openclaw gateway status --json
```

`status` 里看到 `running` 且 `rpc.ok=true` 即正常。

## 4. 验收（必须做）

先看模型解析：

```bash
openclaw models status --json --agent gemini
```

应看到：

- `defaultModel = google/gemini-3.1-pro-preview`
- `resolvedDefault = google/gemini-3.1-pro-preview`

再做一次真实调用：

```bash
openclaw agent --local --agent gemini --message '只回复 OK' --json --timeout 45
```

应看到：

- `payloads[0].text = OK`
- `meta.agentMeta.provider = google`
- `meta.agentMeta.model = gemini-3.1-pro-preview`

## 5. 常见报错与解决

### `Unknown model: google/gemini-3.1-pro-preview`

- 原因：`models.providers.google.models` 没有注册 `gemini-3.1-pro-preview`
- 处理：按示例片段补齐 provider 目录和模型 ID，再重启网关

### `ERR_CONNECTION_REFUSED (localhost)`

- 原因：OpenClaw gateway 未启动或端口异常
- 处理：执行 `openclaw gateway restart`，再 `openclaw gateway status --json` 检查

### `HTTP 401 ... VERCEL_OIDC_TOKEN`

- 这是 Vercel AI Gateway 的 OIDC 路线报错，不是 Google API 路线
- 如果走本教程 API 路线，忽略该报错并使用 `GEMINI_API_KEY`

## 6. Discord 专用频道示例

在 `router.bindings` 增加：

```json
{
  "agentId": "gemini",
  "match": {
    "channel": "discord",
    "peer": { "kind": "channel", "id": "REPLACE_WITH_CHANNEL_ID" }
  }
}
```

这样该频道就会固定走 `gemini` agent（即 3.1 Pro）。

## 7. 安全建议

- 不要提交 `~/.openclaw/.env`
- 不要把真实 API Key 放到 GitHub
- 分享截图前打码邮箱、Token、Project ID

---

如果你只需要“一条命令验证是否成功”，用这条：

```bash
openclaw agent --local --agent gemini --message '只回复 OK' --json --timeout 45 | jq -r '.meta.agentMeta | "\(.provider) \(.model)"'
```

输出 `google gemini-3.1-pro-preview` 即通过。
