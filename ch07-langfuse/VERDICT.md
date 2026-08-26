# Chapter 7 verdict: Langfuse vs hand-rolled observability

Written from real runs on 2026-07-16 against a **self-hosted Langfuse v3.217**
(six containers via docker compose) with the SDK at langfuse 4.14.0; the app
calls gpt-4o-mini so traces carry real tokens, latency, and cost. Reproduce
with the stack up: `secrun python ch07-langfuse/compare.py`.

> **Model note (2026-08-08).** These numbers were measured on `gpt-4o-mini`,
> which was this repo's default at the time. The code has since moved to
> `gpt-5.4-nano`, so re-running now will not reproduce these figures exactly.
> The verdict is deliberately left as measured rather than rewritten: the
> comparison it records really happened, on the models named above. What
> should survive a model change is the *shape* of each finding, and checking
> whether it does is a better exercise than trusting a refreshed number.

## This is the chapter where the tool most clearly pays for itself

Unlike ch02 (a closed problem) or ch05 (a dead tie), an observability
*platform* does something 121 lines of stdlib genuinely cannot. Both
implementations produce the same per-request record: trace id, nested spans,
tokens, cost. The difference is everything that happens **after the process
exits**, and it's not close.

### The measured finding: the server priced it, and matched to the digit
The hand-rolled version computes each request's dollar cost inline, because
nothing else would (`prompt_tokens/1e6 * 0.15 + ...`). The Langfuse port sends
the model name and **token counts only, never a dollar figure**. Queried back,
the server's total spend was **$0.000111**, identical to the hand-rolled
**$0.000111**: Langfuse derived the cost from usage plus its own maintained
model-pricing map and arrived at the same number. That's the same "the tool
maintains the pricing table so you don't" finding as ch01's LiteLLM; here it's
a property of the platform, and it's why you send tokens and stop hand-coding
`* 0.15`.

(Latency did *not* match: hand-rolled p95 2244ms vs Langfuse 4115ms, and
shouldn't: the two arms make separate live model calls, so wall-clock varies
run to run. Cost is deterministic from tokens; latency isn't. Reporting them
differently is the honest read.)

### What the platform actually buys, stated precisely (per LESSONS §8)
Subtracting what the hand-rolled tracer already did (per-request id, spans,
tokens, and, note, cost, which it also computes):

- **Persistence and retention.** The JSON records go to stderr and are gone
  when the process exits unless you separately ship them somewhere. The
  Langfuse traces are on a server, queryable minutes or weeks later.
- **A query API and a UI.** "What did we spend, what's p95, how many blocked?"
  is one `trace.list()` call or a web view at localhost:3000, not a grep over
  log files you first have to collect. The trace is a navigable tree with
  per-span timing, not a flat line you eyeball.
- **Server-side pricing.** As above: you stop maintaining a cost formula.
- **Shareability.** A teammate who wasn't at your terminal can see the trace.
  The stderr line is yours alone.

The hand-rolled tracer's real, non-trivial wins are the mirror image:
**~0 infrastructure** (a `print`), **nothing leaves the box**, and **no schema
lock-in**: the record is a dict you own, not a row in someone else's Postgres
+ ClickHouse + Redis + MinIO.

## What it costs, and the churn tax again

The price of the platform is **six always-on containers** (web, worker,
Postgres, ClickHouse, Redis, MinIO) versus a `print()`. Standing it up was the
chapter's version-churn lesson (LESSONS §10) in infrastructure form:

- The self-host compose bound Postgres to host **5432** and Redis to **6379**,
  both already owned by local services: two edits to remap host ports before
  the stack would start (Langfuse reaches them over the internal network, so
  only `langfuse-web:3000` actually needs the host).
- The SDK's own API had moved: `start_as_current_span` /
  `update_current_trace` (the shape a 2024 tutorial teaches) are gone 
  it's `start_as_current_observation(as_type=...)` now, and `set_trace_io()`
  is *already deprecated* in favor of `propagate_attributes()`, printing a
  warning on a fresh install. The canonical calls deprecate faster than the
  chapters that teach them.

## When you'd reach for which

- **A script, a solo dev, a batch job, an air-gapped box:** the hand-rolled
  tracer. Structured JSON to stderr piped to `jq` answers every question a
  single operator has, at zero infra and zero data exfiltration.
- **A team running a service for real users:** Langfuse (or a hosted peer).
  The moment more than one person needs to see production traces, "grep my
  stderr" stops being an answer, and retention + a query API + a UI + server-
  side pricing stop being luxuries. This is the tool's lane and it owns it 
  provided you'll run (or pay for) the six-container platform underneath.

The honest one-liner: the hand-rolled version gives you the *record*; Langfuse
gives you the *system around the record*: persistence, query, UI, pricing,
sharing, and that system is the entire point once the request is someone
else's and gone in 80ms.

## The interview sentence

"I instrumented the same request path with my own trace/span/JSON-log layer
and with self-hosted Langfuse: both capture the same per-request data (mine
even computes cost) so the platform's real additions are persistence, a
query API, a UI, and server-side pricing (it matched my hand-computed spend to
the digit from tokens alone), paid for with six always-on containers and a
schema I don't own; I hand-roll for scripts and air-gapped boxes, and adopt
the platform the moment a team needs to see production traces."
