"""
Chapter 2 port: the same extraction through Instructor, and through the
provider's own structured-output mode.

Two competitors to the hand-rolled loop, because in 2026 the real question
isn't "Instructor or hand-rolled"; it's "does a library still earn its keep
now that providers do this natively?"

  - instructor_extract(): `instructor.from_openai(client)` patches the client;
    `response_model=JobPosting` replaces the schema block, json.loads, the
    Pydantic call, the fence-stripping, AND the retry-with-error-feedback
    loop: that whole second half of hand_rolled.py is now one kwarg
    (`max_retries`). Works against Ollama too, in JSON mode.
  - native_extract(): `client.chat.completions.parse()`, the OpenAI dive's
    example 14. No retries because (on OpenAI) none are needed for *shape*:
    constrained decoding guarantees schema-valid output at generation time.
    What it does NOT guarantee is Pydantic-side constraints it can't express
    in strict mode; compare.py checks whether that gap is real.

Both count actual HTTP requests via an httpx event hook, so compare.py
reports calls the provider billed, not attempts we think we made.

Run one posting through both:

    secrun python ch02-instructor/with_tool.py
"""

import os
import sys

import httpx
import instructor
from dotenv import load_dotenv
from openai import OpenAI

from extraction import POSTINGS, SYSTEM_RULES, JobPosting
from hand_rolled import MAX_RETRIES, OLLAMA_BASE_URL, OLLAMA_MODEL, OPENAI_MODEL, TEMPERATURE


def counting_client(backend: str) -> tuple[OpenAI, str, list[int]]:
    """An OpenAI client whose every HTTP request bumps a counter."""
    calls: list[int] = []
    http_client = httpx.Client(event_hooks={"request": [lambda _: calls.append(1)]})
    if backend == "openai":
        return OpenAI(http_client=http_client), OPENAI_MODEL, calls
    if backend == "ollama":
        return (
            OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama", http_client=http_client),
            OLLAMA_MODEL,
            calls,
        )
    raise ValueError(f"unknown backend: {backend}")


def _messages(backend: str, posting: str) -> list[dict]:
    suffix = " /no_think" if backend == "ollama" else ""
    return [
        {"role": "system", "content": SYSTEM_RULES},
        {"role": "user", "content": f'Extract the job posting:\n"""{posting}"""{suffix}'},
    ]


def instructor_extract(backend: str, posting: str) -> tuple[JobPosting, int]:
    client, model, calls = counting_client(backend)
    # TOOLS mode (function calling) for OpenAI; Ollama gets JSON mode: same
    # channel the hand-rolled version uses, so the comparison stays fair.
    mode = instructor.Mode.TOOLS if backend == "openai" else instructor.Mode.JSON
    patched = instructor.from_openai(client, mode=mode)
    job = patched.chat.completions.create(
        model=model,
        messages=_messages(backend, posting),
        response_model=JobPosting,
        temperature=TEMPERATURE,
        max_retries=1 + MAX_RETRIES,  # instructor counts total attempts
    )
    return job, len(calls)


def native_extract(backend: str, posting: str) -> tuple[JobPosting, int]:
    client, model, calls = counting_client(backend)
    response = client.chat.completions.parse(
        model=model,
        messages=_messages(backend, posting),
        temperature=TEMPERATURE,
        response_format=JobPosting,
    )
    message = response.choices[0].message
    if message.refusal:
        raise RuntimeError(f"model refused: {message.refusal}")
    assert message.parsed is not None
    return message.parsed, len(calls)


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    name, posting = next(iter(POSTINGS.items()))
    for label, fn in (("instructor", instructor_extract), ("native", native_extract)):
        job, calls = fn("openai", posting)
        print(f"[{label}, {calls} HTTP call(s)] {job.title!r}, "
              f"{job.salary_min}-{job.salary_max} {job.currency}, apply_by={job.apply_by}")
