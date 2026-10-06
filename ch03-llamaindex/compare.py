"""
Chapter 3 measurement: three pipelines, one eval.

Scores the hand-rolled baseline, LlamaIndex-as-it-ships, and
LlamaIndex-matched-to-the-baseline on the same 12 labelled questions with
the rag dive's metrics (hit rate @ k, MRR, answer-fact). One eval function,
three pipelines; the measuring stick never moves.

Note the defaults engine is scored *at its own defaults* (k=2, ada-002,
gpt-3.5-turbo, 1024-token chunks): that's the pipeline you actually shipped
if you copied the quickstart and moved on.

Run it:

    secrun python ch03-llamaindex/compare.py
"""

import logging
import os
import re
import sys
import time

from dotenv import load_dotenv
import openai
from openai import OpenAI

import hand_rolled
import with_tool
from evalset import EVALSET, run_eval

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Run via secrun so OPENAI_API_KEY is set (see ../docs/SECRETS.md).")
logging.disable(logging.INFO)  # silence llama-index's per-request HTTP logs

print("LlamaIndex defaults on this version:")
for key, value in with_tool.describe_defaults().items():
    print(f"  {key}: {value}")

client = OpenAI()
store = hand_rolled.build_store(client)

pipelines = {
    "hand-rolled": (
        lambda q: hand_rolled.retrieve_sources(client, store, q),
        lambda q: hand_rolled.answer(client, store, q),
        len(store.records),
    ),
    "LI defaults": with_tool.build_default(),
    "LI matched": with_tool.build_matched(),
}

print(f"\nScoring {len(EVALSET)} questions per pipeline...\n")
print(f"  {'pipeline':12} {'chunks':>6} {'hit@k':>7} {'MRR':>7} {'answers':>8} "
      f"{'cited':>6} {'s/q':>5}")
results = {}
retired = {}  # pipeline -> the error, when its model no longer exists
for name, (retrieve_fn, answer_fn, n_chunks) in pipelines.items():
    started = time.perf_counter()
    try:
        result = run_eval(retrieve_fn, answer_fn)
    except openai.NotFoundError as e:
        # LlamaIndex's default LLM is gpt-3.5-turbo, even in the newest
        # llama-index-llms-openai, and OpenAI shut it down on 2026-10-23. From
        # then on the defaults pipeline can't answer anything. That's not a bug
        # in this script; it's what copying the quickstart gets you.
        retired[name] = e
        print(f"  {name:12} FAILED: its model is gone ({str(e)[:70]})")
        continue
    seconds_per_q = (time.perf_counter() - started) / len(EVALSET)
    # Citation discipline: does the answer point back at a source at all,
    # via a [n] marker (the baseline's contract) or a corpus filename?
    cited = sum(
        1 for text in result.answers
        if re.search(r"\[\d+\]", text) or ".md" in text
    )
    results[name] = result
    print(f"  {name:12} {n_chunks:>6} {result.hit_rate:>6.0%} {result.mrr:>7.3f} "
          f"{result.answer_rate:>7.0%} {cited:>4}/{len(result.answers):<2} {seconds_per_q:>4.1f}s")

print("\n── misses by pipeline")
for name, result in results.items():
    print(f"  {name}: {len(result.misses)}")
    for miss in result.misses:
        print(f"    - {miss}")

# The grounding probe: a question the corpus does NOT answer. The baseline's
# system prompt demands "say you don't know"; what does each pipeline do?
UNANSWERABLE = "Does Nimbus Notes have a Linux desktop app?"
print(f"\n── unanswerable probe: {UNANSWERABLE!r} (corpus is silent on this)")
for name, (_retrieve_fn, answer_fn, _n) in pipelines.items():
    if name in retired:
        print(f"  {name:12} -> (skipped: its model is gone)")
        continue
    print(f"  {name:12} -> {answer_fn(UNANSWERABLE).strip()[:110]}")

if retired:
    print(
        "\n── a default retired under you\n"
        "  Nothing in this repo changed. The pipeline that touched no knobs inherited\n"
        "  LlamaIndex's default model, and the provider switched that model off. The\n"
        "  pipelines that named their model kept working."
    )
