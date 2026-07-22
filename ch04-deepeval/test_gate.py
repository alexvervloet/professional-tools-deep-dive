"""
Chapter 4 CI artifact: the faithfulness gate as a pytest file.

This is what DeepEval is actually FOR: the eval as a test suite. Each
grounded answer becomes a test case; the gate is `pytest ch04-deepeval` (or
`deepeval test run` for the fancier report). Exit code 1 on regression, no
runner code owned by you; compare that to hand_rolled.py's __main__, which
is the same gate with the loop and the threshold written out by hand.

Two things to know before trusting this gate (measured in compare.py, argued
in VERDICT.md):

  - It gates the GROUNDED system's answers. Don't add the loose ones
    expecting them all to fail: FaithfulnessMetric scores by
    absence-of-contradiction, so an invented-but-uncontradicted claim
    ("links are valid for 24 hours" over a silent context) passes at 1.00.
    If your rubric says unsupported = unfaithful, this metric is not your
    rubric; with someone else's gate you inherit someone else's definition.
  - The multi-step judge pipeline has run-to-run wobble (we observed a
    correct refusal score 0.00 on one run and 1.00 on the next), so a gate
    this small can flake. The evals dive's example 09 is about exactly this.

Run:

    secrun .venv/bin/python -m pytest ch04-deepeval/test_gate.py -q
"""

import json
import os
from pathlib import Path

import pytest

os.environ.setdefault("DEEPEVAL_TELEMETRY_OPT_OUT", "1")

from deepeval import assert_test
from deepeval.metrics import FaithfulnessMetric
from deepeval.test_case import LLMTestCase

from cases import CASES, JUDGE_MODEL

CONTEXTS = {case["name"]: case["context"] for case in CASES}
GROUNDED_ROWS = [
    row
    for row in json.loads((Path(__file__).parent / "answers.json").read_text())
    if row["prompt"] == "grounded"
]


@pytest.mark.parametrize("row", GROUNDED_ROWS, ids=lambda row: row["case"])
def test_grounded_answers_stay_faithful(row: dict) -> None:
    assert_test(
        LLMTestCase(
            input=row["case"],
            actual_output=row["answer"],
            retrieval_context=[CONTEXTS[row["case"]]],
        ),
        [FaithfulnessMetric(threshold=0.75, model=JUDGE_MODEL, async_mode=False)],
    )
