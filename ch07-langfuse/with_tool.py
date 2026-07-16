"""
Chapter 7 port — the same request path, traced with Langfuse.
=============================================================

Same app.py request path as hand_rolled.py, but the trace / spans / attributes
go to a Langfuse instance (self-hosted; see the chapter README) instead of a
JSON line on stderr. The instrumentation shape is deliberately the same so the
comparison is fair:

  hand-rolled                     Langfuse SDK
  ---------------------------     ------------------------------------------
  with start_trace("..."):        with lf.start_as_current_span(name=...):
    trace.set(**attrs)              lf.update_current_trace(metadata=...)
    with trace.span("guard"):       with lf.start_as_current_span(name="guard"):
    with trace.span("model"):       with lf.start_as_current_generation(...):  <- typed as an LLM call
    print(json, file=stderr)        lf.flush()  -> a server, a UI, a query API

The one structural upgrade Langfuse gives for free: the model call is a
GENERATION, a first-class span type that carries model, token usage, and cost,
so the platform can aggregate spend and latency across requests without you
parsing your own logs. That aggregation — not the per-request record, which the
baseline also has — is what compare.py and the verdict weigh.

Requires the stack up and .env present (see README):

    (cd ch07-langfuse && docker compose up -d)   # once
    secrun python ch07-langfuse/with_tool.py
"""

import os
import sys

from dotenv import load_dotenv
from openai import OpenAI

import app


def get_langfuse():
    """Construct the client and verify the server is actually reachable.

    Same rule as ch06: an unreachable platform is not a silent no-op. If the
    server isn't up or the keys are wrong, we fail loudly rather than pretend
    traces were recorded.
    """
    from langfuse import Langfuse

    client = Langfuse(
        public_key=os.environ["LANGFUSE_PUBLIC_KEY"],
        secret_key=os.environ["LANGFUSE_SECRET_KEY"],
        host=os.environ.get("LANGFUSE_HOST", "http://localhost:3000"),
    )
    if not client.auth_check():
        sys.exit(
            "Langfuse auth_check() failed — is the stack up and .env correct?\n"
            "  cd ch07-langfuse && docker compose up -d   (wait ~1 min for boot)\n"
            "Refusing to run: unrecorded traces are not a measurement (see ch06)."
        )
    return client


def answer(lf, oai: OpenAI, question: str) -> str:
    """Run one request as a Langfuse trace with nested spans/generation."""
    with lf.start_as_current_span(name="support.answer") as root:
        lf.update_current_trace(
            input=question,
            metadata={"prompt_version": app.ACTIVE_VERSION, "model": app.MODEL},
        )

        with lf.start_as_current_span(name="guard.input"):
            allowed, reason = app.check_input(question)
        if not allowed:
            root.update(metadata={"blocked": True, "block_reason": reason})
            lf.update_current_trace(output="(blocked)")
            return "(blocked)"

        with lf.start_as_current_generation(name="model.call", model=app.MODEL) as gen:
            response = oai.chat.completions.create(
                model=app.MODEL, temperature=0, max_tokens=200,
                messages=[
                    {"role": "system", "content": app.PROMPTS[app.ACTIVE_VERSION]},
                    {"role": "user", "content": question},
                ],
            )
            usage = response.usage
            assert usage is not None
            text = response.choices[0].message.content or ""
            # Feed the generation its typed fields — this is what lets the UI
            # aggregate tokens/cost across traces without log parsing.
            gen.update(
                input=question,
                output=text,
                usage_details={
                    "input": usage.prompt_tokens,
                    "output": usage.completion_tokens,
                },
            )

        with lf.start_as_current_span(name="guard.output"):
            text = app.redact_pii(text)
        lf.update_current_trace(output=text)
        return text


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    lf = get_langfuse()
    oai = OpenAI()
    for question in app.WORKLOAD:
        result = answer(lf, oai, question)
        print(f"# handled: {question[:45]:45} -> {result[:40]}")
    lf.flush()
    print(f"\nFlushed to Langfuse at {os.environ.get('LANGFUSE_HOST')} "
          f"— open it and look at project {os.environ.get('LANGFUSE_PUBLIC_KEY')!r}.")
