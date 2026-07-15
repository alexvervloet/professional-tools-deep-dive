"""
Chapter 4 measurement — one judge call vs a judging pipeline.
=============================================================

Scores the same 8 committed answers with both harnesses, same judge model:

  - hand-rolled: ONE call per answer, "rate 1-5, reply with the integer."
  - DeepEval FaithfulnessMetric: a multi-step pipeline per answer (extract
    truths from the context, extract claims from the answer, verdict each
    claim, optionally write a reason) — the framework's bet is that
    decomposition beats a one-shot rating.

Reported per harness: per-case scores and pass/fail agreement at the same
0.75 threshold, wall time, and dollars (hand-rolled priced from captured
token usage at gpt-4o-mini list price; DeepEval from its own
metric.evaluation_cost).

    secrun python ch04-deepeval/compare.py
"""

import os
import sys
import time

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")  # before deepeval imports

from dotenv import load_dotenv
from openai import OpenAI

from cases import CASES, JUDGE_MODEL
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase
from hand_rolled import score_all

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")

THRESHOLD = 0.75
GPT_4O_MINI_PRICE = (0.15, 0.60)  # $ per 1M tokens in/out, list price 2026-07

contexts = {case["name"]: case["context"] for case in CASES}

print("── hand-rolled judge (1 call per answer)")
client = OpenAI()
started = time.perf_counter()
rows = score_all(client)
hand_seconds = time.perf_counter() - started
hand_cost = sum(
    row["tokens_in"] / 1e6 * GPT_4O_MINI_PRICE[0] + row["tokens_out"] / 1e6 * GPT_4O_MINI_PRICE[1]
    for row in rows
)

print("── DeepEval FaithfulnessMetric (multi-step pipeline per answer)")
started = time.perf_counter()
deepeval_cost = 0.0
for row in rows:
    metric = FaithfulnessMetric(
        threshold=THRESHOLD, model=JUDGE_MODEL, include_reason=True, async_mode=False
    )
    metric.measure(
        LLMTestCase(
            input=row["case"],
            actual_output=row["answer"],
            retrieval_context=[contexts[row["case"]]],
        )
    )
    row["de_score"] = metric.score
    row["de_reason"] = metric.reason or ""
    deepeval_cost += metric.evaluation_cost or 0.0
deepeval_seconds = time.perf_counter() - started

print(f"\n  {'case':38} {'prompt':8} {'hand':>5} {'deepeval':>9} {'agree':>6}")
disagreements = []
for row in rows:
    hand_pass = row["score"] >= THRESHOLD
    de_pass = row["de_score"] >= THRESHOLD
    agree = "yes" if hand_pass == de_pass else "NO"
    if hand_pass != de_pass:
        disagreements.append(row)
    print(f"  {row['case']:38} {row['prompt']:8} {row['raw']}/5 {row['de_score']:>9.2f} {agree:>6}")

print(f"\n  {'':38} {'':8} {'wall':>5} {'cost':>10}")
print(f"  {'hand-rolled totals':38} {'':8} {hand_seconds:>4.1f}s {hand_cost:>9.6f}$")
print(f"  {'deepeval totals':38} {'':8} {deepeval_seconds:>4.1f}s {deepeval_cost:>9.6f}$")

if disagreements:
    print("\n── disagreements, with DeepEval's stated reason")
    for row in disagreements:
        print(f"  [{row['case']} / {row['prompt']}] hand={row['raw']}/5 de={row['de_score']:.2f}")
        print(f"    answer: {row['answer'][:90]}")
        print(f"    reason: {row['de_reason'][:200]}")
