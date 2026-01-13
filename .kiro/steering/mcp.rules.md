---
inclusion: fileMatch
fileMatchPattern: ['**/services.py', '**/llm/**', '**/ai/**', '**/adapters/**']
---

# LLM Integration Rules

Rules for implementing LLM service integrations (Gemini, Qwen, Mistral) in NeuroTwin.

## Pre-Implementation Research

Before adding or modifying any LLM integration:

1. Use web search tools to verify current SDK versions and package names
2. Confirm official packages (e.g., `google-genai` for Gemini, NOT `google-generativeai`)
3. Check for breaking changes or deprecations in target SDK

## Approved Packages

| Provider | Package | Env Variable |
|----------|---------|--------------|
| Google Gemini | `google-genai` | `GOOGLE_GENAI_API_KEY` |
| Qwen | TBD | `QWEN_API_KEY` |
| Mistral | TBD | `MISTRAL_API_KEY` |

Install via: `uv add <package-name>`

## Architecture Requirements

- All LLM calls MUST go through adapter classes in `apps/*/adapters/` or `core/adapters/`
- Never call LLM APIs directly from views, serializers, or models
- Adapters must implement a common interface for provider swapping

## Async & Performance

- All LLM calls MUST be async or run in background tasks
- Never block HTTP request threads with synchronous LLM operations
- Implement exponential backoff for rate limit handling
- Set reasonable timeouts (30s default, configurable)

## Error Handling

- Catch and log all API errors with context (model, prompt length, timestamp)
- Implement fallback behavior when LLM is unavailable
- Return graceful degradation responses, never expose raw API errors

## Audit & Logging

- Log every LLM interaction: timestamp, model, token count, latency, success/failure
- Store prompts and responses for audit (respect data retention policies)
- Include Cognitive Blend value when generating Twin responses

## Security

- API keys in `.env` only, never hardcoded
- Sanitize user input before including in prompts
- Implement token/cost limits per user session
