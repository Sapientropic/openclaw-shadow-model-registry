# Archived: Gemini 3.1 Pro Integration

[中文说明](./README.md)

This material is preserved as historical reference from the earlier phase of this repository.

It is archived not because it stopped working, but because it no longer needs to be the main focus here: upstream OpenClaw support for Gemini 3.1 Pro has effectively caught up, while the more reusable long-term problem is the generic Shadow Model Registry workflow.

## Scope

- OpenClaw: `2026.2.19-2` and nearby builds
- OS: macOS
- Target model: `gemini-3.1-pro-preview`
- Updated: 2026-02-20

## Minimal config snippet

Reference: [`./examples/openclaw.snippet.json`](./examples/openclaw.snippet.json)

Core idea:

1. allow `google/gemini-3.1-pro-preview` in `agents.defaults.models`
2. register the provider under `models.providers.google`
3. add a `gemini` agent with 3.1 primary and 3.0 fallback
4. optionally bind a Discord channel to `gemini`

## Verification

```bash
openclaw models status --json --agent gemini
openclaw agent --local --agent gemini --message 'Reply with OK only' --json --timeout 45
```

Success should show:

- `resolvedDefault = google/gemini-3.1-pro-preview`
- response body `OK`
- `meta.agentMeta.provider = google`
- `meta.agentMeta.model = gemini-3.1-pro-preview`

## Note

- If your current problem is “the model is already live but OpenClaw has not fully caught up yet,” this archived single-model guide is no longer the best starting point.
- The main maintained path is now the Shadow Model Registry at:
  - [`../../shadow-model-registry/README.en.md`](../../shadow-model-registry/README.en.md)
