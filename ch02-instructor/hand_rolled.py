"""
Chapter 2 baseline: schema in the prompt, parse-and-retry by hand.

This is what the prompt-engineering dive built (example 02), plus the retry
loop every production version of it grows within a week:

  1. Render the schema as prose inside the prompt (schema_block()).
  2. Ask for JSON mode so the reply is at least *syntactically* JSON.
  3. json.loads it (stripping the ```json fences some models add anyway).
  4. Validate with Pydantic, because "valid JSON" says nothing about the
     right keys, types, enums, or the currency regex.
  5. On failure, go again, with the validation error pasted into the
     conversation so the model can fix what it got wrong.

Steps 3-5 are the code Instructor exists to delete. Note the shape of what
you own here: the fence-stripping heuristic, the error-feedback message, the
retry budget, and the decision of what to do when the budget runs out.

Run one posting through it:

    secrun python ch02-instructor/hand_rolled.py
"""

import json
import os
import sys

from dotenv import load_dotenv
from openai import OpenAI
from pydantic import ValidationError

from extraction import POSTINGS, SYSTEM_RULES, JobPosting, schema_block

OPENAI_MODEL = "gpt-5.4-nano"
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"

MAX_RETRIES = 2
TEMPERATURE = 0.7  # deliberately not 0; compare.py measures reliability


def make_client(backend: str) -> tuple[OpenAI, str]:
    if backend == "openai":
        return OpenAI(), OPENAI_MODEL
    if backend == "ollama":
        return OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama"), OLLAMA_MODEL
    raise ValueError(f"unknown backend: {backend}")


def strip_fences(text: str) -> str:
    """Models sometimes wrap JSON in ```json ... ``` even in JSON mode."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("\n", 1)[1] if "\n" in text else text
        text = text.rsplit("```", 1)[0]
    return text.strip()


def extract(backend: str, posting: str) -> tuple[JobPosting, int]:
    """Return (validated JobPosting, calls_used). Raises after MAX_RETRIES."""
    client, model = make_client(backend)
    suffix = " /no_think" if backend == "ollama" else ""
    messages = [
        {"role": "system", "content": SYSTEM_RULES},
        {
            "role": "user",
            "content": f"{schema_block()}\n\nJob posting:\n\"\"\"{posting}\"\"\"{suffix}",
        },
    ]

    last_error: Exception | None = None
    for attempt in range(1 + MAX_RETRIES):
        response = client.chat.completions.create(
            model=model,
            messages=messages,
            temperature=TEMPERATURE,
            response_format={"type": "json_object"},
        )
        raw = response.choices[0].message.content or ""
        try:
            return JobPosting.model_validate(json.loads(strip_fences(raw))), attempt + 1
        except (json.JSONDecodeError, ValidationError) as e:
            last_error = e
            # What makes the retry work: show the model what it got wrong.
            messages.append({"role": "assistant", "content": raw})
            messages.append({
                "role": "user",
                "content": f"That was invalid: {e}\nReturn corrected JSON only.{suffix}",
            })
    raise RuntimeError(f"failed after {1 + MAX_RETRIES} attempts") from last_error


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    name, posting = next(iter(POSTINGS.items()))
    job, calls = extract("openai", posting)
    print(f"[{name}] parsed in {calls} call(s):")
    print(job.model_dump_json(indent=2))
