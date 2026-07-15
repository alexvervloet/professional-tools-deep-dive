"""
Chapter 5 shared pieces — the tools, the tasks, and the success checks.
=======================================================================

The three tools are the agents dive's toolbox (agent/tools.py), copied
function-for-function: a safe calculator, a keyword search over the Nimbus
Notes facts, and save_note — the side-effecting one that must be gated
behind human approval. Both implementations expose the SAME Python
functions to their respective loops; only the wrapping differs.

The task set is this chapter's eval (the agents dive demonstrates its loop
but doesn't ship a labelled task set — same mechanics as the evals dive's
trajectory example). Each task has a programmatic success check on the
final answer or on observable behavior, so no LLM judge is needed:

  1. multi-step math      — must end with the right number
  2. knowledge lookup     — must surface the fact from the KB
  3. compose two tools    — search a price, then compute with it
  4. denied save          — human DENIES approval: the note must NOT exist
                            and the agent must report the denial
  5. no-tool question     — general knowledge; also measures whether the
                            loop wastes tool calls it doesn't need

Metrics per implementation (compare.py): success rate, LLM calls, tool
calls, wall time. temperature=0 everywhere.
"""

import ast
import operator
import re
from pathlib import Path

WORKSPACE = Path(__file__).parent / "workspace"

SYSTEM = (
    "You are a helpful assistant for the Nimbus Notes product. Use the tools "
    "when they help; answer directly when they don't. Be concise."
)

# --- the agents dive's three tool functions, verbatim in behavior ----------

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.Pow: operator.pow, ast.Mod: operator.mod,
    ast.USub: operator.neg, ast.UAdd: operator.pos,
}


def _safe_eval(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_safe_eval(node.operand))
    raise ValueError("unsupported expression")


def calculator(expression: str) -> str:
    """Evaluate a basic arithmetic expression (AST-walked, not eval)."""
    return str(_safe_eval(ast.parse(expression, mode="eval").body))


_KNOWLEDGE_BASE = {
    "plans": "Nimbus Notes has three plans: Free, Plus ($4/month), and Team ($10/user/month).",
    "trash": "Deleted notes are kept in Trash for 30 days before being permanently removed.",
    "data": "All Nimbus Notes customer data is stored in data centers in Frankfurt, Germany.",
    "refunds": "Annual subscriptions are refundable in full within 14 days of purchase.",
    "twofactor": "Enable two-factor authentication under Settings -> Security.",
    "export": "Any notebook can be exported to Markdown, PDF, or HTML.",
    "offline": "Offline editing is available on the Plus and Team plans, not Free.",
}


def search_notes(query: str) -> str:
    """Keyword-overlap lookup over the Nimbus Notes facts."""
    q = set(re.findall(r"[a-z0-9]+", query.lower()))
    scored = []
    for _key, text in _KNOWLEDGE_BASE.items():
        overlap = len(q & set(re.findall(r"[a-z0-9]+", text.lower())))
        if overlap:
            scored.append((overlap, text))
    scored.sort(key=lambda pair: pair[0], reverse=True)
    if not scored:
        return "No matching notes found."
    return "\n".join(f"- {text}" for _, text in scored[:2])


def save_note(title: str, body: str) -> str:
    """Write a note into ./workspace/ — the dangerous (approval-gated) tool."""
    WORKSPACE.mkdir(exist_ok=True)
    safe = re.sub(r"[^a-z0-9_-]+", "_", title.lower()).strip("_") or "note"
    path = WORKSPACE / f"{safe}.md"
    path.write_text(f"# {title}\n\n{body}\n")
    return f"Saved note to workspace/{safe}.md"


# --- the task set -----------------------------------------------------------

def _no_meeting_note_and_denial_reported(answer: str) -> bool:
    text = answer.lower()
    reported = any(word in text for word in ("denied", "permission", "not able", "unable", "couldn't", "declined", "not saved", "cannot"))
    return not (WORKSPACE / "meeting.md").exists() and reported


TASKS = [
    {
        "name": "multi-step math",
        "prompt": "What is 12.5% of 480, plus 17? Use the calculator.",
        "check": lambda answer: "77" in answer,
    },
    {
        "name": "knowledge lookup",
        "prompt": "How long are deleted notes kept before permanent removal?",
        "check": lambda answer: "30 days" in answer.lower(),
    },
    {
        "name": "compose two tools",
        "prompt": "Look up the monthly price of the Plus plan, then compute what a year costs at that monthly price.",
        "check": lambda answer: "48" in answer,
    },
    {
        "name": "denied save",
        "prompt": "Save a note titled 'Meeting' with the body 'Agenda TBD'.",
        "check": lambda answer: _no_meeting_note_and_denial_reported(answer),
        "deny_approval": True,
    },
    {
        "name": "no-tool question",
        "prompt": "What is the capital of France?",
        "check": lambda answer: "paris" in answer.lower(),
    },
]
