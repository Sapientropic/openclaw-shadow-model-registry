# OpenClaw Shadow Model Registry

[中文说明](./README.md)

When a new model is already live but OpenClaw or `pi-ai` has not added it to the catalog yet, this workflow lets you patch it in locally through a shadow registry layer.

The goal is not to force config changes blindly. The goal is to:

1. sync overrides into `~/.openclaw/openclaw.json`
2. sync provider patches into the target agent's `models.json`
3. sync `sessions.json` when required
4. run `config validate`
5. run `models status`
6. run a real `agent` healthcheck
7. auto-rollback on failure

## Files

- Main script: [`./openclaw-model-patch.py`](./openclaw-model-patch.py)
- Blank overrides template: [`./examples/openclaw-model-overrides.json`](./examples/openclaw-model-overrides.json)
- OpenAI Codex `gpt-5.4` example: [`./examples/openai-codex-gpt-5.4.json`](./examples/openai-codex-gpt-5.4.json)
- Stable rollback example: [`./examples/openai-codex-stable.json`](./examples/openai-codex-stable.json)

## Good fit for

- a new OpenAI / Codex model ships before OpenClaw adds it
- a Gemini release lands before OpenClaw updates naming or catalog entries
- you want to trial a new model on one agent without manually mutating live config for hours

## Usage

Dry-run first:

```bash
python3 shadow-model-registry/openclaw-model-patch.py \
  --overrides shadow-model-registry/examples/openai-codex-gpt-5.4.json \
  --dry-run
```

Apply for real:

```bash
python3 shadow-model-registry/openclaw-model-patch.py \
  --overrides shadow-model-registry/examples/openai-codex-gpt-5.4.json
```

## Practical lessons

- `config validate` does not prove the model is actually callable
- allowlisting alone is not enough; the provider/model registry must be patched too
- `models status` is valuable, but the final gate must still be a real `openclaw agent` call
- for OAuth-style providers such as `openai-codex`, `baseUrl` and `api` must match OpenClaw's internal transport semantics

## Real pitfall from the `gpt-5.4` rollout

For `openai-codex/gpt-5.4`:

- wrong: `baseUrl=https://api.openai.com/v1`
- correct: `baseUrl=https://chatgpt.com/backend-api`
- correct API: `openai-codex-responses`

The fact that a model exists on the OpenAI API platform does not mean OpenClaw's `openai-codex` OAuth lane can use the plain OpenAI API endpoint.

## Known limitations

- the healthcheck still writes into a real long-lived session transcript
- some display-layer commands may lag behind runtime support
- OpenClaw may still need an upstream thinking whitelist patch for certain new models
