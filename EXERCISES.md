# Exercises

Grown chapter by chapter. Each exercise is designed so the thing you discover
is the thing the chapter claimed: verify it, don't take the verdict's word.

## Chapter 1: LiteLLM

1. **Add a fourth provider to both implementations.** Any OpenAI-compatible
   runner works (LM Studio on another machine, vLLM, a second Ollama). Count
   the lines it took in `hand_rolled.py` vs `with_tool.py`. Then check: did
   `completion_cost()` know what to charge for it, or did the maintained
   pricing map just hit the same wall as the hand table?
2. **Catch the fallback red-handed.** In `with_tool.chat_with_fallback`, the
   primary model's failure never raises; it goes to a logger. Wire up
   `litellm.callbacks` (or just a logging handler) so a fallback event
   produces something you'd actually see in production. How would the
   hand-rolled version have surfaced the same failure?
3. **Find where `ollama/` loses the answer.** Set
   `litellm._turn_on_debug()` and re-run compare.py §3. Somewhere in the
   debug output, the tool-result turn goes into the generate-API translation
   and an empty string comes out. Locating it teaches you what "the
   abstraction tax" costs when you're the one paying it: you're now debugging
   someone else's provider layer instead of your own.

## Chapter 2: Instructor

1. **Make the failures come back.** The verdict says the reliability gap has
   mostly closed *on this schema*. Stress it: add a deeply nested field
   (say, `interview_stages: list[Stage]` with its own enum and date), or
   drop the local model to something smaller than 8B, and re-run
   compare.py. At what point does the hand-rolled first-call rate fall, and
   does native mode's guarantee still hold when the schema gets gnarly, or
   does strict mode start rejecting parts of your model?
2. **Charge the retry to someone.** Two of twenty hand-rolled runs took a
   second call. Extend compare.py to price the matrix with ch01's cost
   tools: what does each approach cost per 1,000 postings, and does
   Instructor's tool-call transport (schema tokens in every request) cost
   more than the hand-rolled prompt block it replaced?
3. **Find the constraint the decoder can't check.** Add a Pydantic
   `model_validator` that enforces `salary_min <= salary_max`. Constrained
   decoding cannot express cross-field rules, so what happens in each of
   the three approaches when the model emits a reversed range? (Build a
   posting that tempts it: "up to 95k, from 80k".)

## Chapter 3: LlamaIndex

1. **Build the corpus that separates them.** All three pipelines tied at
   100% here. Make them differentiate: add near-duplicate docs (three plan
   pages differing only in one number, the rag dive's example 11 trick),
   then re-run compare.py. Which falls first: the 4-whole-doc defaults
   engine, or the fine-chunked ones?
2. **Price the defaults.** Wire ch01's cost tools into compare.py and put a
   dollar figure on one full eval pass per pipeline. ada-002 is 5× the
   embedding price and gpt-3.5-turbo ~2.5× the LLM price, but the defaults
   engine also embeds fewer, bigger chunks and retrieves k=2. Which effect
   wins on this corpus? Measure before you guess.
3. **Win the citations back.** The port silently dropped the baseline's
   citation contract (0/12). LlamaIndex's own fix is
   `CitationQueryEngine`: swap it into build_matched() and re-run. Does the
   cited rate recover to 12/12, and what did its prompt and chunking do to
   the other columns?

## Chapter 4: DeepEval

1. **Measure the flake rate properly.** We saw the gate flip across four
   passes; four is an anecdote. Loop the pytest gate 10 times, tally
   per-case pass counts, and compute what CI would experience as the
   false-alarm rate. Then re-shape the gate to threshold the *mean* across
   cases (like hand_rolled.py) instead of asserting per case: how much
   does the flake rate drop?
2. **Close the definition gap.** DeepEval's GEval metric takes your own
   criteria text. Re-express the dive's rubric ("every claim must be
   supported; true-but-unsupported fails") as a GEval and re-run
   compare.py: does "24 hours" fail now? What did the switch cost per case
   vs FaithfulnessMetric?
3. **Cross-check with Ragas.** Score the same answers.json with Ragas'
   faithfulness metric (separate venv if the resolver objects; see the
   requirements.txt saga). Three tools, one word, how many definitions?

## Chapter 5: LangGraph

1. **Make durability earn its complexity.** The interrupt demo resumes in
   the same process, which the hand-rolled callback also handles. Split it:
   one script that runs until the interrupt and exits; a second script that
   resumes from a `SqliteSaver` checkpoint with the approval. Then try to
   sketch what the hand-rolled loop would need to do the same; that gap is
   LangGraph's actual product.
2. **Find the tie-breaker task.** Both implementations tied 10/10. Design a
   task where they *diverge* (hint: the baseline's max_steps=6 vs the
   graph's default recursion limit of 25. Give both an impossible task
   ("compute the 4th root of the Plus plan's color") and compare how many
   LLM calls each burns before giving up, and what that costs.
3. **Migrate off the deprecated import.** Install `langchain`, switch to
   `from langchain.agents import create_agent`, and re-run compare.py. What
   changed in the dependency tree, and did any measured number move? Now
   you've done a framework version migration: write down how long it took.

## Chapter 6: Llama Guard + Guardrails AI

1. **Does the 8B change the story?** This ran on Llama Guard 3 **1B**. Pull
   `llama-guard3` (8B) or point at a hosted one, flip
   `with_tool.LLAMA_GUARD_MODEL`, and re-run compare.py. Does the bigger
   model catch any of the 0/3 indirect injections, or is the blind spot the
   *taxonomy*, not the capacity? (Predicted: taxonomy. Verify it.)
2. **Chase the S1 misfire.** Llama Guard labeled two injection attempts as
   "S1, violent crimes." Feed it just those payloads and vary the wording:
   what is it actually tripping on? Is there a rephrase that makes the
   misfire disappear (proving it's not really seeing injection)?
3. **Build the two-layer guard that wins.** No single guard blocked
   everything. Compose the honest production stack: Llama Guard for harmful +
   `llm_guard` for injection + `channel_guard` on the output. Score the
   *combination* (flag if ANY fires) on all 18 cases. Does defense-in-depth
   reach the benign column's 0 false positives, or does stacking guards
   finally block one of the clean five?

## Chapter 7: Langfuse

1. **Make retention the thing you feel.** Run `hand_rolled.py`, close the
   terminal, and now answer "what did request #3 cost?" You can't, the
   stderr is gone. Do the same with `with_tool.py`, then open localhost:3000
   and find it. Then wire the hand-rolled JSONL to a file + `jq` so it *does*
   persist: how much of Langfuse did you just rebuild, and what's still
   missing (UI, sharing, server-side pricing)?
2. **Trust, then verify, the server's pricing.** The server priced the run to
   the digit, on gpt-4o-mini, a model it knows. Point the app at a newer or
   obscure model and re-run: does Langfuse still price it, or does
   `total_cost` come back null the way ch01's hand table did on an unknown
   model? Whose pricing map is more current?
3. **Survive the version churn.** `set_trace_io()` is already deprecated for
   `propagate_attributes()`. Migrate the port off it, set a real `session_id`
   per run, and scope compare.py's query with `session_id=` instead of
   `from_timestamp`. Did the deprecation warning point you at a working
   replacement, or did you have to read the source (LESSONS §10)?
