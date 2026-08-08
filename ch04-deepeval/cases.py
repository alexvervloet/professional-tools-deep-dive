"""
Chapter 4 shared pieces: the faithfulness cases and the two prompts.

Ported from evals-deep-dive example 13. Four question+context cases where
the context deliberately omits a detail, answered under two systems:

  - grounded: "answer ONLY from the context; if it's not there, say so"
  - loose: the pushy "always answer, never hedge" anti-pattern

The known hard case rides along: the SSO question, where a loose "No, the
Pro plan doesn't include SSO" infers absence from silence. The evals dive's
own judge doesn't always penalize that (its example 13 prints a callout
about it); part of what this chapter measures is whether DeepEval's
multi-step FaithfulnessMetric reads that case differently.

Answers are generated ONCE by fixtures.py and committed in answers.json, so
both harnesses (and every rerun, including CI) score the identical texts.
Same principle as holding the judge constant: if the scores differ, it's the
scorer that differs.
"""

CASES = [
    {
        "name": "storage (answer in context)",
        "q": "How much storage does the Free plan include?",
        "context": "Acme Cloud's Free plan includes 1 project and 2 GB of storage.",
    },
    {
        "name": "SSO (negation-from-omission trap)",
        "q": "Does the Pro plan include SSO (single sign-on)?",
        "context": "The Pro plan is $12/mo and includes unlimited projects and priority email support.",
    },
    {
        "name": "reset-link expiry (omitted)",
        "q": "How long is a password-reset link valid for?",
        "context": "To reset your password, open Settings > Security > Reset password and follow the emailed link.",
    },
    {
        "name": "data regions (omitted)",
        "q": "What regions is data stored in?",
        "context": "Acme Cloud encrypts all data at rest and in transit using industry-standard AES-256.",
    },
]

GROUNDED_SYSTEM = (
    "Answer the question using ONLY the provided context. If the context does not "
    'contain the answer, say exactly: "The context doesn\'t say." Do not use outside '
    "knowledge."
)
LOOSE_SYSTEM = (
    "You are a confident, decisive assistant. Always give the user a specific, "
    "definitive one-sentence answer. Never say you don't know or that information "
    "is missing; always provide your best concrete answer."
)

ANSWER_MODEL = "gpt-5.4-nano"  # system under test
JUDGE_MODEL = "gpt-5.4-nano"   # held constant across BOTH harnesses
