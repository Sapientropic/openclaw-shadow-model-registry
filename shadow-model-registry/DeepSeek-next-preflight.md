# DeepSeek 下一代模型预兼容预检

适用场景：

- 你预期 DeepSeek 很快会发新一代模型
- OpenClaw / `pi-ai` / provider catalog 可能会慢半拍
- 你想提前把“落地步骤”和“最容易出错的字段”准备好

这份文档的目标不是提前伪造一个可执行的 `deepseek-v4` 示例，而是把真正会决定成败的未知项先框出来。等官方信息一出，只需要把占位字段替换掉，再跑一次标准验证流程。

## 当前判断

截至 `2026-03-09`：

- OpenClaw 本体已经内置了多条 DeepSeek 相关模型线
- 但我还没有看到 DeepSeek 官方 API 文档公开 `V4` 的正式模型名 / 接口名 / transport 细节
- 所以现在最稳的做法是：
  - 先准备 preflight checklist
  - 先准备 override skeleton
  - 不要提前把 `deepseek-v4` 当成确定 model id 写死

## 发布当天先确认什么

至少确认这 `7` 件事：

1. 官方模型 id
   - 例如是否是：
     - `deepseek-chat-v4`
     - `deepseek-v4`
     - `deepseek-reasoner-v4`
     - 或别的命名
2. provider lane
   - 是 OpenClaw 里的 `deepseek/...`
   - 还是先通过 `openrouter/...`
   - `huggingface/...`
   - `qianfan/...`
   - `volcengine/...`
3. `baseUrl`
   - 是否仍是当前 DeepSeek 官方兼容接口
4. `api`
   - 是否仍走 `openai-completions`
   - 还是出现了单独的 provider transport
5. reasoning 语义
   - 新模型是否默认 reasoning
   - 是否需要单独 thinking / reasoning lane
6. 能力边界
   - `input`
   - `contextWindow`
   - `maxTokens`
7. OpenClaw 是否已经原生跟上
   - `models status` 能否直接识别
   - `models list --all` 是否显示正常
   - 是否仍需要 allowlist / provider registry 补丁

## 最小 skeleton

等官方字段确定后，可以从这个骨架开始：

```json
{
  "providers": {
    "deepseek": {
      "baseUrl": "REPLACE_WITH_OFFICIAL_BASE_URL",
      "api": "openai-completions",
      "models": [
        {
          "id": "REPLACE_WITH_OFFICIAL_MODEL_ID",
          "name": "REPLACE_WITH_DISPLAY_NAME",
          "reasoning": true,
          "input": [
            "text"
          ],
          "contextWindow": 128000,
          "maxTokens": 8192
        }
      ]
    }
  },
  "agents": {
    "eng": {
      "model": {
        "primary": "deepseek/REPLACE_WITH_OFFICIAL_MODEL_ID",
        "fallbacks": [
          "zai/glm-5"
        ]
      },
      "allowlist": {
        "deepseek/REPLACE_WITH_OFFICIAL_MODEL_ID": {}
      },
      "healthcheck": {
        "prompt": "healthcheck: reply with OK and current provider/model only",
        "expectProvider": "deepseek",
        "expectModel": "REPLACE_WITH_OFFICIAL_MODEL_ID",
        "expectText": "OK deepseek/REPLACE_WITH_OFFICIAL_MODEL_ID",
        "timeoutSeconds": 120
      }
    }
  }
}
```

## 不要提前写死的字段

下面这些最容易因为“凭印象先写”而踩坑：

- `id`
- `name`
- `reasoning`
- `contextWindow`
- `maxTokens`
- `baseUrl`
- `api`

如果官方第一波只公布 marketing 名字，没有明确 API model id，就先不要落可执行补丁。

## 建议的发布日流程

1. 先查官方 docs / pricing / changelog
2. 再查 OpenClaw 当前 stable 是否已经内置
3. 如果 stable 还没跟上，再复制上面的 skeleton 落成临时 overrides
4. 先 `--dry-run`
5. 再 `config validate`
6. 再 `models status`
7. 再跑真实 `agent healthcheck`
8. 记录结果并决定要不要同步 upstream

## 什么时候值得把它变成正式示例

满足下面条件后，再把这份预检文档升级成正式示例 JSON：

- 官方 model id 已明确
- provider lane 已明确
- 至少跑通一次真实 healthcheck
- 明确知道 fallback 和 reasoning 语义
- 确认不是 OpenClaw stable 已原生支持、无需 shadow patch
