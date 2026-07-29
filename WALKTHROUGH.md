# WALKTHROUGH

A guided tour of the journey through this repo, end to end. The [README](README.md)
tells you what to run and the [TEXTBOOK](TEXTBOOK.md) explains the ideas; this
file is the travelogue. It walks the seven chapters in order, and for each one it
names the fork in the road (where you can branch off and try something else), the
gotcha that will trip you (drawn from actually building it, not from the happy
path), and the best and worst case for reaching for that tool.

If you read one thing before starting, read this. It is the map with the potholes
marked.

---

## How to travel

**Prerequisite.** This is a "volume 2." Each chapter compares a professional tool
against a primitive you built from scratch in an earlier dive. You do not have to
have done every earlier dive, but you should be able to read the final artifact of
the matching one comfortably, because the whole teaching device is the comparison
against something you understand.

**One-time setup, and the four things that gate a chapter:**

1. **A virtual environment and the pins.** `python -m venv .venv`, then
   `pip install -r requirements.txt`. The requirements file is hard-pinned on
   purpose; the pins encode the exact versions each verdict is true of. Installing
   them cleanly on a fresh box is the one thing CI checks, because this repo's
   subject is dependency churn and that is the thing that churns.
2. **API keys, via `secrun`.** Keys live in the macOS Keychain and are injected by
   the `secrun` wrapper, never in a `.env` or your shell. Every runnable script is
   launched as `secrun python <path>`. A script that needs a key and does not get
   one exits loudly rather than guessing.
3. **Ollama, for the local-model halves.** Chapters 1, 2, and 6 run against a local
   model through Ollama. Chapter 6 needs `llama-guard3` specifically (see its
   gotcha below; it is the heavy download of the repo).
4. **Docker, for chapter 7 only.** Langfuse is self-hosted as six containers. You
   do not need it for any other chapter.

**The rhythm of a chapter.** Each chapter folder holds the same four files, and the
honest way through is to run them in this order:

- read the header docstring of `hand_rolled.py`, then run it (the primitive, the
  baseline you already understand),
- read and run `with_tool.py` (the professional tool doing the same job),
- run `compare.py` (the measurement: the same eval against both),
- read `VERDICT.md` (what the numbers meant), then try an exercise from
  [EXERCISES.md](EXERCISES.md).

The verdict is written last for a reason. Do not read it first; the point is to see
the numbers before you are told what they say.

**A standing caveat.** This repo rots faster than most by design. Frameworks rename
modules and change APIs between minor versions, and several gotchas below are
already stale in the good way (the fix is in the code). Treat the concepts in each
verdict as current and the exact version behavior as a snapshot. Before trusting a
tool choice in a later year, re-run the landscape check.

---

## Chapter 1: LiteLLM (the provider layer)

**The journey.** You take the hand-rolled provider layer (two SDKs, two message
shapes, two streaming event shapes, a hand-maintained pricing table) and replace it
with one router that speaks to every provider through the OpenAI shape. Chat,
streaming, and a full tool-call round trip, across OpenAI, Anthropic, and local
Ollama.

**The fork.** Add a fourth provider to both sides and count the lines it costs each.
Any OpenAI-compatible runner works. Then exercise fallbacks: point at a model that
does not exist and let the router fall through to one that does.

**The gotcha.** Two of them, and both are the abstraction tax in miniature. First,
the moment you pass `tools=` to `completion()`, LiteLLM imports `fastapi` and then
`orjson` as undeclared dependencies (via an MCP proxy handler), so a plain SDK call
crashes until you install packages the router never told you it needed. They are
pinned in requirements.txt with a comment for exactly this reason. Second, and
nastier: the model prefix is a code path, not just a provider label.
`ollama_chat/qwen3:8b` completes a tool call; `ollama/qwen3:8b` returns an **empty
string** for the final turn, with no error and no warning, because the two prefixes
route through different translation code inside the router. You debug that by
reading LiteLLM's source, not yours.

**Best case.** Many providers, a real fallback policy, and pricing upkeep you should
not own. The router maintains the per-provider translation and the price map for
about a hundred providers; that is the whole product and it is worth it.

**Worst case.** Two providers you control and a hard need to see raw provider errors.
The router wraps a provider's clean 404 in its own exception type, or fails to route
before any request is made with a message that does not mention your typo. A thin
hand-rolled wrapper is more debuggable there, and it cannot fail to import itself.

---

## Chapter 2: Instructor (structured extraction)

