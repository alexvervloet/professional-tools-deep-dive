# Chapter 3 verdict: LlamaIndex vs the hand-rolled RAG pipeline

Written from real runs on 2026-07-14 (llama-index-core 0.14.23, openai
2.45.0; corpus = the rag dive's four Nimbus Notes docs; eval = the dive's
hit@k/MRR/answer-fact metrics over 12 labelled questions). Reproduce with
`secrun python ch03-llamaindex/compare.py`.

> **Model note (2026-08-08).** These numbers were measured on `gpt-4o-mini`,
> which was this repo's default at the time. The code has since moved to
> `gpt-5.4-nano`, so re-running now will not reproduce these figures exactly.
> The verdict is deliberately left as measured rather than rewritten: the
> comparison it records really happened, on the models named above. What
> should survive a model change is the *shape* of each finding, and checking
> whether it does is a better exercise than trusting a refreshed number.

## Accuracy: a three-way tie, and that's the finding

All three pipelines scored **100% hit rate and ~1.0 MRR and 100%
answer-fact** on the same 12 questions: hand-rolled (12 word-window chunks),
LlamaIndex as it ships (4 whole-doc chunks), and LlamaIndex matched to the
baseline (17 sentence-aware chunks). On a small corpus of well-separated
docs, retrieval quality is bound by the corpus, not the framework: even
2022-era default embeddings ace it. (The rag dive's own authoring lessons
hit this repeatedly: an effect needs a corpus that isolates it. A corpus
where these pipelines *would* separate is bigger, messier, and
near-duplicate-heavy; see the exercises.)

So the honest chapter is not "which retrieves better here"; it's what else
you inherit when you type `VectorStoreIndex.from_documents(docs)`.

## What the defaults actually were (this version, mid-2026)

- **embed_model: text-embedding-ada-002**: OpenAI's 2022 embedder, at
  $0.10/1M tokens: five times the list price of text-embedding-3-small
  ($0.02/1M), and two generations older.
- **llm: gpt-3.5-turbo**: a legacy model ($0.50/$1.50 per 1M vs
  gpt-4o-mini's $0.15/$0.60).
- **SentenceSplitter(1024, 200)**: on ~310-word docs, that's one chunk per
  document: retrieval granularity silently becomes "whole file."
- **similarity_top_k: 2**: the baseline measured its way to k=4.

None of this is a bug; every knob is settable. But the quickstart pipeline
you get without touching them is **2023's stack at higher-than-2026 prices**
and older on both model axes and more expensive on both. The dive's version of
these choices was measured (chunk size in its example 05, k in 09); the
framework's version is whatever the defaults were when that release shipped.
"Defaults chosen by someone else, on a date you don't know" is the unstated
cost of `from_documents()`.

## The property that did separate them: citations

The baseline's grounding contract, every answer cites its sources
survived in **12/12** hand-rolled answers and **0/12** from both LlamaIndex
engines. The default prompt never asks for citations, and the framework's
context assembly isn't numbered, so the baseline's `[n]` contract isn't even
*expressible* in a `text_qa_template` alone; the framework has its own
answer (`CitationQueryEngine`, exercise 3), but you have to know to reach
for it. This is the sharpest lesson in the chapter: **swapping pipelines can
silently drop a product property while every accuracy metric stays green.**
Our eval caught it only because it also captured the answers, not just the
metrics.

Grounding itself held everywhere: on a question the corpus can't answer,
hand-rolled and matched both said "I don't know," and even the gpt-3.5
defaults engine hedged to "not mentioned in the provided context" rather
than inventing. Latency differences were real but small (defaults 1.9s/q vs
matched 1.1s vs hand-rolled 1.3s): the defaults engine is slowest *and*
oldest, which is its own small indictment.

## What the framework actually bought

Not retrieval quality; this corpus couldn't pay that out. What's real: the
reader (four .md files are trivial, but the same line ingests PDFs and
DOCX), a sentence-aware splitter that respects boundaries the baseline's
word-window cuts through, swappable vector-store backends for when
brute-force cosine stops scaling, and an ecosystem of composable pieces
(rerankers, citation engines, metadata filters) the rag dive built by hand
one example at a time. The cost is symmetrical: prompts you didn't write,
context assembly you don't control, and defaults with a vintage.

## The interview sentence

"I ported my from-scratch RAG pipeline to LlamaIndex and evaled both on the
same labelled set: accuracy tied (corpus difficulty, not the framework, was
the constraint) but the port silently dropped my citation contract while
every metric stayed green, and the shipped defaults were a 2022 embedder at
5× the price of the current one. So I treat frameworks as a bag of parts
with a vintage: audit the defaults, and eval product *properties*, not just
retrieval metrics."
