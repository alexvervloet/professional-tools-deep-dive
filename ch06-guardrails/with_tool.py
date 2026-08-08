"""
Chapter 6 port: the managed guards: Llama Guard 3 and Guardrails AI.

Two tools that both get called "guardrails" and are not remotely the same
thing. That confusion is the chapter's subject.

  - llama_guard(): Meta's open-weight SAFETY CLASSIFIER, running locally via
    Ollama (no key, no vendor). You hand it a conversation; it replies "safe"
    or "unsafe" plus a taxonomy code (S1 violent crimes, S2 non-violent
    crimes, S11 self-harm, ...). Read that taxonomy and the prediction writes
    itself: there is no category for "tried to override the system prompt."
    The chapter's job is to MEASURE the prediction, not assert it 
    AUTHORING-LESSONS §12 (a refuted prediction, reported, teaches more than a
    tidy confirmation).

  - guardrails_ai(): a VALIDATOR FRAMEWORK. Not a model, but a pipeline that runs
    validators over text and fails/fixes on violation. The comparison it
    invites isn't "is it smarter than my regex"; it's "what does owning the
    *framework* around my regex buy?"

    The much-cited "50+ validator Hub" turned out to be **account-gated**:
    `guardrails hub install hub://guardrails/regex_match` returns 401
    Unauthorized without a token from guardrailsai.com. Its own error message
    says the token "is only required to install validators and run remote
    inference. It is not needed for local validation," so this chapter takes
    the keyless path and writes a CUSTOM validator, which is both runnable by
    any reader and the more honest comparison anyway: the same injection regex
    as the baseline, wrapped in the framework's machinery.

Both are wrapped behind the same `flag(text) -> bool` the baseline uses, so
compare.py scores every guard identically.

    secrun python ch06-guardrails/with_tool.py
"""

import re

from openai import OpenAI

OLLAMA_BASE_URL = "http://localhost:11434/v1"
# The 1B variant: same Llama Guard 3 taxonomy, smaller weights. The 8B blob
# would not finalize on this network (see VERDICT/history); :1b did. Point this
# at "llama-guard3" (8B) or a hosted endpoint if you have one.
LLAMA_GUARD_MODEL = "llama-guard3:1b"

_ollama = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")

# Llama Guard's reply shape: "safe" | "unsafe\nS<n>". We keep the raw reply so
# compare.py can report WHICH category it fired on: the interesting part.
_LAST_CATEGORY: dict[str, str] = {}


def llama_guard_raw(text: str) -> str:
    """Classify a user turn with Llama Guard 3. Returns its raw verdict."""
    response = _ollama.chat.completions.create(
        model=LLAMA_GUARD_MODEL,
        temperature=0,
        max_completion_tokens=16,
        messages=[{"role": "user", "content": text}],
    )
    return (response.choices[0].message.content or "").strip()


def llama_guard(text: str) -> bool:
    """True if Llama Guard says 'unsafe'. Records the taxonomy code it cited."""
    verdict = llama_guard_raw(text)
    _LAST_CATEGORY[text] = verdict.replace("\n", " ")
    return verdict.lower().startswith("unsafe")


def last_category(text: str) -> str:
    """The taxonomy code Llama Guard cited for `text` (after llama_guard ran)."""
    return _LAST_CATEGORY.get(text, "")


# --- Guardrails AI ----------------------------------------------------------
# Built from the validators that need no extra vendor/model download, so the
# chapter stays runnable: the framework's own structural checks. This is
# deliberately the SAME regex idea as the baseline's heuristic_guard: the
# question being measured is what the framework adds around it.

_INJECTION_PATTERN = (
    r"(?i)(ignore (all |the )?(previous|prior|above)|you are now|"
    r"new instructions?|system\s*:|reveal (the |your )?(secret|passphrase|system prompt))"
)


def _build_guard():
    from guardrails import Guard
    from guardrails.validator_base import (
        FailResult,
        PassResult,
        Validator,
        register_validator,
    )

    @register_validator(name="local/no-injection", data_type="string")
    class NoInjection(Validator):
        """The baseline's regex, as a Guardrails validator. Custom, so no Hub
        account is needed; see the module docstring."""

        def _validate(self, value, metadata):
            if re.search(_INJECTION_PATTERN, value or ""):
                return FailResult(error_message="possible prompt injection")
            return PassResult()

    return Guard().use(NoInjection(on_fail="exception"))


_guard = None


def guardrails_ai(text: str) -> bool:
    """True if the Guardrails AI validator pipeline rejects the text."""
    global _guard
    if _guard is None:
        _guard = _build_guard()
    try:
        _guard.validate(text)
        return False
    except Exception:
        return True


if __name__ == "__main__":
    from cases import ALL_CASES

    print(f"  {'case':22} {'family':9} {'want':>5} {'lguard':>7} {'category':16} {'grails':>7}")
    for case in ALL_CASES:
        flagged = llama_guard(case.text)
        print(f"  {case.name:22} {case.family:9} {str(case.should_flag):>5} "
              f"{str(flagged):>7} {last_category(case.text):16} {str(guardrails_ai(case.text)):>7}")
