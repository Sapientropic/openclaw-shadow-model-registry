# OpenClaw Shadow Model Registry

[中文说明](./README.md)

This repository is now focused on a reusable `Shadow Model Registry` workflow for OpenClaw.

It is designed for the gap between:

- a model already being released upstream
- OpenClaw accepting the config shape
- but provider wiring, catalogs, thinking whitelists, or display-layer commands still lagging behind

The goal is not to hand-edit live config and hope for the best. The goal is to provide a repeatable forward-compat workflow that:

1. describes new-model patches in a single overrides file
2. syncs them into `openclaw.json`, agent `models.json`, and when needed `sessions.json`
3. runs `config validate`
4. runs `models status`
5. runs a real `agent` healthcheck
6. auto-rolls back on failure

## Quick links

- Main guide: [`./shadow-model-registry/README.en.md`](./shadow-model-registry/README.en.md)
- Chinese guide: [`./shadow-model-registry/README.md`](./shadow-model-registry/README.md)
- Main script: [`./shadow-model-registry/openclaw-model-patch.py`](./shadow-model-registry/openclaw-model-patch.py)
- `openai-codex/gpt-5.4` example: [`./shadow-model-registry/examples/openai-codex-gpt-5.4.json`](./shadow-model-registry/examples/openai-codex-gpt-5.4.json)

## Why this repository exists

- the workflow is not tied to one provider
- it applies to OpenAI / Codex, Gemini, and similar “model ships first, framework support lands later” situations
- it solves a recurring OpenClaw problem class rather than a one-off model integration

## Current status

- the forward-compat workflow for cases like `openai-codex/gpt-5.4` has continued to hold up in local testing on OpenClaw `2026.3.7`
- runtime forward-compat and display-layer / canonical model facts can still diverge; for example, latest stable may still omit config-injected models from `models list --all`
- this repository should not be treated as a permanent substitute for upstream design fixes in catalog / canonical model facts
- the findings have been pushed upstream as OpenClaw issues / PR follow-ups

## Archived material

This repository originally centered on a `Gemini 3.1 Pro API` integration guide. Since upstream support has effectively caught up, that content is now archived instead of being the main maintenance target:

- [`./archive/gemini-3.1-pro/README.en.md`](./archive/gemini-3.1-pro/README.en.md)

If you want to start immediately, this is the shortest path:

```bash
python3 shadow-model-registry/openclaw-model-patch.py \
  --overrides shadow-model-registry/examples/openai-codex-gpt-5.4.json \
  --dry-run
```
