# Build plan: professional-tools-deep-dive

Working doc. Continue from the first unchecked milestone. Keep commits small:
one file per commit where the file is likely to stay stable; err on the side
of over-committing.

> Tool slate verified against mid-2026 usage via web search on
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
  injection is a *hypothesis*: run the red-team eval and report whatever
  comes out, including a refuted prediction (AUTHORING-LESSONS §12).
- **Keys** via `secrun` (Keychain wrapper), never .env. Keyless runs fail
  loudly (no silent mock fallback in this repo); where a chapter can run
  fully local (Ollama), prefer that path as the default.
- **Deps**: single `.venv` (zsh chpwd hook auto-activates), one pinned
  `requirements.txt` at root *until the resolver fights back*: LlamaIndex,
  LangGraph, and Guardrails AI in one env is a known conflict risk. If it
  breaks, split into per-chapter `requirements.txt` and write that up as part
  of the version-churn lesson, not as a footnote.
- **Structure**: `ch01-litellm/`, `ch02-instructor/`, ... each with
  `hand_rolled.py` (the baseline, ported in), `with_tool.py` (the port),
  `compare.py` (runs the shared eval on both), `VERDICT.md`.

## Milestones

- [x] **M0, scaffold**: git init, LICENSE, .gitignore, README, this plan.
- [x] **M1, ch01 LiteLLM** (done 2026-07-14; see ch01-litellm/VERDICT.md 
      costs agreed to the digit, errors surface a layer removed, `ollama/`
      vs `ollama_chat/` silent tool-call failure): baseline = the hand-rolled
      provider layer
      (openai/claude dives). Port: same three calls (chat, streaming, tool
      call) through LiteLLM against OpenAI + Anthropic + Ollama; exercise
      fallbacks and its cost tracking vs the hand-rolled token math.
      Verdict question: what does a router buy over a thin wrapper, and what
      does it hide when a provider errors?
- [x] **M2, ch02 Instructor** (done 2026-07-14; see ch02-instructor/VERDICT.md
      60/60 extractions succeeded across all three approaches and both
      models, all 34 semantic traps passed; the differences were retry
      ownership, portability, and a 2× constrained-decoding latency cost on
      Ollama): baseline = prompt-engineering dive's
      extract-JSON-and-retry loop. Port the same extraction schema via
      instructor + Pydantic. Measure: parse-failure rate over N runs on the
      same inputs, hand-rolled vs instructor vs provider-native structured
      output (three-way; the provider mode is the real competitor now).
      Mention BAML in the verdict as the rising schema-first alternative
      (2026 reviews call instructor "starting to feel outdated" next to it);
      don't port to it unless the three-way leaves the story incomplete.
- [x] **M3, ch03 LlamaIndex** (done 2026-07-14; see ch03-llamaindex/VERDICT.md
      accuracy tied 100% across hand-rolled / LI-defaults / LI-matched on
      12 questions (corpus-bound, not framework-bound); the port silently
      dropped the citation contract 12/12 → 0/12; shipped defaults were
      ada-002 + gpt-3.5-turbo + 1024-token chunks + k=2): baseline =
      rag-deep-dive's final pipeline.
      Port chunk→embed→retrieve→cite on the *same corpus*; score both with
      the dive's hit-rate/MRR eval. Verdict: where do its defaults
      (chunking, top-k, prompt templates) differ from yours, and does it show?
- [x] **M4, ch04 DeepEval** (done 2026-07-14; see ch04-deepeval/VERDICT.md 
      FaithfulnessMetric = absence-of-contradiction, so a pure invention
      scored 1.00 every run; the pytest gate flipped verdicts across reruns
      on fixed inputs; ~7× time, ~12× cost vs the one-call judge; the
      click/huggingface-hub pin pair in requirements.txt is this chapter's
      resolver story): baseline = evals-deep-dive harness. Re-express
      one eval suite (cases + judge metrics + threshold gate) as DeepEval
      pytest tests; run both on the same model pair, compare verdicts and
      ergonomics; wire the DeepEval gate into CI as the artifact. Name-check
      Ragas (RAG-specific metrics standard) and the common "open-source
      framework for CI + platform (Braintrust/LangSmith) for production"
      two-tool pattern.
- [x] **M5, ch05 LangGraph** (done 2026-07-14; see ch05-langgraph/VERDICT.md
      dead tie on the five-task eval: 10/10, 2.0 llm calls, 1.0 tool
      calls, ~1.5s/task for BOTH; real differences are the approval
      architecture (callback vs durable interrupt/checkpoint/resume) and
      create_react_agent deprecating mid-chapter): baseline =
      agents-deep-dive loop. Port the
      same tools + task set; measure steps-to-completion and success rate on
      the dive's task eval. Reuse the COMPARISON.md instincts from
      askrepo-langchain (separate project) but keep this chapter minimal 
      loop, state, one human-in-the-loop interrupt.
- [x] **M6, ch06 Llama Guard + Guardrails AI** (done 2026-07-16 after the
      pull finally finalized on retry, `llama-guard3:1b`; the 8B blob never
      finalized). See ch06-guardrails/VERDICT.md. **Prediction confirmed:**
      Llama Guard 3 = perfect on harmful (4/4, correct S1/S2/S11 codes, 0
      false positives) and blind to injection (0/3 indirect, missed
      doc_phishing_line); its taxonomy has no injection cell. The surprise,
      confirmed: the managed model covers no category the dive's own llm_guard
      didn't already (llm_guard: 6/6 direct, 3/3 indirect, 4/4 harmful, and
      the ONLY guard to block doc_phishing_line). Guardrails AI's wrapped
      regex detected identically to the bare heuristic (framework = scaffolding
      not detection); its Hub is account-gated (401; custom Validator is the
      keyless path). compare.py drops unreachable guards loudly (never scores
      an unavailable guard as a miss (the near-miss caught during the block).
- [x] **M7, ch07 Langfuse** (done 2026-07-16; self-hosted v3.217 via docker,
      6 containers, headless project init, keyless). See
      ch07-langfuse/VERDICT.md. Both sides capture the same per-request record
      (the hand-rolled tracer even computes cost); the platform's real
      additions are persistence, a query API, a UI, server-side pricing, and
      sharing. Measured: Langfuse priced the run to the digit ($0.000111 ==
      hand-rolled) from tokens alone, using its own model-pricing map. Cost:
      six always-on containers + schema lock-in. Churn tax again: had to remap
      postgres 5432 / redis 6379 host ports (local services own them), and the
      SDK's canonical calls moved (start_as_current_span -> _observation;
      set_trace_io already deprecated). Loud auth_check() so an unreachable
      server can't masquerade as "no traces" (ch06 discipline).
- [ ] **M8, series wiring**: EXERCISES.md (grown per chapter, may land
      earlier), TEXTBOOK.md chapter (match the series pattern), GitHub remote
      + submodule in the parent repo, add to README/CHOOSING/CAREERS in the
      parent, CI (pinned-install + compare.py smoke runs).

## Open questions (decide when reached)

- ~~ch04: promptfoo vs Braintrust vs Ragas~~, resolved 2026-07-14: promptfoo
  acquired by OpenAI and folding into their platform; DeepEval is the 2026
  open-source CI-eval standard. Revisit only if DeepEval can't express the
  judge-bias controls from the evals dive.
- ch07: self-hosted Langfuse vs cloud free tier; self-hosted preferred;
  fall back to cloud if docker friction eats the lesson.
- Whether ch06 also needs NeMo Guardrails: only if Guardrails AI turns out
  to cover a different niche (validators) than the chapter's point needs.
