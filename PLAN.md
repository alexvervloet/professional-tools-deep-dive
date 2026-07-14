# Build plan — professional-tools-deep-dive

Working doc. Continue from the first unchecked milestone. Keep commits small:
one file per commit where the file is likely to stay stable; err on the side
of over-committing.

> Tool slate verified against the mid-2026 landscape via web search on
> 2026-07-14 (adoption surveys, download stats, acquisition news). Notable:
> promptfoo acquired by OpenAI (2026-03, folding into their Frontier
> platform) → ch04 switched to DeepEval; Langfuse acquired by ClickHouse
> (2026-01) but still open-source/self-hostable; LangGraph confirmed the
> production default (~39M monthly PyPI downloads); "LlamaIndex for the RAG
> layer + LangGraph for orchestration" is the published 2026 consensus.
> Re-verify before starting any chapter that's been sitting a while.

## Ground rules (decided up front)

- **Method per chapter** (mirrors README): recap primitive → introduce tool →
  minimal port → run the *same eval* on hand-rolled vs tool → VERDICT.md
  written from the actual run. A chapter is done only when the verdict cites
  numbers from a run that happened (AUTHORING-LESSONS §1–2, §12).
- **Reuse the measuring sticks, don't rebuild them.** The retrieval metrics
  (hit-rate/MRR) come from rag-deep-dive, the red-team eval from
  prompt-injection-deep-dive, the judge harness from evals-deep-dive. Copy the
  minimal pieces in (with a comment pointing home) rather than importing
  across repos.
- **Predictions get measured, not assumed.** E.g. the expectation that Llama
  Guard (a content-safety classifier) will miss task-aligned indirect
  injection is a *hypothesis* — run the red-team eval and report whatever
  comes out, including a refuted prediction (AUTHORING-LESSONS §12).
- **Keys** via `secrun` (Keychain wrapper), never .env. Keyless runs fail
  loudly — no silent mock fallback in this repo; where a chapter can run
  fully local (Ollama), prefer that path as the default.
- **Deps**: single `.venv` (zsh chpwd hook auto-activates), one pinned
  `requirements.txt` at root *until the resolver fights back* — LlamaIndex,
  LangGraph, and Guardrails AI in one env is a known conflict risk. If it
  breaks, split into per-chapter `requirements.txt` and write that up as part
  of the version-churn lesson, not as a footnote.
- **Structure**: `ch01-litellm/`, `ch02-instructor/`, … each with
  `hand_rolled.py` (the baseline, ported in), `with_tool.py` (the port),
  `compare.py` (runs the shared eval on both), `VERDICT.md`.

## Milestones

- [x] **M0 — scaffold**: git init, LICENSE, .gitignore, README, this plan.
- [x] **M1 — ch01 LiteLLM** (done 2026-07-14; see ch01-litellm/VERDICT.md —
      costs agreed to the digit, errors surface a layer removed, `ollama/`
      vs `ollama_chat/` silent tool-call failure): baseline = the hand-rolled
      provider layer
      (openai/claude dives). Port: same three calls (chat, streaming, tool
      call) through LiteLLM against OpenAI + Anthropic + Ollama; exercise
      fallbacks and its cost tracking vs the hand-rolled token math.
      Verdict question: what does a router buy over a thin wrapper, and what
      does it hide when a provider errors?
- [ ] **M2 — ch02 Instructor**: baseline = prompt-engineering dive's
      extract-JSON-and-retry loop. Port the same extraction schema via
      instructor + Pydantic. Measure: parse-failure rate over N runs on the
      same inputs, hand-rolled vs instructor vs provider-native structured
      output (three-way — the provider mode is the real competitor now).
      Mention BAML in the verdict as the rising schema-first alternative
      (2026 reviews call instructor "starting to feel outdated" next to it);
      don't port to it unless the three-way leaves the story incomplete.
- [ ] **M3 — ch03 LlamaIndex**: baseline = rag-deep-dive's final pipeline.
      Port chunk→embed→retrieve→cite on the *same corpus*; score both with
      the dive's hit-rate/MRR eval. Verdict: where do its defaults
      (chunking, top-k, prompt templates) differ from yours, and does it show?
- [ ] **M4 — ch04 DeepEval**: baseline = evals-deep-dive harness. Re-express
      one eval suite (cases + judge metrics + threshold gate) as DeepEval
      pytest tests; run both on the same model pair, compare verdicts and
      ergonomics; wire the DeepEval gate into CI as the artifact. Name-check
      Ragas (RAG-specific metrics standard) and the common "open-source
      framework for CI + platform (Braintrust/LangSmith) for production"
      two-tool pattern.
- [ ] **M5 — ch05 LangGraph**: baseline = agents-deep-dive loop. Port the
      same tools + task set; measure steps-to-completion and success rate on
      the dive's task eval. Reuse the COMPARISON.md instincts from
      askrepo-langchain (separate project) but keep this chapter minimal —
      loop, state, one human-in-the-loop interrupt.
- [ ] **M6 — ch06 Llama Guard + Guardrails AI**: baseline = prompt-injection
      dive's detectors + output checks. Llama Guard 3 runs locally via
      Ollama. Score managed vs hand-rolled with the dive's red-team eval,
      including `doc_phishing_line`. Report per-attack-category results.
- [ ] **M7 — ch07 Langfuse**: baseline = production dive's tracing + prompt
      versioning and observability dive's metrics. Self-host Langfuse via
      docker compose (keeps it keyless/local). Instrument one small app both
      ways; verdict on what a platform buys over structured logs you own.
- [ ] **M8 — series wiring**: EXERCISES.md (grown per chapter, may land
      earlier), TEXTBOOK.md chapter (match the series pattern), GitHub remote
      + submodule in the parent repo, add to README/CHOOSING/CAREERS in the
      parent, CI (pinned-install + compare.py smoke runs).

## Open questions (decide when reached)

- ~~ch04: promptfoo vs Braintrust vs Ragas~~ — resolved 2026-07-14: promptfoo
  acquired by OpenAI and folding into their platform; DeepEval is the 2026
  open-source CI-eval standard. Revisit only if DeepEval can't express the
  judge-bias controls from the evals dive.
- ch07: self-hosted Langfuse vs cloud free tier — self-hosted preferred;
  fall back to cloud if docker friction eats the lesson.
- Whether ch06 also needs NeMo Guardrails — only if Guardrails AI turns out
  to cover a different niche (validators) than the chapter's point needs.
