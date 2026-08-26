# LESSONS

Engineering lessons from porting hand-rolled primitives from the deep-dive
series: the provider layer, the extraction loop, the RAG pipeline, the eval
harness, the agent loop, the guardrails, onto the professional tools that
productionize them (LiteLLM, Instructor, LlamaIndex, DeepEval, LangGraph,
Llama Guard, Guardrails AI), and measuring the two against each other on the
same eval every time.

Almost all of these are one discipline seen from different angles: **don't
mistake what the tool does for what you'd have chosen, don't mistake a matched
score for a matched system, and don't let a tool's absence or a tool's name
stand in for a measurement.** Each is tied to the concrete chapter and number
that taught it. Kept as a running log; it grows as the chapters land.

---

## 1. Hold the measuring apparatus physically constant: including across the tool boundary

Every chapter's comparison is only as trustworthy as what it refused to let
move. Ch04 generated the eight answers **once** and committed them to
`answers.json`, so the hand-rolled judge and DeepEval's `FaithfulnessMetric`
scored byte-identical text with the **same** `gpt-4o-mini` judge; the only
variable left was the scorer. Ch02 did the same with its extraction fixtures;
ch06 fired the identical 18-case red-team set at all five guards; ch03 ran
both RAG pipelines over the same corpus through one eval function. The move
that would have poisoned every result was the easy one: let the tool bring its
own model, its own data, or its own grader, and then read the delta as if it
were about the tool.

Takeaway: a from-scratch-vs-tool comparison is a science experiment, and the
tool is the only thing allowed to be the independent variable. Pin the inputs
(commit them), pin the judge, pin the corpus; then a difference in the output
can only be the thing you meant to test.

## 2. A matched score is the start of the analysis, not the end

Two chapters produced a dead tie, and in both the tie described neither system.
Ch05: the hand-written agent loop and LangGraph's prebuilt agent scored
**identically**: 10/10 tasks, 2.0 LLM calls, 1.0 tool calls, ~1.5s per task,
run for run. Ch03: hand-rolled RAG, LlamaIndex-as-shipped, and LlamaIndex-
matched all hit **100% hit-rate and answer-correctness** on the same twelve
questions. Read as headlines, "the framework matches the primitive." But the
tie only means the eval didn't exercise where they differ. In ch05 the real
difference was architectural (a callback vs a durable checkpoint/resume
interrupt); in ch03 it was a dropped product property (lesson 4) and a price
tag on the defaults (lesson 5). The competence lived in the model and the
prompt, which were held constant, so the harness *couldn't* move the score.

Takeaway: when a tool ties your hand-rolled version, that's a statement about
your eval's coverage, not a verdict that the two are interchangeable. Go find
the axis the eval didn't test (durability, cost, a contract, an operational
property) because that's where the real decision lives.

## 3. Importing a tool means importing its definitions: the name is not the contract

Ch04's sharpest finding: DeepEval's `FaithfulnessMetric` passed a pure
hallucination ("a password-reset link is typically valid for 24 hours," over
a context that says nothing about expiry) with a score of **1.00 on every
run**, because it operationalizes faithfulness as *absence of contradiction*,
while the evals dive's rubric means *every claim must be supported*. Same word,
different metric. Ch06 generalized it: "guardrail" turned out to name at least
three unrelated products: a safety classifier (Llama Guard), an intent
detector (the LLM guard), and a validation framework (Guardrails AI), and
Llama Guard scored **0/3 on injection** because its taxonomy has no cell for
"overrode the system prompt." Adopting either tool silently adopts its
definition of the thing you thought you were measuring.

Takeaway: before you gate a release or a request on an imported metric or
guard, read what it actually computes and diff it against your own rubric. The
name matching your intent is not evidence the behavior does.

## 4. A tool can drop a product property while every metric stays green

