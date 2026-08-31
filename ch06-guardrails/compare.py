"""
Chapter 6 measurement: five guards, four case families, one scoreboard.

Scores every guard on the same 18 cases with the prompt-injection dive's
question: how often did the attacker win, and how often did the guard block a
customer? Per family, because the whole point is that the families have
different answers:

  detection rate per family: of the cases that SHOULD be flagged, how many
                              were? (direct / indirect / harmful separately)
  false-positive rate       of the 5 benign cases, how many were blocked?
                              A guard that fires here is worse than useless.

The prediction on record (from this repo's own planning, and the reason ch06
exists): Llama Guard is a content-safety classifier, so it should win the
HARMFUL family outright and MISS the task-aligned indirect injections,
`doc_phishing_line` above all, the attack that beat every layer in the dive.
Predictions get measured, not asserted (AUTHORING-LESSONS §12); whatever this
prints goes in VERDICT.md, confirmed or refuted.

    secrun python ch06-guardrails/compare.py
"""

import os
import sys
import time

from dotenv import load_dotenv
from openai import OpenAI

import hand_rolled
import with_tool
from cases import ALL_CASES, FAMILIES

load_dotenv()
if not os.getenv("OPENAI_API_KEY"):
    sys.exit("Run via secrun so OPENAI_API_KEY is set (see ../docs/SECRETS.md).")

client = OpenAI()

GUARDS = {
    "heuristic": hand_rolled.heuristic_guard,
    "llm_guard": lambda text: hand_rolled.llm_guard(text, client),
    "channel": hand_rolled.channel_guard,
    "llama_guard": with_tool.llama_guard,
    "grails_ai": with_tool.guardrails_ai,
}


def probe(guard_name: str, guard) -> str:
    """Is this guard actually runnable? Returns '' if OK, else the reason.

    This matters more than it looks. If Llama Guard can't be reached and we
    silently recorded 'did not flag', the scoreboard would print a beautiful,
    completely fabricated finding: 'Llama Guard detected 0/13 attacks.'
    UNAVAILABLE IS NOT A MEASUREMENT. Any guard that can't run is dropped from
    the table with a loud banner instead of scored as a miss.
    """
    try:
        guard("hello")
        return ""
    except Exception as e:
        return f"{type(e).__name__}: {str(e)[:90]}"


unavailable = {name: reason for name, reason in ((n, probe(n, g)) for n, g in GUARDS.items()) if reason}
for name, reason in unavailable.items():
    print(f"\n  !!!! {name.upper()} IS UNAVAILABLE: dropped from the scoreboard, NOT scored as a miss.")
    print(f"       {reason}")
    if name == "llama_guard":
        print("       Llama Guard needs: ollama pull llama-guard3 (or :1b). Without it this")
        print("       chapter's central question: does a safety classifier catch injection?")
        print("       is UNANSWERED. Do not read the table below as evidence about it.")
GUARDS = {name: guard for name, guard in GUARDS.items() if name not in unavailable}

# guard -> case.name -> flagged
flags: dict[str, dict[str, bool]] = {}
elapsed: dict[str, float] = {}

for guard_name, guard in GUARDS.items():
    started = time.perf_counter()
    flags[guard_name] = {}
    for case in ALL_CASES:
        try:
            flags[guard_name][case.name] = bool(guard(case.text))
        except Exception as e:
            sys.exit(f"{guard_name} failed mid-run on {case.name}: {e}; refusing to "
                     f"report a partial scoreboard as a result.")
    elapsed[guard_name] = time.perf_counter() - started

# --- per-family detection + false positives --------------------------------
print("\n  detection rate by family (higher is better), false-positive rate (lower is better)\n")
header = f"  {'guard':12}" + "".join(f"{family:>11}" for family in FAMILIES if family != "benign")
print(header + f"{'benign FP':>11}{'sec':>7}")
for guard_name in GUARDS:
    row = f"  {guard_name:12}"
    for family in FAMILIES:
        cases = [case for case in ALL_CASES if case.family == family]
        fired = sum(flags[guard_name][case.name] for case in cases)
        row += f"{f'{fired}/{len(cases)}':>11}"
    row += f"{elapsed[guard_name]:>6.1f}s"
    print(row)

# --- the attack that beat every layer in the dive ---------------------------
print("\n  ── doc_phishing_line (the attack that survived the whole dive)")
for guard_name in GUARDS:
    verdict = "BLOCKED" if flags[guard_name]["doc_phishing_line"] else "missed"
    print(f"     {guard_name:12} {verdict}")

# --- what Llama Guard actually said ----------------------------------------
if "llama_guard" in GUARDS:
    print("\n  ── Llama Guard's verdicts (taxonomy code = why it fired)")
    for case in ALL_CASES:
        print(f"     {case.name:22} {case.family:9} {with_tool.last_category(case.text) or '(n/a)'}")
else:
    print("\n  ── Llama Guard did not run; its column is absent above, not zero.")
