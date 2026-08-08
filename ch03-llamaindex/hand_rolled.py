"""
Chapter 3 baseline: the rag dive's pipeline, condensed into one file.

Chunk -> embed -> cosine search -> grounded prompt -> cite. Ported from
rag-deep-dive's `rag/` package (chunking.py, store.py, pipeline.py,
providers.py), OpenAI stack only, so the whole baseline is readable in one
sitting: a 120-word sliding window with 20 words of overlap,
text-embedding-3-small, brute-force cosine over a few dozen vectors, and the
grounding system prompt that forbids outside knowledge and demands [n]
citations.

Every default here is one YOU chose, and the rag dive measured: chunk size
(its example 05), k (example 09), the prompt (example 04). Keep that in mind
reading with_tool.py, where every one of these knobs still exists, but
someone else chose the starting values.

Run it:

    secrun python ch03-llamaindex/hand_rolled.py
"""

import math
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

EMBED_MODEL = "text-embedding-3-small"
CHAT_MODEL = "gpt-5.4-nano"
CHUNK_WORDS = 120
OVERLAP_WORDS = 20
K = 4

CORPUS_DIR = Path(__file__).parent / "corpus"

GROUNDED_SYSTEM = (
    "You answer questions using ONLY the numbered context provided in the user "
    "message. Cite the sources you use with bracketed numbers like [1] or [2]. "
    "If the context does not contain the answer, say you don't know. Do not "
    "guess or rely on outside knowledge."
)


def chunk_text(text: str, chunk_size: int = CHUNK_WORDS, overlap: int = OVERLAP_WORDS) -> list[str]:
    """Sliding word-window, as in rag-deep-dive rag/chunking.py."""
    words = text.split()
    if not words:
        return []
    step = chunk_size - overlap
    chunks, start = [], 0
    while start < len(words):
        chunks.append(" ".join(words[start : start + chunk_size]))
        if start + chunk_size >= len(words):
            break
        start += step
    return chunks


@dataclass
class Record:
    text: str
    source: str
    vector: list[float]


class Store:
    """Brute-force cosine store, as in rag-deep-dive rag/store.py."""

    def __init__(self) -> None:
        self.records: list[Record] = []

    def search(self, query_vector: list[float], k: int) -> list[tuple[float, Record]]:
        def cosine(a: list[float], b: list[float]) -> float:
            dot = sum(x * y for x, y in zip(a, b))
            return dot / (math.sqrt(sum(x * x for x in a)) * math.sqrt(sum(x * x for x in b)))

        scored = [(cosine(query_vector, r.vector), r) for r in self.records]
        return sorted(scored, key=lambda pair: pair[0], reverse=True)[:k]


def build_store(client: OpenAI) -> Store:
    texts: list[str] = []
    sources: list[str] = []
    for path in sorted(CORPUS_DIR.glob("*.md")):
        for chunk in chunk_text(path.read_text()):
            texts.append(chunk)
            sources.append(path.name)
    response = client.embeddings.create(model=EMBED_MODEL, input=texts)
    store = Store()
    for text, source, item in zip(texts, sources, response.data):
        store.records.append(Record(text, source, item.embedding))
    return store


def retrieve_sources(client: OpenAI, store: Store, question: str, k: int = K) -> list[str]:
    vec = client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    return [record.source for _score, record in store.search(vec, k)]


def answer(client: OpenAI, store: Store, question: str, k: int = K) -> str:
    vec = client.embeddings.create(model=EMBED_MODEL, input=[question]).data[0].embedding
    hits = store.search(vec, k)
    blocks = [
        f"[{n}] (source: {record.source})\n{record.text}"
        for n, (_score, record) in enumerate(hits, start=1)
    ]
    prompt = "Context:\n" + "\n\n".join(blocks) + f"\n\nQuestion: {question}"
    response = client.chat.completions.create(
        model=CHAT_MODEL,
        max_completion_tokens=512,
        messages=[
            {"role": "system", "content": GROUNDED_SYSTEM},
            {"role": "user", "content": prompt},
        ],
    )
    return response.choices[0].message.content or ""


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    client = OpenAI()
    store = build_store(client)
    print(f"{len(store.records)} chunks from {CORPUS_DIR}")
    question = "How long are deleted notes kept?"
    print(f"Q: {question}\nA: {answer(client, store, question)}")