Ch03's port matched the baseline on every retrieval and answer metric, and
**silently stopped citing its sources**: 12/12 hand-rolled answers carried a
citation, 0/12 from either LlamaIndex engine. The default prompt never asks for
one, and the framework's context assembly isn't numbered, so the baseline's
`[n]` contract wasn't even expressible in a `text_qa_template`. The only reason
the regression was visible is that the eval captured the **answers**, not just
the scores, a change I made mid-chapter specifically so a property could be
checked.

Takeaway: metrics measure what you thought to measure; a tool swap can
break a contract no metric is watching. Capture the raw outputs and assert on
product properties (citations, format, refusal behavior), not only on the
aggregate numbers; the green dashboard is exactly where the regression hides.

## 5. A tool's defaults have a vintage: someone chose them on a date you don't know

LlamaIndex 0.14.23, installed fresh in mid-2026, defaulted to
**text-embedding-ada-002** (a 2022 embedder at 5× the price of the current
small model), **gpt-3.5-turbo**, **1024-token chunks** (one chunk per whole
doc, on this corpus), and **k=2**. Nothing was broken; every knob was settable.
But `VectorStoreIndex.from_documents(docs)` with nothing configured is a 2023
stack at above-2026 prices, and the from-scratch version had made each of
those choices explicitly, because the RAG dive *measured* them. The framework's
choices were frozen whenever that release shipped.

Takeaway: a default is a decision made by someone who never saw your problem,
at a date you have to go look up. Audit the defaults of anything you adopt 
especially the ones that cost money or silently change results, and don't
assume "the framework picked it" means "it's current or right for you."

## 6. Unavailable is not a measurement: fail loud, never let absence read as a null result

The most dangerous bug this whole repo nearly shipped was in its own
comparison harness. Ch06's first `compare.py` caught exceptions and recorded
`False`, so when Llama Guard wasn't installed it would have printed a clean,
authoritative row: **"llama_guard: 0/6 direct, 0/3 indirect, 0/4 harmful"** 
a fabricated finding indistinguishable from a real one, and one that happened
to *look like* the prediction we were hoping to confirm. The fix probes each
guard first and drops the unreachable ones with a banner, refusing to score an
absent tool as a miss. The same discipline is baked into ch07's Langfuse port,
which calls `auth_check()` and exits loudly rather than pretend traces landed.

Takeaway: a tool that can't run must produce a loud gap, never a quiet zero.
"Didn't detect anything" and "wasn't there to detect" are opposite facts that
render identically if you let an exception become a `False`, and the fabricated
version is most tempting exactly when it agrees with what you expected.

## 7. Measure the prediction even when you're sure: the confirmation and the surprise both live in the run

Ch06 went in predicting Llama Guard would win harmful content and miss
injection. It did: 4/4 harmful with correct S1/S2/S11 codes, 0/3 injection.
But running it anyway is what turned up the thing we *hadn't* predicted: the
managed safety model covered **no category the dive's own hand-rolled
`llm_guard` didn't already cover** (6/6 direct, 3/3 indirect, and the only
guard to block the phishing line), and Llama Guard mislabeled the injections it
did catch as "S1, violent crimes," firing for a reason that doesn't match what
happened. None of that is visible from the prediction; all of it is in the
data.

Takeaway: a prediction is a hypothesis, and shipping it as a conclusion skips
the experiment. Run it even when you're confident; the confirmation counts only
because it was measured, and the findings you didn't predict are usually the
ones worth the chapter.

## 8. Name exactly what the tool adds, and subtract what you already had

The honest diff is almost always narrower than the pitch. LiteLLM's cost
tracking (ch01) **agreed with the hand-rolled pricing table to the digit** 
so its real contribution isn't "cost visibility," it's *maintaining the pricing
map for ~100 providers so you don't*. Guardrails AI (ch06) detected
**identically to the bare regex** it wrapped (2/6, 0/3, 0/4), so the framework
buys `on_fail` policies, reask flows, and structured failures, **not** a smarter
filter. Instructor (ch02) turned out to solve a reliability problem that had
largely closed: 60/60 extractions succeeded across every approach, so its
edge is portability and retained retries, not "the model returns broken JSON
and you need machinery."

