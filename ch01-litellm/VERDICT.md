# Chapter 1 verdict: LiteLLM vs the hand-rolled provider layer

Written from real runs on 2026-07-14 (litellm 1.92.0, openai 2.45.0,
anthropic 0.116.0; models: gpt-4o-mini, claude-haiku-4-5, qwen3:8b via
Ollama). Reproduce with `secrun python ch01-litellm/compare.py`; every claim
below came out of that script or the two implementations' own runs.

## What the router bought

- **One shape for everything.** Chat, streaming, and the full tool-call dance
  run through a single code path for all three providers. The hand-rolled
  version is 225 lines for 3 providers and grows a branch per provider; the
  port is 148 lines and flat in providers (~100 supported). The translation
  work didn't disappear; it became someone else's maintained code, which is
  the entire product.
- **The pricing table stopped being your chore.** On identical token counts,
  `completion_cost()` agreed with the dives' hand-maintained table to the
  digit on both paid models (e.g. anthropic 19 in / 42 out → $0.000229 from
  both). Today they agree; the difference is what happens the day a price
  changes: one map is maintained upstream, the other is you remembering.
- **Cross-provider fallback in one kwarg.** A request to a nonexistent model
  with `fallbacks=["anthropic/claude-haiku-4-5"]` came back answered by
  claude-haiku-4-5. Hand-rolling that means try/except across two SDKs'
  exception hierarchies.

## What it cost

- **Install friction, immediately.** Passing `tools=` to `completion()`
  crashed with `ModuleNotFoundError: fastapi`, then (fastapi installed)
  `orjson`: undeclared dependencies pulled in by an MCP proxy handler even
  in plain SDK use. Two pins in requirements.txt exist only to work around
  this (see the comments there).
- **You debug the router's errors, not the provider's.** The same mistake (a
  model name that doesn't exist) surfaces three different ways (compare.py
  §2):
  - raw SDK: `NotFoundError: Error code: 404 ... The model does not exist` 
    the provider talking to you.
  - litellm, bare name: `BadRequestError: LLM Provider NOT provided`, the
    router failing to *route*, before any request is made. Nothing in that
    message says "typo in model name."
  - litellm, `openai/` prefix: the real 404, wrapped in litellm's exception
    type.
- **The prefix picks a code path, and one of them fails silently.** The same
  local model, same tool call: `ollama_chat/qwen3:8b` answers; `ollama/qwen3:8b`
  returns an **empty string** for the final turn: no exception, no warning
  (compare.py §3). The hand-rolled version (Ollama's own OpenAI-compat
  endpoint) answers fine, so the gap is in the router's translation layer.
  This is the abstraction tax in its purest form: a bug you can't see from
  your own code, in a layer you didn't write, triggered by a naming
  convention.
- **Fallback convenience is fallback opacity.** When the fallback demo
  succeeded, the primary model's failure appeared only as a logger `ERROR`
  with a traceback; the returned response object looks like a clean success.
  In production you'd want that surfaced in your observability, or you'll
  discover your primary has been down for a week from the invoice.

## When you'd still hand-roll

Two providers you control, a thin wrapper, and a hard requirement to see raw
provider errors: the 225 lines are honest and debuggable, and you drop a
dependency that (this version, at least) can't install its own imports for
tool calls. The router wins as soon as provider count, fallback policy, or
pricing upkeep become real work, which in a team setting is quickly.

## The interview sentence

"LiteLLM does exactly what my hand-rolled layer does, re-dress an
OpenAI-shaped request per provider, so I know both why I'd adopt it (the
translation and pricing upkeep scale with providers, and I shouldn't own
that) and where it'll bite (its errors are one layer removed from the
provider's, and its per-route translations can fail in ways the provider's
own API doesn't)."
