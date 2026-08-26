"""
Chapter 3 shared eval: the measuring stick, held constant.

The metrics and the first five questions are the rag dive's example 09,
verbatim in mechanics: hit rate @ k, MRR, and does-the-expected-fact-appear
answer correctness. Seven more labelled questions were added (from the same
corpus, same style) so a difference between pipelines has room to show up;
five questions can hide a real gap behind one lucky hit.

Every pipeline in this chapter is scored by run_eval() through the same two
callables, so nothing about the scoring can favor an implementation:

    retrieve_sources(question) -> ordered list of source filenames
    answer(question)           -> the generated answer text
"""

from dataclasses import dataclass
from typing import Callable

# (question, document that should answer it, fact the answer must contain)
EVALSET: list[tuple[str, str, str]] = [
    # -- the rag dive's original five --
    ("How long are deleted notes kept?", "security-and-privacy.md", "30 days"),
    ("How much does the Plus plan cost per month?", "plans-and-billing.md", "$4"),
    ("Where is my data stored?", "security-and-privacy.md", "Frankfurt"),
    ("Can I get a refund on an annual subscription?", "plans-and-billing.md", "14 days"),
    ("Which app can I import my notes from?", "getting-started.md", "Evernote"),
    # -- seven more, labelled from the same corpus --
    ("What is the API rate limit?", "account-and-support.md", "120"),
    ("What keyboard shortcut opens Quick Capture?", "getting-started.md", "Ctrl+Shift+Space"),
    ("How much storage does the Free plan include?", "plans-and-billing.md", "1 GB"),
    ("Why doesn't Nimbus Notes support SMS codes for two-factor auth?",
     "security-and-privacy.md", "SIM"),
    ("What error code means my import file is too big?", "getting-started.md", "NN-413"),
    ("How big is the education discount?", "plans-and-billing.md", "50%"),
    ("On which days is support available?", "account-and-support.md", "Monday"),
]


@dataclass
class EvalResult:
    hit_rate: float
    mrr: float
    answer_rate: float
    misses: list[str]  # human-readable failures for the printout
    answers: list[str]  # every generated answer, for property checks (citations etc.)


def run_eval(
    retrieve_sources: Callable[[str], list[str]],
    answer: Callable[[str], str],
) -> EvalResult:
    hits = 0
    rr_total = 0.0
    answers_ok = 0
    misses: list[str] = []
    answers: list[str] = []
    for question, expected_source, expected_fact in EVALSET:
        sources = retrieve_sources(question)
        if expected_source in sources:
            hits += 1
            rr_total += 1.0 / (sources.index(expected_source) + 1)
        else:
            misses.append(f"retrieval: {question!r} -> {sources}")
        text = answer(question)
        answers.append(text)
        if expected_fact.lower() in text.lower():
            answers_ok += 1
        else:
            misses.append(f"answer: {question!r} lacks {expected_fact!r}: {text[:80]!r}")
    n = len(EVALSET)
    return EvalResult(hits / n, rr_total / n, answers_ok / n, misses, answers)
