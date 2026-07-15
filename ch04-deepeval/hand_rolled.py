"""
Chapter 4 baseline — the evals dive's faithfulness judge + threshold gate.
==========================================================================

The whole hand-rolled eval stack, condensed from evals-deep-dive
(evals/judges.py + the runner's gate idea): one LLM call per case with a
1-5 rubric, parsed with a regex, pass = rating >= 4. Then the gate every CI
eval needs: the grounded prompt must average >= 0.75 faithfulness AND beat
the loose prompt's mean — exit 1 otherwise.

Total machinery: ~60 lines, one judge call per answer, zero dependencies
beyond the SDK. Keep that count in mind when you watch DeepEval's
FaithfulnessMetric spend several calls per answer to produce its version of
the same number (compare.py counts them).

    secrun python ch04-deepeval/hand_rolled.py
"""

import json
import os
import re
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from cases import JUDGE_MODEL

ANSWERS_PATH = Path(__file__).parent / "answers.json"
GATE_MEAN = 0.75

# Verbatim from evals-deep-dive evals/judges.py.
FAITHFULNESS_SYSTEM = (
    "You judge whether an ANSWER is faithful to (fully grounded in) the provided "
    "CONTEXT. An answer is faithful only if EVERY factual claim it makes is supported "
    "by the context. A claim that is true in the real world but NOT present in the "
    "context still makes the answer unfaithful — the test is grounding, not truth. "
    "Refusing or saying the context doesn't cover it, when it genuinely doesn't, IS "
    "faithful. Rate 1 (claims unsupported by the context) to 5 (every claim grounded). "
    "Reply with ONLY the integer."
)


def judge_faithfulness(client: OpenAI, context: str, answer: str) -> tuple[float, int, int, int]:
    """One call, one integer, one regex. Returns (score 0-1, raw 1-5, tokens in, tokens out)."""
    response = client.chat.completions.create(
        model=JUDGE_MODEL,
        temperature=0,
        max_tokens=8,
        messages=[
            {"role": "system", "content": FAITHFULNESS_SYSTEM},
            {"role": "user", "content": f"CONTEXT:\n{context}\n\nANSWER:\n{answer}\n\nFaithfulness score (1-5):"},
        ],
    )
    match = re.search(r"[1-5]", response.choices[0].message.content or "")
    raw = int(match.group()) if match else 1
    usage = response.usage
    assert usage is not None
    return (raw - 1) / 4, raw, usage.prompt_tokens, usage.completion_tokens


def score_all(client: OpenAI) -> list[dict]:
    from cases import CASES

    contexts = {case["name"]: case["context"] for case in CASES}
    rows = json.loads(ANSWERS_PATH.read_text())
    for row in rows:
        score, raw, tokens_in, tokens_out = judge_faithfulness(
            client, contexts[row["case"]], row["answer"]
        )
        row["score"], row["raw"] = score, raw
        row["tokens_in"], row["tokens_out"] = tokens_in, tokens_out
    return rows


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    rows = score_all(OpenAI())
    for row in rows:
        print(f"  {row['raw']}/5  {row['prompt']:8} {row['case']}")

    def mean(prompt: str) -> float:
        scores = [row["score"] for row in rows if row["prompt"] == prompt]
        return sum(scores) / len(scores)

    grounded, loose = mean("grounded"), mean("loose")
    print(f"\nmean faithfulness — grounded: {grounded:.2f}   loose: {loose:.2f}")
    if grounded >= GATE_MEAN and grounded > loose:
        print(f"GATE PASS (grounded >= {GATE_MEAN} and > loose)")
    else:
        print("GATE FAIL")
        sys.exit(1)