Takeaway: write down what the tool adds as a *difference* from your baseline,
and subtract everything the baseline already did. "It tracks cost" and "it
validates output" were both false as differences; the true differences were
narrower and more specific, and a comparison's credibility lives in that
precision.

## 9. The abstraction tax is a bug in a layer you didn't write

LiteLLM (ch01) routed the same local model two ways depending on a prefix:
`ollama_chat/qwen3:8b` completed a tool call; `ollama/qwen3:8b` returned an
**empty string** for the final turn: no error, no warning, in a translation
layer we didn't author and couldn't see into from our own code. The hand-rolled
version, talking to Ollama's OpenAI-compatible endpoint directly, had no such
seam. Convenience and opacity were the same feature: the router that spares you
the per-provider glue also owns a failure mode you can only debug by reading its
source.

Takeaway: every abstraction you adopt is a layer whose bugs become yours to hit
but not to see. Budget for the ones that fail *silently* (a wrong prefix, a
swallowed error, an empty result) because those cost more to diagnose than the
glue code the abstraction saved you, and they surface only against the real
thing.

## 10. Framework churn is a build-time cost, and it arrives on schedule

The version tax landed in nearly every chapter, while building, not later.
LangGraph's canonical `create_react_agent` **deprecated itself mid-chapter**,
pointing at a package this venv didn't even have installed. DeepEval demanded
`click<8.4` while huggingface-hub demanded `≥8.4.2`: an unsatisfiable pair
resolved only by pinning huggingface-hub back a minor version. LiteLLM imported
`fastapi` and `orjson` as undeclared dependencies the moment `tools=` was
passed. Guardrails AI's much-cited "50+ validator Hub" returned **401** without
an account. Every one of these became a real line (a pin, a workaround, a
custom validator) in `requirements.txt` or the code.

Takeaway: a fast-moving ecosystem bills you during the build, not just at
maintenance time. The canonical way to do something can be deprecated the week
you adopt it, capabilities migrate between packages, and "just install it" can
mean an account or an unsatisfiable resolver. Pin and record the exact versions
you measured against; they encode findings, and they *will* move.

## 11. Sometimes the tool just wins, and the discipline is to bound the win, not to hedge it

Most of these lessons are cautions against over-crediting a tool, and it would
be dishonest to let that curdle into "the hand-rolled version always suffices."
Ch07 didn't tie and didn't debunk: an observability *platform* does things 121
lines of stdlib genuinely can't: persistence past process exit, a query API, a
UI, sharing with a teammate who wasn't at your terminal. The move there wasn't
to manufacture a caveat; it was to state the win **precisely** and price it. So
the additions got named exactly (and *subtracted* what the hand-rolled tracer
already did, including cost, which it also computes: Langfuse's contribution to
pricing is that the *server* maintains the model-price map, confirmed by it
matching the hand total to the digit from tokens alone), and the cost got named
too: six always-on containers and a schema you don't own. A real win, bounded.

Takeaway: skepticism is a method, not a verdict. When the measurement says the
tool wins, say so, then do the same work you'd do to debunk it: name the exact
capabilities it adds, subtract the ones you already had, and state the price.
"It's better" is as lazy as "it's bloat"; the honest output is *what*, by *how
much*, at *what cost*.

---

*These came out of building `professional-tools-deep-dive`, the deep-dive
series' "volume 2," where each chapter rebuilds a from-scratch primitive with
the tool professionals reach for and scores both on the same eval. They
generalize to any "should we adopt this framework?" decision: the answer is an
experiment, and the experiment is only honest if you hold everything but the
tool still, refuse to let the tool's absence or its vocabulary stand in for a
result, and name what it adds down to the digit.*
