# DeepSeek next-model preflight

Use this when:

- you expect a new DeepSeek generation to land soon
- OpenClaw / `pi-ai` / provider catalogs may lag behind
- you want the rollout path ready before the official model details are fully public

This is intentionally **not** a fake runnable `deepseek-v4` example. The safer move is to prepare the checklist and the override skeleton now, then replace the placeholders once the official model id and transport details are public.

## Current call

As of `2026-03-09`:

- OpenClaw already ships multiple DeepSeek-related model lanes
- but I have not found official DeepSeek API docs publicly exposing a finalized `V4` model id / API name / transport contract
- so the safest preparation is:
  - preflight checklist now
  - override skeleton now
  - no hard-coded `deepseek-v4` runnable example yet

## Confirm these on release day

At minimum, confirm these `7` items:

1. official model id
2. provider lane
   - `deepseek/...`
   - `openrouter/...`
   - `huggingface/...`
   - `qianfan/...`
   - `volcengine/...`
3. `baseUrl`
4. `api`
5. reasoning behavior
6. capability envelope
   - `input`
   - `contextWindow`
   - `maxTokens`
7. whether current OpenClaw stable already supports it natively

## Minimal skeleton

Once the official fields are known, start from this:

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

## Fields not to guess early

Do not hard-code these before the official docs are clear:

- `id`
- `name`
- `reasoning`
- `contextWindow`
- `maxTokens`
- `baseUrl`
- `api`

If the first announcement only exposes a marketing name and not a stable API model id, stop there and do not ship a runnable patch yet.

## Recommended release-day flow

1. check official docs / pricing / changelog
2. check whether current OpenClaw stable already includes the model
3. only if stable still lags, copy the skeleton into a temporary overrides file
4. run `--dry-run`
5. run `config validate`
6. run `models status`
7. run a real `agent healthcheck`
8. document the result and decide whether to push an upstream follow-up

## When to upgrade this into a real example

Turn this preflight doc into a real example JSON only after all of these are true:

- the official model id is public
- the provider lane is clear
- at least one real healthcheck passes
- fallback and reasoning semantics are known
- current OpenClaw stable still does not support it natively
