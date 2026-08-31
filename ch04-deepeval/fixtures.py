"""
Chapter 4 fixture generation: run the system under test ONCE.

Generates the 8 answers (4 cases x grounded/loose) at temperature 0 and
writes answers.json. Committed to the repo so every scorer run (hand-rolled,
DeepEval, pytest gate, CI) grades the same fixed texts instead of a fresh
nondeterministic sample. Regenerate deliberately (delete the file and rerun)
and expect scores to move a little; that wobble is the evals dive's
example 09, not a bug here.

    secrun python ch04-deepeval/fixtures.py
"""

import json
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

from cases import ANSWER_MODEL, CASES, GROUNDED_SYSTEM, LOOSE_SYSTEM

ANSWERS_PATH = Path(__file__).parent / "answers.json"


def main() -> None:
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see ../docs/SECRETS.md).")
    if ANSWERS_PATH.exists():
        sys.exit(f"{ANSWERS_PATH.name} already exists; delete it to regenerate.")

    client = OpenAI()
    rows = []
    for case in CASES:
        for prompt_label, system in (("grounded", GROUNDED_SYSTEM), ("loose", LOOSE_SYSTEM)):
            response = client.chat.completions.create(
                model=ANSWER_MODEL,
                temperature=0,
                max_completion_tokens=200,
                messages=[
                    {"role": "system", "content": system},
                    {"role": "user", "content": f"Context:\n{case['context']}\n\nQuestion: {case['q']}"},
                ],
            )
            text = response.choices[0].message.content or ""
            rows.append({"case": case["name"], "prompt": prompt_label, "answer": text})
            print(f"[{case['name']} / {prompt_label}] {text[:70]}")
    ANSWERS_PATH.write_text(json.dumps(rows, indent=2) + "\n")
    print(f"\nWrote {len(rows)} answers to {ANSWERS_PATH.name}")


if __name__ == "__main__":
    main()
