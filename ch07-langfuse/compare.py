"""
Chapter 7 measurement: the record vs the platform.

Both implementations trace the same workload. This script makes the honest
difference concrete by asking ONE operational question ("what did we spend,
how slow was p95, how many got blocked?") of each side, and showing what it
took to answer:

  - hand-rolled: the traces are JSON lines. To answer the question you parse
    them yourself (here, in Python, the grep-equivalent). You also computed
    the per-request cost yourself, inline, because nothing else would.
  - Langfuse: the traces are on a server that already computed each request's
    cost from token usage and its own pricing map (we sent it token counts,
    never dollars), persisted them, and exposes them via a query API. You ask;
    it answers over data that outlives the process.

The point isn't who can run sum(); both can. It's WHERE the data lives after
the process exits, WHO priced it, and whether a teammate who wasn't at your
terminal can ever see it.

    (cd ch07-langfuse && docker compose up -d)      # stack must be up
    secrun python ch07-langfuse/compare.py
"""

import io
import os
import statistics
import sys
from contextlib import redirect_stderr
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

import app
import hand_rolled
import with_tool

load_dotenv(Path(__file__).parent / ".env")
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")

client = OpenAI()

# --- hand-rolled: run the workload, capture the JSON trace records ----------
# The records are what would go to stderr; we grab them to aggregate in Python.
print("── hand-rolled: run workload, then aggregate the JSON records yourself")
hand_summaries = []
buf = io.StringIO()
with redirect_stderr(buf):
    for question in app.WORKLOAD:
        hand_summaries.append(hand_rolled.answer(client, question))

hand_cost = sum(s.get("cost_usd", 0.0) for s in hand_summaries)
hand_latencies = [s["duration_ms"] for s in hand_summaries if not s.get("blocked")]
hand_blocked = sum(1 for s in hand_summaries if s.get("blocked"))
hand_p95 = max(hand_latencies) if hand_latencies else 0.0  # n=3, "p95" ~= max
print(f"   total spend  ${hand_cost:.6f}   (you computed each request's cost inline)")
print(f"   p95 latency  {hand_p95:.0f}ms   (you parsed it out of the dicts)")
print(f"   blocked      {hand_blocked}       (you counted the flag yourself)")
print("   ...and once this process exits, these records are gone unless you shipped them somewhere.")

# --- Langfuse: run the same workload, then ASK the server -------------------
# Scope the query to THIS run with from_timestamp: otherwise trace.list pulls
# every historical support.answer trace and the totals double-count vs the
# hand-rolled four (a bug we hit: 8 traces, ~2x the spend).
import time
from datetime import datetime, timezone

print("\n── Langfuse: run workload, then query the platform")
lf = with_tool.get_langfuse()
run_start = datetime.now(timezone.utc)
for question in app.WORKLOAD:
    with_tool.answer(lf, client, question)
lf.flush()
time.sleep(3)  # let async ingestion land

traces = lf.api.trace.list(limit=50, name="support.answer", from_timestamp=run_start).data
lf_cost = sum((t.total_cost or 0.0) for t in traces)
lf_latencies = [t.latency for t in traces if t.latency and t.latency > 0.01]
lf_p95 = max(lf_latencies) * 1000 if lf_latencies else 0.0
print(f"   traces on server   {len(traces)}   (persisted; survive this process, visible to a teammate)")
print(f"   total spend        ${lf_cost:.6f}   (THE SERVER priced it: we sent tokens, never dollars)")
print(f"   p95 latency        {lf_p95:.0f}ms   (server-computed from the spans)")
print(f"   query story        one API call / a UI at {os.environ['LANGFUSE_HOST']}, not a grep")

# --- the receipts -----------------------------------------------------------
hand_loc = len(Path(hand_rolled.__file__).read_text().splitlines())
print("\n── what each side costs to own")
print(f"   hand-rolled: ~{hand_loc} lines of trace/span/log code you maintain, 0 extra services,")
print(f"                nothing leaves the box, no UI, no retention.")
print(f"   langfuse:    ~0 lines of tracing infra, but SIX always-on containers")
print(f"                (web, worker, postgres, clickhouse, redis, minio) and your")
print(f"                traces now live in someone else's schema.")
