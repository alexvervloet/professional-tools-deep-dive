# Chapter 4 verdict: DeepEval vs the hand-rolled eval harness

Written from real runs on 2026-07-14 (deepeval 4.1.0, judge pinned to
gpt-4o-mini for BOTH harnesses; 8 committed answers in answers.json so every
pass scores identical texts). Reproduce with
`secrun python ch04-deepeval/compare.py` and
`secrun .venv/bin/python -m pytest ch04-deepeval/test_gate.py -q`.

## The stable finding: same metric name, different metric

The evals dive's faithfulness rubric says *every claim must be supported by
the context; true-but-unsupported still fails*. DeepEval's
`FaithfulnessMetric` operationalizes faithfulness as **absence of
contradiction**: the loose prompt's pure invention ("A password-reset link
is typically valid for 24 hours," over a context that says nothing about
expiry: scored **1.00 in every run**, reason: *"no contradictions
present."* The hand-rolled judge scored it 1/5 in every run. Neither
implementation is buggy; they measure different things under the same word.
**Importing a metric means importing its definition**, and the definition,
not the name, is what your CI gate enforces. (Ragas, the RAG-metrics
standard this chapter name-checks, has its own faithfulness definition 
closer to the dive's claim-support reading; the lesson applies to it
equally: read the definition before you gate on it.)

## The wobble finding: the pipeline gate flakes on fixed inputs

Four scoring passes over the *same committed answers*, three different
outcomes for the grounded refusals ("The context doesn't say."):

| pass | grounded refusals (3 cases) |
|------|------------------------------|
| compare.py run 1 | two 1.00, one **0.00** |
| compare.py run 2 | all 1.00 |
| pytest gate run 1 | **3 of 4 tests FAILED** |
| pytest gate run 2 | all passed |

A refusal over a silent context is apparently an edge its multi-step
pipeline (extract truths → extract claims → verdict each claim) resolves
differently run to run, presumably whether "the context doesn't say"
yields zero claims or one unverifiable one. Whatever the mechanism, the
measured behavior is what CI would see: **a gate that flips on identical
inputs.** The one-call hand-rolled judge returned the same integers on
every pass. More steps, more places to wobble; the evals dive's
nondeterminism lesson (its example 09), now starring the tool that was
supposed to solve it. Gate design note: the hand-rolled gate thresholds the
*mean*, which absorbs single-case wobble; DeepEval's natural pytest shape
asserts *per case*, which amplifies it.

## Costs, measured

Same 8 answers, same judge model: hand-rolled ~6s and $0.0002 per pass;
DeepEval ~39s and $0.0024: **~7× the wall clock and ~12× the dollars** for
the decomposed pipeline (the pytest gate spent 105s judging 4 answers).
That buys real things: written reasons per verdict (genuinely useful when a
score surprises you), pytest/CI integration with no runner code of your
own, 50+ maintained metrics, dataset tooling. Also noteworthy: telemetry is
on by default (`DEEPEVAL_TELEMETRY_OPT_OUT=1` in every script here).

## Where that leaves it

The two-tool pattern the 2026 surveys describe (an open-source framework
for CI gates plus a platform for production traces) is right about the
*slot* DeepEval fills; this chapter is about what to check before trusting
it in that slot: whether its metric definition matches your rubric (here it
didn't), and whether the gate is stable enough to page you honestly (here,
on refusal-heavy cases, it wasn't). The hand-rolled judge won this
comparison on definition-fit, stability, latency, and cost; DeepEval wins
the moment you need many metrics, many cases, reports someone else
maintains, and reasons attached to scores. Both verdicts are only visible
because the answers were pinned and the judge held constant, which is the
evals dive's whole curriculum, applied to the eval tool itself.

## The interview sentence

"I gated the same fixed answers with my own faithfulness judge and
DeepEval's FaithfulnessMetric, same judge model: the imported metric passed
a pure hallucination every run because its definition is
absence-of-contradiction, not claim-support, and its per-case pytest gate
flipped verdicts across reruns on identical inputs, so before I adopt an
eval framework I diff its metric definitions against my rubric and rerun
its gate for stability, because a flaky or mis-defined gate is worse than
none."
