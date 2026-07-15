# Exercises

Grown chapter by chapter. Each exercise is designed so the thing you discover
is the thing the chapter claimed — verify it, don't take the verdict's word.

## Chapter 1 — LiteLLM

1. **Add a fourth provider to both implementations.** Any OpenAI-compatible
   runner works (LM Studio on another machine, vLLM, a second Ollama). Count
   the lines it took in `hand_rolled.py` vs `with_tool.py`. Then check: did
   `completion_cost()` know what to charge for it, or did the maintained
   pricing map just hit the same wall as the hand table?
2. **Catch the fallback red-handed.** In `with_tool.chat_with_fallback`, the
   primary model's failure never raises — it goes to a logger. Wire up
   `litellm.callbacks` (or just a logging handler) so a fallback event
   produces something you'd actually see in production. How would the
   hand-rolled version have surfaced the same failure?
3. **Find where `ollama/` loses the answer.** Set
   `litellm._turn_on_debug()` and re-run compare.py §3. Somewhere in the
   debug output, the tool-result turn goes into the generate-API translation
   and an empty string comes out. Locating it teaches you what "the
   abstraction tax" costs when you're the one paying it: you're now debugging
   someone else's provider layer instead of your own.

## Chapter 2 — Instructor

1. **Make the failures come back.** The verdict says the reliability gap has
   mostly closed *on this schema*. Stress it: add a deeply nested field
   (say, `interview_stages: list[Stage]` with its own enum and date), or
   drop the local model to something smaller than 8B, and re-run
   compare.py. At what point does the hand-rolled first-call rate fall — and
   does native mode's guarantee still hold when the schema gets gnarly, or
   does strict mode start rejecting parts of your model?
2. **Charge the retry to someone.** Two of twenty hand-rolled runs took a
   second call. Extend compare.py to price the matrix with ch01's cost
   tools: what does each approach cost per 1,000 postings, and does
   Instructor's tool-call transport (schema tokens in every request) cost
   more than the hand-rolled prompt block it replaced?
3. **Find the constraint the decoder can't check.** Add a Pydantic
   `model_validator` that enforces `salary_min <= salary_max`. Constrained
   decoding cannot express cross-field rules — so what happens in each of
   the three approaches when the model emits a reversed range? (Build a
   posting that tempts it: "up to 95k, from 80k".)

## Chapter 3 — LlamaIndex

1. **Build the corpus that separates them.** All three pipelines tied at
   100% here. Make them differentiate: add near-duplicate docs (three plan
   pages differing only in one number — the rag dive's example 11 trick),
   then re-run compare.py. Which falls first: the 4-whole-doc defaults
   engine, or the fine-chunked ones?
2. **Price the defaults.** Wire ch01's cost tools into compare.py and put a
   dollar figure on one full eval pass per pipeline. ada-002 is 5× the
   embedding price and gpt-3.5-turbo ~2.5× the LLM price — but the defaults
   engine also embeds fewer, bigger chunks and retrieves k=2. Which effect
   wins on this corpus? Measure before you guess.
3. **Win the citations back.** The port silently dropped the baseline's
   citation contract (0/12). LlamaIndex's own fix is
   `CitationQueryEngine` — swap it into build_matched() and re-run. Does the
   cited rate recover to 12/12, and what did its prompt and chunking do to
   the other columns?
