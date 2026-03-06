# OpenClaw Model Integration Guide

[中文说明](./README.md)

This repository now contains two tracks:

- `Gemini 3.1 Pro API path`: use OpenClaw with `google/gemini-3.1-pro-preview`
- `Shadow Model Registry`: locally patch OpenClaw when upstream model catalogs lag behind newly released models

Quick links:

- Gemini snippet: [`./examples/openclaw.snippet.json`](./examples/openclaw.snippet.json)
- Shadow Model Registry: [`./shadow-model-registry/README.en.md`](./shadow-model-registry/README.en.md)

---

# OpenClaw + Gemini 3.1 Pro via API

This guide switches OpenClaw to `google/gemini-3.1-pro-preview` using `GEMINI_API_KEY` instead of OAuth.

## Scope

- OpenClaw: `2026.2.19-2` and nearby builds
- OS: macOS
- Target model: `gemini-3.1-pro-preview`
- Updated: 2026-02-20

## 1. Set `GEMINI_API_KEY`

Create a Gemini API key in [Google AI Studio](https://aistudio.google.com/) and write it into `~/.openclaw/.env`:

```bash
read -s "GEMINI_API_KEY?Paste GEMINI_API_KEY and press Enter: "; echo
mkdir -p ~/.openclaw
if rg -q '^GEMINI_API_KEY=' ~/.openclaw/.env 2>/dev/null; then
  sed -i '' "s|^GEMINI_API_KEY=.*|GEMINI_API_KEY=$GEMINI_API_KEY|" ~/.openclaw/.env
else
  printf '\nGEMINI_API_KEY=%s\n' "$GEMINI_API_KEY" >> ~/.openclaw/.env
fi
unset GEMINI_API_KEY
```

## 2. Update `~/.openclaw/openclaw.json`

Add these pieces:

1. allow `google/gemini-3.1-pro-preview` in `agents.defaults.models`
2. register `models.providers.google`
3. add a `gemini` agent with 3.1 as primary and 3.0 as fallback
4. optionally bind a Discord channel to the `gemini` agent

Reference: [`./examples/openclaw.snippet.json`](./examples/openclaw.snippet.json)

## 3. Restart the gateway

```bash
openclaw gateway restart
openclaw gateway status --json
```

## 4. Verify with a real call

Check model resolution:

```bash
openclaw models status --json --agent gemini
```

Then run a real request:

```bash
openclaw agent --local --agent gemini --message 'Reply with OK only' --json --timeout 45
```

Expected result:

- `payloads[0].text = OK`
- `meta.agentMeta.provider = google`
- `meta.agentMeta.model = gemini-3.1-pro-preview`

## 5. Common errors

### `Unknown model: google/gemini-3.1-pro-preview`

- Cause: `models.providers.google.models` does not include the model
- Fix: register it in the provider catalog, then restart the gateway

### `ERR_CONNECTION_REFUSED (localhost)`

- Cause: OpenClaw gateway is not running
- Fix: run `openclaw gateway restart`, then confirm with `openclaw gateway status --json`

### `HTTP 401 ... VERCEL_OIDC_TOKEN`

- That belongs to a Vercel AI Gateway OIDC route, not the direct Google API route in this guide
- If you follow this guide, ignore it and use `GEMINI_API_KEY`

## 6. Discord channel binding example

```json
{
  "agentId": "gemini",
  "match": {
    "channel": "discord",
    "peer": { "kind": "channel", "id": "REPLACE_WITH_CHANNEL_ID" }
  }
}
```

## 7. Security notes

- Do not commit `~/.openclaw/.env`
- Do not push real API keys to GitHub
- Redact email, token, and project identifiers before sharing screenshots

If you only want a one-line verification:

```bash
openclaw agent --local --agent gemini --message 'Reply with OK only' --json --timeout 45 | jq -r '.meta.agentMeta | "\(.provider) \(.model)"'
```

If it prints `google gemini-3.1-pro-preview`, the setup is working.