**The journey.** You take the schema-in-the-prompt plus parse-and-retry loop and
rebuild it three ways: hand-rolled, Instructor, and the provider's own native
structured-output mode. Five job postings, each carrying a trap (an hourly rate that
must not become an annual salary, a hybrid role that is not remote, a date written
out in Norwegian prose), run twice each on a frontier mini model and a local 8B.

**The fork.** Add a deeply nested field or a cross-field rule (`salary_min <=
salary_max`) that constrained decoding cannot express, and watch which approach
still holds. Or price the three approaches per thousand postings with chapter 1's
cost tools.

**The gotcha.** The problem this tool was built for has mostly closed. All sixty
extractions succeeded, across all three approaches and both models, with every
semantic trap handled. The 2023 pitch ("models emit broken JSON, you need
machinery") does not reproduce on current models for a flat-ish schema. So do not
adopt Instructor for reliability you no longer lack; adopt it for portability and
for retries on constraints a decoder cannot check. Also measured: native
constrained decoding is the fastest option on the provider's own hardware and the
**slowest by 2x** on a local runtime, because the schema guarantee is paid for in
grammar-constrained sampling speed.

**Best case.** Multi-provider structured extraction where you want one code path and
retained retries for validation rules the decoder cannot enforce.

**Worst case.** A single provider and a simple flat schema. The provider's native
mode is zero extra dependencies and, on its own hardware, the fastest and strongest
guarantee. (Keep an eye on BAML as the rising schema-first alternative, but nothing
here creates a problem it would solve for a single-service Python stack.)

---

## Chapter 3: LlamaIndex (the RAG pipeline)

**The journey.** You take the from-scratch chunk, embed, retrieve, cite pipeline and
rebuild it with LlamaIndex twice: once exactly as it ships, once with every exposed
knob set to your baseline's values. All three are scored by the same twelve-question
eval on the same corpus.

**The fork.** The three pipelines tie at a perfect score here, so make them diverge:
add near-duplicate documents that differ only in one number, and watch which
pipeline retrieves the wrong one. Or swap in `CitationQueryEngine` and see if it
wins the citations back (see the gotcha). Or price the defaults with chapter 1's
tools.

**The gotcha.** Two, and both are about what you inherit silently. First, the
defaults have a vintage: installed fresh in 2026, LlamaIndex still defaulted to a
2022 embedding model at five times the current price, a legacy chat model,
1024-token chunks (one chunk per whole document on this corpus), and k=2. Nothing is
broken; the one-liner from the README is just a two-year-old stack at above-market
prices, so audit the defaults. Second, and sharper: the port matched every metric
and **silently stopped citing its sources** (twelve of twelve answers cited before,
zero of twelve after), because the default prompt never asks for a citation and the
framework's context assembly is not numbered. The only reason it was caught is that
the eval captured the raw answers, not just the scores.

**Best case.** Heterogeneous ingestion (PDFs, DOCX, tables), swappable vector-store
backends when brute-force cosine stops scaling, and a bag of composable parts
(rerankers, citation engines, metadata filters) you would otherwise build one at a
time.

**Worst case.** A small, clean corpus your hand pipeline already nails, especially
when you have a product contract (like citations) that the defaults do not express.
You will match the metrics and lose the contract.

---

## Chapter 4: DeepEval (the eval harness and gate)

**The journey.** You take the evals dive's faithfulness judge plus threshold gate and
re-express it two ways: your one-call LLM judge, and DeepEval's multi-step
`FaithfulnessMetric`, both scoring the same eight answers (generated once and
committed to a file) with the same judge model. Then the gate becomes a real pytest
suite, which is what DeepEval is actually for.

**The fork.** Close the definition gap with a GEval metric that takes your own
criteria text and see if the pure invention fails now. Or loop the pytest gate ten
times and measure the real flake rate. Or cross-check with Ragas.

**The gotcha.** Three. First, on install: DeepEval requires `click<8.4` while another
pinned library requires `click>=8.4.2`, an unsatisfiable pair resolved only by
holding `huggingface-hub` back a minor version (documented in requirements.txt).
Second, the metric is not your metric: DeepEval's faithfulness means absence of
contradiction, so it passed a pure hallucination ("password-reset links are valid
for 24 hours," over a context silent on expiry) with a perfect score on every run,
while your rubric means every claim must be supported. The name matched your intent;
the behavior did not. Third, the per-case pytest gate **flipped its verdict across
reruns on the exact same committed inputs** (three of four tests failed one run, all
passed the next), because the multi-step judge pipeline has more places to wobble.
Also: telemetry is on by default; opt out.

**Best case.** You want many maintained metrics, pytest and CI integration with no
runner code of your own, dataset tooling, and a written reason attached to every
score.

**Worst case.** You need a specific rubric the built-in metric does not share, or a
stable gate on a small number of cases. A one-call judge you wrote is easier to pin
to your definition and returned the same numbers every run. Threshold the mean across
cases, not each case, if you want the gate to stop flaking.

---

## Chapter 5: LangGraph (the agent loop)

**The journey.** You take the hand-written agent loop and rebuild it on LangGraph's
prebuilt agent, same three tools, same five-task eval (multi-step math, a knowledge
lookup, a two-tool composition, a denied save, a no-tool question).

**The fork.** The two implementations tie 10/10, so go find where they diverge. Split
the human-in-the-loop demo into two real processes with a SQLite checkpointer, so one
exits mid-task and the other resumes from disk. Or give both an impossible task and
compare how many model calls each burns before giving up.

**The gotcha.** The churn arrives while you build. On its first run the port prints a
deprecation: `create_react_agent` has moved to `langchain.agents` (a different
package, one this environment does not even have installed), deprecated in v1.0 for
removal in v2.0. The canonical way to build the canonical agent changed packages
between the tutorials everyone learned from and the version pinned here. Also, the
approval gate is real infrastructure, not a callback: LangGraph's `interrupt()`
stops the graph, checkpoints state, and resumes on a second invocation, which needs a
checkpointer, a thread id, and a resume loop even for the demo. And note that the
`MemorySaver` you get out of the box is in-memory, so it demonstrates the shape of
checkpointing while being unable to survive the process death the feature exists for;
cross-process resume needs a separate package.

**Best case.** You need what the tie did not test: durable checkpoint and resume
across processes, long-lived human approvals, streaming node-by-node events, or
multi-agent graphs with shared state. Those are why the enterprise deployment lists
are real.

**Worst case.** A short, single-process, tool-using task. A 60-line loop ties it on
every measured axis, is debuggable with a print statement, and does not deprecate its
own entry point while you are writing the comparison.

---

## Chapter 6: Llama Guard + Guardrails AI (the guardrails)

**The journey.** You take the prompt-injection dive's detectors (a heuristic, an LLM
intent guard, and a structural channel guard) and score them against two managed
tools: Llama Guard 3 (a local safety classifier via Ollama) and Guardrails AI (a
validator framework). Eighteen cases across four families: direct injection, indirect
injection, genuinely harmful requests, and benign controls.

**The fork.** Pull the 8B Llama Guard instead of the 1B and see whether the extra
capacity catches any injection, or whether the blind spot is the taxonomy, not the
size (it is the taxonomy). Or build the defense-in-depth stack that actually wins:
Llama Guard for harmful content, the LLM guard for injection, the channel guard on
the output.

**The gotcha.** This is the chapter where the journey itself is the lesson. First, the
download: the 8B `llama-guard3` blob would not finalize on the network across several
attempts (it stalled mid-blob, at a fixed byte offset, while the registry answered
fine), so the chapter runs on `llama-guard3:1b`, which did finalize on a later retry.
Budget for the heavy pull, and know it can stall. Second, and more important than any
tool: **an unavailable tool is not a measurement.** The first version of `compare.py`
caught the "model not found" exception and recorded "did not flag," which would have
printed a clean, authoritative row reading "Llama Guard detected zero of thirteen
attacks," a fabricated finding that happened to agree with the prediction. The harness
now drops any unreachable guard with a loud banner instead of scoring it as a miss.
Third, Guardrails AI's much-cited validator Hub is account-gated (`guardrails hub
install` returns 401 without a token), so the chapter ships a custom validator on the
keyless path.

**Best case.** Llama Guard for harmful-content moderation: local, fast, a stable
auditable taxonomy, no per-call frontier bill, and zero false positives here. That is
its lane and it owns it. Guardrails AI for validation scaffolding (declarative guards,
on_fail policies, reask flows) if you will feed it your own validators.

**Worst case.** Either one for prompt-injection defense. Llama Guard scored zero on the
indirect attacks, including the phishing line, because its taxonomy has no cell for
"overrode the system prompt," and Guardrails AI's wrapped regex detected identically
to the bare regex it wrapped. For injection you want the dive's stack: an intent
detector plus the structural output check, in depth.

---

## Chapter 7: Langfuse (observability)

**The journey.** You take the production dive's hand-rolled tracer (trace id, spans,
one JSON line per request to stderr) and send the same request path to a self-hosted
Langfuse instead. Then you query the traces back and ask one operational question of
each side: what did we spend, what is p95, how many were blocked?

**The fork.** Feel the difference retention makes: run the hand-rolled version, close
the terminal, and try to answer "what did request three cost?" (you cannot; it is
gone). Do the same with Langfuse and find it in the UI. Or verify the server's pricing
on a model it does not know and see if `total_cost` comes back null the way the
hand-rolled table did on an unknown model.

**The gotcha.** The infrastructure fights back. The self-host compose binds Postgres
to host port 5432 and Redis to 6379, both commonly already owned by local services, so
the stack will not start until you remap those host ports (Langfuse reaches them over
its internal network, so only the web port on 3000 actually needs the host). The SDK's
API had also moved: the `start_as_current_span` and `update_current_trace` calls a 2024
tutorial teaches are gone, replaced by `start_as_current_observation(as_type=...)`, and
`set_trace_io()` is already deprecated on a fresh install. Verify the SDK's methods
against the installed version rather than a blog post. And, as in chapter 6, the port
calls `auth_check()` and exits loudly rather than pretend traces landed on a server
that is not there.

**Best case.** A team running a service for real users. The moment more than one person
needs to see production traces, "grep my stderr" stops being an answer, and persistence,
a query API, a UI, sharing, and server-side pricing (Langfuse priced a run to the exact
cent from token counts alone, using its own model-price map) stop being luxuries. This
is the chapter where the tool most clearly earns its keep.

**Worst case.** A script, a solo developer, a batch job, or an air-gapped box. Structured
JSON to stderr piped to `jq` answers every question a single operator has, at zero
infrastructure and with nothing leaving the machine. Six always-on containers and a copy
of your traces in a schema you do not own is a steep price for a `print` you could have
kept.

---

## The gotchas, in one place

If you skim nothing else, these are the traps most likely to cost you an afternoon:

- **The pins are load-bearing.** Do not float the versions. Chapter 4's `click` versus
  `huggingface-hub` conflict and chapter 1's undeclared `fastapi` and `orjson` are both
  encoded as pins with comments. A clean `pip install -r requirements.txt` on a fresh
  box is the CI check for a reason.
- **A model name is often a code path.** LiteLLM's `ollama/` versus `ollama_chat/`
  changes behavior, not just routing, and one form fails silently.
- **The metric or guard you import brings its own definition.** DeepEval's faithfulness
  and Llama Guard's taxonomy are not your rubric. Read what they compute before you gate
  on them.
- **A tool can break a product property while every metric stays green.** LlamaIndex
  dropped citations behind a passing eval. Capture your outputs and assert on properties,
  not just aggregate scores.
- **An unavailable tool is not a measurement.** If a model will not download or a server
  is down, the harness must fail loudly, never record a quiet zero that looks like a real
  result and, worse, may agree with what you expected.
- **The canonical API may have moved.** LangGraph's agent entry point and Langfuse's span
  calls both changed. Verify against the installed version, not a tutorial.
- **Local infrastructure is heavy and grabby.** The Llama Guard pull is large and can
  stall; the Langfuse stack is six containers that want ports your machine may already be
  using.

---

## Best and worst fit, at a glance

| Chapter | Reach for the tool when | Hand-roll (or stay native) when |
|---------|-------------------------|----------------------------------|
| 1 LiteLLM | many providers, fallbacks, pricing upkeep | two providers you control; you need raw provider errors |
| 2 Instructor | multi-provider extraction, retries for uncheckable constraints | single provider, simple schema (native mode wins) |
| 3 LlamaIndex | mixed document types, swappable stores, composable retrievers | small clean corpus with a contract the defaults drop |
| 4 DeepEval | many metrics, pytest/CI, reasons per score | a specific rubric, or a stable gate on few cases |
| 5 LangGraph | durable resume, streaming, multi-agent graphs | short single-process tasks |
| 6 Llama Guard / Guardrails AI | harmful-content moderation; validation scaffolding | prompt-injection defense (use defense-in-depth) |
| 7 Langfuse | a team needs shared, persistent, queryable traces | a script, solo dev, or air-gapped box |

The through-line, if you want one sentence to carry out: adopting a tool is an
experiment, not a preference, and the answer is only trustworthy if you hold everything
but the tool still, refuse to let the tool's absence or its vocabulary stand in for a
result, and name what it adds down to the digit. Every fork, gotcha, and verdict above
is that one idea, walked seven times.
