"""
Chapter 5 port — the same agent through LangGraph's prebuilt ReAct graph.
=========================================================================

`create_react_agent` is the framework's version of hand_rolled.py's while
loop: a two-node graph (model -> tools -> model ...) you get in one call.
The same three tool functions ride in as `@tool`-decorated wrappers.

The interesting difference is the approval gate. The hand-rolled loop asks
a callback mid-iteration. Here, save_note calls `interrupt()`: the graph
STOPS, checkpoints its state (MemorySaver), and returns control with an
`__interrupt__` marker; the caller resumes it later — seconds or days later
— with `Command(resume=...)`. That's not a callback, it's durable
human-in-the-loop infrastructure: survives restarts with a real
checkpointer, but requires a checkpointer + thread_id even for this demo.
One feature, two costs — compare.py measures whether it also changes the
agent's behavior on the same tasks.

Run the task set through it:

    secrun python ch05-langgraph/with_tool.py
"""

import os
import sys
import time

from dotenv import load_dotenv
from langchain_core.messages import AIMessage, ToolMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent
from langgraph.types import Command, interrupt

import tasks
from hand_rolled import MODEL, RunStats
from tasks import SYSTEM, TASKS


@tool
def calculator(expression: str) -> str:
    """Evaluate an arithmetic expression like '12 * (3 + 4)'. Use this for any math instead of computing it yourself."""
    return tasks.calculator(expression)


@tool
def search_notes(query: str) -> str:
    """Search the Nimbus Notes help knowledge base (plans, billing, security, etc.)."""
    return tasks.search_notes(query)


@tool
def save_note(title: str, body: str) -> str:
    """Save a note to the user's workspace. Writes a file to disk."""
    approved = interrupt({"tool": "save_note", "title": title, "body": body})
    if not approved:
        return "Error: the user denied permission to run this tool."
    return tasks.save_note(title, body)


def build_agent():
    return create_react_agent(
        model=ChatOpenAI(model=MODEL, temperature=0),
        tools=[calculator, search_notes, save_note],
        prompt=SYSTEM,
        checkpointer=MemorySaver(),
    )


def run_task(agent, task: dict, thread_id: str) -> tuple[RunStats, bool, float]:
    config = {"configurable": {"thread_id": thread_id}}
    started = time.perf_counter()
    result = agent.invoke({"messages": [("user", task["prompt"])]}, config)
    while "__interrupt__" in result:
        # The graph is paused inside save_note. Same policy as the baseline's
        # deny-callback: approve only if the task doesn't say to deny.
        result = agent.invoke(Command(resume=not task.get("deny_approval")), config)
    seconds = time.perf_counter() - started

    stats = RunStats(answer=result["messages"][-1].content)
    for message in result["messages"]:
        if isinstance(message, AIMessage):
            stats.llm_calls += 1
        elif isinstance(message, ToolMessage):
            stats.tool_calls += 1
    return stats, bool(task["check"](stats.answer)), seconds


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    agent = build_agent()
    for n, task in enumerate(TASKS):
        stats, ok, seconds = run_task(agent, task, thread_id=f"demo-{n}")
        print(f"[{'ok' if ok else 'FAIL'}] {task['name']:18} "
              f"llm={stats.llm_calls} tools={stats.tool_calls} {seconds:.1f}s")
        print(f"      {str(stats.answer)[:90]}")
