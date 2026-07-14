# Chapter 2 verdict — Instructor vs hand-rolled vs provider-native

Written from a real run on 2026-07-14 (instructor 1.15.4, openai 2.45.0,
pydantic 2.13.4; gpt-4o-mini and qwen3:8b via Ollama; temperature 0.7; 5 trap
postings × 2 reps × 3 approaches × 2 models = 60 extractions). Reproduce with
`secrun python ch02-instructor/compare.py`.

## The headline finding is the one we didn't order

Every approach succeeded on every run: 10/10 per cell, on both models — and
all 34 semantic trap checks passed everywhere, including an 8B local model
correctly leaving an hourly rate un-annualized and converting a Norwegian
"søknadsfrist 15. august 2026" to ISO. **The 2023 pitch for parse-retry
libraries — "models emit broken JSON, you need machinery" — did not
reproduce** on this schema, at temperature 0.7, on either a frontier mini
model or a local 8B. That's the honest 2026 baseline: for a flat-ish schema
in JSON mode, the reliability war is mostly over.

(Caveats that keep this honest: one schema, n=20 per approach/model, and
failures are rare events — these runs bound the failure rate as "low," not
"zero." The hand-rolled loop DID fire its retry twice, see below.)

## What the measured differences actually were

- **The retry loop still earns its keep — barely.** Hand-rolled went 9/10 on
  first call on *each* backend (2 of 20 runs needed the error-feedback
  retry, both recovered). Instructor and native were 10/10 first-call
  throughout. So first-attempt validation failures at temp 0.7 are real but
  rare — and the difference between the approaches is not whether retries
  happen, it's **who owns the ~40 lines that handle them** (hand_rolled.py's
  entire second half vs `max_retries=3` vs "not needed, the decoder can't
  emit an invalid shape").
- **Constrained decoding is not free — on your own hardware you pay for it
  in latency.** Native mode was the *fastest* approach on OpenAI (1.8s vs
  2.0/2.6) and the *slowest by 2×* on Ollama: 27.7s/request vs Instructor's
  12.5s and hand-rolled's 17.5s, same model, same postings. The schema
  guarantee is enforced by grammar-constrained sampling in the local
  runtime, and it costs generation speed. "Guaranteed shape" and "free" are
  different claims; only the first one survived measurement.
- **The transport does not buy correctness.** 34/34 traps for every
  approach: prompt-block schema, tool-call schema, and constrained decoding
  extracted identical *meaning*. Structured-output tooling decides how the
  schema travels and what happens on shape failure — the normalization rules
  (identical system prompt everywhere) did the semantic work. If your
  extraction is wrong, no structured-output library is the fix.

## Two portability surprises (both pleasant, both version-dependent)

- OpenAI's strict mode accepted a Pydantic `date` field and a `pattern`
  regex on `currency` — both historically outside strict-mode's supported
  subset. The gap between "your Pydantic model" and "what strict mode can
  express" is narrower than its reputation; re-check on your own models.
- Ollama's OpenAI-compat endpoint accepted `response_format=json_schema` via
  the SDK's `.parse()` unchanged — native mode is no longer OpenAI-only,
  it's "any runner that implements the shape."

## Where that leaves the three options

The live decision in 2026 is **Instructor vs native**, and it's about
portability, not reliability: Instructor ran unmodified against both
backends (one `mode=` swap) and keeps semantic retries for constraints a
decoder can't express; native is zero extra dependencies and, on the
provider's own hardware, the fastest and strongest guarantee. Hand-rolling
this particular layer is the hardest to defend of the three — the code you'd
own does nothing the other two don't, which was not true of chapter 1's
provider layer. BAML (the rising schema-first DSL, cross-language, its own
prompt format) is worth knowing exists; nothing in these measurements — zero
failures to fix, zero trap misses — creates a problem it would solve for a
single-service Python stack.

## The interview sentence

"I've built structured extraction three ways — schema-in-prompt with my own
validate-and-retry loop, Instructor, and native constrained decoding — and
measured them head-to-head: on current models the shape-failure problem the
libraries were built for has mostly closed, so I choose by portability and
latency, and I know constrained decoding's guarantee costs 2× generation
speed on a local runtime."
