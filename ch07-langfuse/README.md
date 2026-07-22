# Chapter 7: Langfuse vs hand-rolled observability

The production dive built observability from scratch: a trace id per request,
timed spans, and one JSON object per line to stderr
([hand_rolled.py](hand_rolled.py), condensed from `prod/observability.py`).
That answers "what happened in *this* request." What it doesn't answer is
"what happened across the last *ten thousand* requests," because the query
story is grep. Langfuse is the platform that turns the record you already own
into something you can aggregate, filter, and look at.

Both implementations wrap the **same** request path ([app.py](app.py)): input
guard → versioned prompt → model call → output redaction. Only the tracing
differs.

## Running it

The hand-rolled side needs nothing but a key:

```bash
secrun python ch07-langfuse/hand_rolled.py      # JSON trace records -> stderr
```

The Langfuse side needs the self-hosted stack (six containers: web, worker,
Postgres, ClickHouse, Redis, MinIO):

```bash
cd ch07-langfuse
cp .env.example .env            # local-only demo keys; auto-creates a project
docker compose up -d            # first boot pulls images + migrates (~1-2 min)
# wait until http://localhost:3000 loads, then:
secrun python with_tool.py      # sends traces; prints where to look
```

Open <http://localhost:3000> (login from `.env`) to see the traces as a
nested tree with per-span timing, token usage, and cost: the thing the JSON
lines contain but can't *show* you.

Tear down when done:

```bash
docker compose down             # add -v to also drop the volumes
```

## The honest framing

This is the chapter where the tool most obviously earns its keep: an
observability *platform* genuinely does something 70 lines of stdlib can't
(a UI, server-side aggregation, retention, filtering). The chapter's job is
to be precise about the price of that: six always-on containers vs a
`print()`, and a trace that now lives in someone else's schema. See
[VERDICT.md](VERDICT.md) for the measured comparison.
