# Professional Tools: A Guided Deep Dive

Every other repo in this series builds a primitive **from scratch** (the agent
loop, the retriever, the eval harness, the guardrails) because the primitive is
what transfers. This repo is the second half of that bargain: the tools
professionals actually reach for on the job, learned *against* the versions you
already built by hand.

[CAREERS.md](https://github.com/alexvervloet/ai-deep-dives/blob/main/CAREERS.md)
maps each dive to the industry tools that productionize it, so you can
*recognize* them in a job posting. Recognizing a tool and having used it are
different interview answers. This dive closes that gap, and does it the only
way this series knows how: **measured, against a baseline you understand,
with the tradeoffs shown honestly.**

> **New here? Read [WALKTHROUGH.md](WALKTHROUGH.md) first.** It is the guided
> tour of the whole journey: the setup that gates each chapter, and for every
> tool the fork in the road, the gotcha that will trip you, and the best and
> worst case for reaching for it. This README is the reference; the walkthrough
> is the map with the potholes marked.

## The method: port, measure, verdict

Every chapter follows the same shape:

1. **The primitive.** A short recap of what you hand-rolled in the earlier dive,
   and a link to it. That's the baseline: you know exactly what it does,
   because you wrote every line.
2. **The tool.** The professional replacement, introduced by what it claims to
   automate, not by its marketing page.
3. **The port.** Rebuild the same artifact with the tool. Minimal, runnable,
   side by side with the hand-rolled version.
4. **The measurement.** Run the **same eval** against both. Not vibes: the
   retrieval metrics, red-team attack success rates, and judge scores you built
   in the earlier dives are the measuring stick here.
5. **The verdict.** What the tool bought you (less code, maintained
   integrations, tracing for free), what it cost you (debugging opacity,
   version churn, an abstraction between you and the request), and when you'd
   still hand-roll. Written from the run you just did, not from the docs.

The point is never "the framework is better" or "frameworks are bloat." The
point is that after each chapter you can say, in an interview and in a design
review: *"I built the primitive, I've used the tool, and here is precisely
what the tool is doing for me."*

## The chapters

One representative tool per category; the survey breadth lives in CAREERS.md;
depth lives here. Order mirrors the original series path. The slate was
verified against mid-2026 usage (surveys, adoption data), not habit, e.g.
promptfoo lost its slot to DeepEval after OpenAI acquired it in March 2026.
That verification date is part of the repo's honesty: check the landscape
again before trusting the slate in 2027.

| # | Chapter | Replaces the hand-rolled... | From dive | Status |
|---|---------|---------------------------|-----------|--------|
| 1 | **[LiteLLM](ch01-litellm/)** | provider layer: one client, many providers, fallbacks, cost tracking | [OpenAI API](https://github.com/alexvervloet/openai-api-deep-dive) / [Claude API](https://github.com/alexvervloet/claude-api-deep-dive) | **done**, [verdict](ch01-litellm/VERDICT.md) |
| 2 | **[Instructor](ch02-instructor/)** | JSON-parse-and-retry loop for structured extraction | [Prompt Engineering](https://github.com/alexvervloet/prompt-engineering-deep-dive) | **done**, [verdict](ch02-instructor/VERDICT.md) |
| 3 | **[LlamaIndex](ch03-llamaindex/)** | chunk → embed → retrieve → cite pipeline | [RAG](https://github.com/alexvervloet/rag-deep-dive) | **done**, [verdict](ch03-llamaindex/VERDICT.md) |
| 4 | **[DeepEval](ch04-deepeval/)** | eval harness and regression gate | [Evals](https://github.com/alexvervloet/evals-deep-dive) | **done**, [verdict](ch04-deepeval/VERDICT.md) |
| 5 | **[LangGraph](ch05-langgraph/)** | agent loop, tool routing, state | [Agents](https://github.com/alexvervloet/agents-deep-dive) | **done**, [verdict](ch05-langgraph/VERDICT.md) |
| 6 | **[Llama Guard + Guardrails AI](ch06-guardrails/)** | input/output detectors and checks | [Prompt Injection & Guardrails](https://github.com/alexvervloet/prompt-injection-deep-dive) | **done**, [verdict](ch06-guardrails/VERDICT.md) |
| 7 | **[Langfuse](ch07-langfuse/)** | tracing, cost accounting, prompt versioning | [Production](https://github.com/alexvervloet/ai-in-production-deep-dive) + [Observability](https://github.com/alexvervloet/observability-deep-dive) | **done**, [verdict](ch07-langfuse/VERDICT.md) |

Chapters land incrementally; the status column is the source of truth. A
chapter isn't "done" until its verdict is backed by a real measured run; see
the series'
[authoring principles](https://github.com/alexvervloet/ai-deep-dives/blob/main/AUTHORING-LESSONS.md):
the output is the argument.

## Prerequisites

This is a **volume 2**. Each chapter assumes you've done the corresponding
from-scratch dive (or at least can read its final artifact comfortably); the
whole teaching device is the comparison against something you understand.
Start with the [series path](https://github.com/alexvervloet/ai-deep-dives) if
you haven't.

## A warning this repo wears on purpose

This repo will **rot faster than the others, by design**. Frameworks rename
modules, break APIs between minor versions, and fall out of fashion, and that
churn is itself one of the lessons, and it's the reason the rest of the series
teaches primitives first. Dependencies are pinned per chapter so the examples
keep running; when a pin drifts far behind the tool's current release, treat
the *concepts* in the verdict as current and the code as a snapshot. The
primitive underneath doesn't move.

---

*Part of the [AI Engineering deep-dive series](https://github.com/alexvervloet/ai-deep-dives)
sequenced, self-contained, from-scratch lessons. This dive is the bridge
from "I built it by hand" to "I've run the tool professionals use, and I know
what it's doing."*
