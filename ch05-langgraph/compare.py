"""
Chapter 5 measurement: same tasks, same tools, loop vs graph.

Runs the five-task eval REPS times through both implementations and prints
success rate, LLM calls, tool calls, and wall time per task. Both use
gpt-5.4-nano at temperature 0 with identical tool functions, so differences
isolate the harness: the 60-line while loop vs the prebuilt ReAct graph
with checkpointing and interrupts.

    secrun python ch05-langgraph/compare.py
"""

import os
import sys
import warnings

from dotenv import load_dotenv
from openai import OpenAI

warnings.filterwarnings("ignore")  # the create_react_agent deprecation; see VERDICT

import hand_rolled
import with_tool
from tasks import TASKS

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")

REPS = 2
client = OpenAI()
agent = with_tool.build_agent()

IMPLS = {
    "hand-rolled": lambda task, rep: hand_rolled.run_task(client, task),
    "langgraph": lambda task, rep: with_tool.run_task(agent, task, thread_id=f"cmp-{task['name']}-{rep}"),
}

print(f"  {'impl':12} {'task':18} {'ok':>5} {'llm':>4} {'tools':>6} {'sec':>6}")
totals: dict[str, dict[str, float]] = {}
for name, runner in IMPLS.items():
    total = totals[name] = {"ok": 0, "llm": 0, "tools": 0, "sec": 0.0, "n": 0}
    for task in TASKS:
        for rep in range(REPS):
            stats, ok, seconds = runner(task, rep)
            total["ok"] += ok
            total["llm"] += stats.llm_calls
            total["tools"] += stats.tool_calls
            total["sec"] += seconds
            total["n"] += 1
            print(f"  {name:12} {task['name']:18} {'ok' if ok else 'FAIL':>5} "
                  f"{stats.llm_calls:>4} {stats.tool_calls:>6} {seconds:>5.1f}s")

print(f"\n  {'impl':12} {'success':>9} {'llm/task':>9} {'tools/task':>11} {'sec/task':>9}")
for name, total in totals.items():
    n = total["n"]
    print(f"  {name:12} {int(total['ok'])}/{n:<7} {total['llm'] / n:>8.1f} "
          f"{total['tools'] / n:>10.1f} {total['sec'] / n:>8.1f}s")
