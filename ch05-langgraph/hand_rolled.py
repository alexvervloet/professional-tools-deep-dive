"""
Chapter 5 baseline — the agents dive's loop, condensed to one file.
===================================================================

The while-loop that IS an agent (agents-deep-dive agent/loop.py), with its
three safety pieces intact: max_steps, errors-fed-back-to-the-model, and
the approval gate on dangerous tools. OpenAI-only here so the loop and the
provider glue fit on one screen.

What to notice for the comparison: the approval gate is a synchronous
callback INSIDE the loop — deny it and the denial becomes a tool result the
model reacts to in the same run. LangGraph's equivalent (with_tool.py) is
an interrupt: the graph *stops*, persists state to a checkpointer, and a
second invocation resumes it. Same product feature, two very different
shapes — one is a function call, the other is infrastructure.

Run the task set through it:

    secrun python ch05-langgraph/hand_rolled.py
"""

import json
import os
import sys
import time
from dataclasses import dataclass, field
from typing import Callable

from dotenv import load_dotenv
from openai import OpenAI

from tasks import SYSTEM, TASKS, calculator, save_note, search_notes

MODEL = "gpt-4o-mini"
MAX_STEPS = 6

TOOL_DEFS = [
    {"type": "function", "function": {
        "name": "calculator",
        "description": "Evaluate an arithmetic expression like '12 * (3 + 4)'. Use this for any math instead of computing it yourself.",
        "parameters": {"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]},
    }},
    {"type": "function", "function": {
        "name": "search_notes",
        "description": "Search the Nimbus Notes help knowledge base (plans, billing, security, etc.).",
        "parameters": {"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]},
    }},
    {"type": "function", "function": {
        "name": "save_note",
        "description": "Save a note to the user's workspace. Writes a file to disk.",
        "parameters": {"type": "object", "properties": {"title": {"type": "string"}, "body": {"type": "string"}}, "required": ["title", "body"]},
    }},
]
FUNCS: dict[str, Callable] = {"calculator": calculator, "search_notes": search_notes, "save_note": save_note}
DANGEROUS = {"save_note"}


@dataclass
class RunStats:
    answer: str = ""
    llm_calls: int = 0
    tool_calls: int = 0
    stopped_early: bool = False
    trace: list[str] = field(default_factory=list)


def run_agent(client: OpenAI, user_input: str, approve: Callable[[str, dict], bool] | None = None) -> RunStats:
    """The whole idea: ask; if tool calls, run them and loop; else done."""
    stats = RunStats()
    messages = [
        {"role": "system", "content": SYSTEM},
        {"role": "user", "content": user_input},
    ]
    for _ in range(MAX_STEPS):
        response = client.chat.completions.create(
            model=MODEL, temperature=0, messages=messages, tools=TOOL_DEFS
        )
        stats.llm_calls += 1
        message = response.choices[0].message
        if not message.tool_calls:
            stats.answer = message.content or ""
            return stats
        messages.append(message)
        for call in message.tool_calls:
            arguments = json.loads(call.function.arguments)
            stats.tool_calls += 1
            if call.function.name in DANGEROUS and approve and not approve(call.function.name, arguments):
                result = "Error: the user denied permission to run this tool."
            else:
                try:
                    result = str(FUNCS[call.function.name](**arguments))
                except Exception as e:  # feed any failure back to the model
                    result = f"Error running {call.function.name}: {e}"
            stats.trace.append(f"{call.function.name}({arguments}) -> {result[:60]}")
            messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    stats.answer = "(stopped: reached the step limit without finishing)"
    stats.stopped_early = True
    return stats


def run_task(client: OpenAI, task: dict) -> tuple[RunStats, bool, float]:
    approve = (lambda _name, _args: False) if task.get("deny_approval") else None
    started = time.perf_counter()
    stats = run_agent(client, task["prompt"], approve=approve)
    seconds = time.perf_counter() - started
    return stats, bool(task["check"](stats.answer)), seconds


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    client = OpenAI()
    for task in TASKS:
        stats, ok, seconds = run_task(client, task)
        print(f"[{'ok' if ok else 'FAIL'}] {task['name']:18} "
              f"llm={stats.llm_calls} tools={stats.tool_calls} {seconds:.1f}s")
        print(f"      {stats.answer[:90]}")
