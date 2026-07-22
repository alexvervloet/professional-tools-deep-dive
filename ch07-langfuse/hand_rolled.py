"""
Chapter 7 baseline: the production dive's observability, condensed.

trace + spans + one-JSON-object-per-line structured logs, ported from
ai-in-production-deep-dive prod/observability.py. This is the whole thing an
observability tool replaces, in ~70 lines of stdlib: a request gets a trace
id, timed spans nest inside it, and the summary is a flat JSON record you can
grep or ship to any log store.

What you OWN here, and will compare against Langfuse: the data model (trace ->
spans -> attributes), the sink (stderr JSON: a real deploy points it at a log
aggregator), and the query story (there isn't one; grep is the query story).
That last gap is the whole pitch for a platform.

Run the workload through it (writes JSONL trace records to stderr):

    secrun python ch07-langfuse/hand_rolled.py
"""

import json
import os
import sys
import time
import uuid
from contextlib import contextmanager
from dataclasses import dataclass, field

from dotenv import load_dotenv
from openai import OpenAI

import app


@dataclass
class Trace:
    trace_id: str
    name: str
    attributes: dict = field(default_factory=dict)
    spans: dict = field(default_factory=dict)
    duration_ms: float = 0.0

    def set(self, **attrs) -> None:
        self.attributes.update(attrs)

    @contextmanager
    def span(self, name: str):
        start = time.perf_counter()
        try:
            yield
        finally:
            self.spans[name] = round((time.perf_counter() - start) * 1000, 1)

    def summary(self) -> dict:
        return {
            "trace_id": self.trace_id, "request": self.name,
            "duration_ms": round(self.duration_ms, 1), **self.attributes,
            "spans": self.spans,
        }


@contextmanager
def start_trace(name: str):
    trace = Trace(trace_id=uuid.uuid4().hex[:12], name=name)
    start = time.perf_counter()
    try:
        yield trace
    finally:
        trace.duration_ms = (time.perf_counter() - start) * 1000
        print(json.dumps(trace.summary(), default=str), file=sys.stderr)


def answer(client: OpenAI, question: str) -> dict:
    """Run one request, fully traced. Returns the trace summary.

    The summary is built AFTER the `with` closes, because start_trace sets
    duration_ms in its exit hook; returning from inside the block would hand
    back a record with duration_ms=0.0 that contradicts the JSON written to
    stderr (an honest-output bug we hit and fixed; see LESSONS §presentation).
    """
    with start_trace("support.answer") as trace:
        trace.set(prompt_version=app.ACTIVE_VERSION, model=app.MODEL)

        with trace.span("guard.input"):
            allowed, reason = app.check_input(question)
        if not allowed:
            trace.set(blocked=True, block_reason=reason)
        else:
            with trace.span("model.call"):
                response = client.chat.completions.create(
                    model=app.MODEL, temperature=0, max_tokens=200,
                    messages=[
                        {"role": "system", "content": app.PROMPTS[app.ACTIVE_VERSION]},
                        {"role": "user", "content": question},
                    ],
                )
            usage = response.usage
            assert usage is not None
            cost = usage.prompt_tokens / 1e6 * 0.15 + usage.completion_tokens / 1e6 * 0.60
            trace.set(
                prompt_tokens=usage.prompt_tokens, completion_tokens=usage.completion_tokens,
                cost_usd=round(cost, 6),
            )
            with trace.span("guard.output"):
                _ = app.redact_pii(response.choices[0].message.content or "")
    return trace.summary()


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    client = OpenAI()
    # The JSON trace record (one per request) is written to stderr as each
    # trace closes: that IS the artifact. We don't re-print duration here: the
    # summary returned by answer() is built inside the trace, before the exit
    # hook sets duration_ms, so it would read 0.0 and contradict the JSON.
    for question in app.WORKLOAD:
        summary = answer(client, question)
        print(f"# handled [{summary['trace_id']}] "
              f"{'BLOCKED' if summary.get('blocked') else 'ok'}: {question[:45]}", file=sys.stderr)
