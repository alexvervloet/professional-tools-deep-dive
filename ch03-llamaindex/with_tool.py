"""
Chapter 3 port — the same RAG through LlamaIndex, twice.
========================================================

Two builds on the same corpus, because "use the framework" hides a decision:

  - build_default(): LlamaIndex exactly as it ships. Reader, splitter, embed
    model, LLM, top-k, prompt — every knob on the value someone at LlamaIndex
    chose. The rag dive chose OUR values by measuring (chunk size in its
    example 05, k in 09); this engine is what you get when you don't.
    __main__ prints what those defaults actually are on this version.
  - build_matched(): the same knobs turned to the baseline's values wherever
    the framework exposes them — text-embedding-3-small, gpt-4o-mini,
    similarity_top_k=4, a grounding prompt, and a SentenceSplitter sized to
    approximate the baseline's 120-word window (~160 tokens). Two honest
    mismatches remain: the splitter is sentence-aware (the baseline's window
    cuts mid-sentence), and LlamaIndex assembles context its own way, without
    the baseline's numbered [n] blocks. That residue is the framework.

Both return the same two callables the eval scores, so compare.py treats all
pipelines identically.

Run it:

    secrun python ch03-llamaindex/with_tool.py
"""

import os
import sys
from pathlib import Path
from typing import Callable

from dotenv import load_dotenv
from llama_index.core import PromptTemplate, Settings, SimpleDirectoryReader, VectorStoreIndex
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.openai import OpenAIEmbedding
from llama_index.llms.openai import OpenAI as LlamaOpenAI

CORPUS_DIR = Path(__file__).parent / "corpus"

# The baseline's grounding discipline, restated in LlamaIndex's template
# variables. LlamaIndex numbers nothing, so [n] citations become "name the
# source file" — the closest expressible equivalent.
GROUNDED_QA_TEMPLATE = PromptTemplate(
    "Context information is below.\n"
    "---------------------\n{context_str}\n---------------------\n"
    "Answer the question using ONLY the context above. If the context does "
    "not contain the answer, say you don't know — do not guess or rely on "
    "outside knowledge.\nQuestion: {query_str}\nAnswer: "
)

Pipeline = tuple[Callable[[str], list[str]], Callable[[str], str], int]  # + chunk count


def _wrap(index: VectorStoreIndex, k: int | None, template: PromptTemplate | None) -> Pipeline:
    retriever = index.as_retriever(**({"similarity_top_k": k} if k else {}))
    kwargs = {}
    if k:
        kwargs["similarity_top_k"] = k
    if template:
        kwargs["text_qa_template"] = template
    engine = index.as_query_engine(**kwargs)

    def retrieve_sources(question: str) -> list[str]:
        return [node.metadata.get("file_name", "?") for node in retriever.retrieve(question)]

    def answer(question: str) -> str:
        return str(engine.query(question))

    return retrieve_sources, answer


def build_default() -> Pipeline:
    """LlamaIndex as it ships: no knob touched, including k and the prompt."""
    documents = SimpleDirectoryReader(str(CORPUS_DIR)).load_data()
    index = VectorStoreIndex.from_documents(documents)
    retrieve_sources, answer = _wrap(index, k=None, template=None)
    return retrieve_sources, answer, len(index.docstore.docs)


def build_matched() -> Pipeline:
    """Every knob the framework exposes, set to the baseline's value."""
    documents = SimpleDirectoryReader(str(CORPUS_DIR)).load_data()
    index = VectorStoreIndex.from_documents(
        documents,
        embed_model=OpenAIEmbedding(model="text-embedding-3-small"),
        transformations=[SentenceSplitter(chunk_size=160, chunk_overlap=27)],
    )
    # LLM must ride the query engine, not the index.
    retriever_fn, _ = _wrap(index, k=4, template=GROUNDED_QA_TEMPLATE)
    engine = index.as_query_engine(
        llm=LlamaOpenAI(model="gpt-4o-mini"),
        similarity_top_k=4,
        text_qa_template=GROUNDED_QA_TEMPLATE,
    )
    return retriever_fn, lambda question: str(engine.query(question)), len(index.docstore.docs)


def describe_defaults() -> dict[str, object]:
    """What this llama-index version decided for you (printed by compare.py)."""
    splitter = Settings.node_parser
    return {
        "embed_model": getattr(Settings.embed_model, "model_name", type(Settings.embed_model).__name__),
        "llm": getattr(Settings.llm, "model", type(Settings.llm).__name__),
        "splitter": f"{type(splitter).__name__}(chunk_size={getattr(splitter, 'chunk_size', '?')}, "
                    f"chunk_overlap={getattr(splitter, 'chunk_overlap', '?')})",
        "retriever_top_k": VectorStoreIndex.from_documents(
            SimpleDirectoryReader(str(CORPUS_DIR)).load_data()
        ).as_retriever().similarity_top_k,
    }


if __name__ == "__main__":
    load_dotenv()
    if not os.getenv("OPENAI_API_KEY"):
        sys.exit("Run via secrun so OPENAI_API_KEY is set (see SECRETS.md).")
    print("LlamaIndex's defaults on this version:")
    for key, value in describe_defaults().items():
        print(f"  {key}: {value}")
    retrieve_sources, answer, n_chunks = build_default()
    question = "How long are deleted notes kept?"
    print(f"\n[default engine, {n_chunks} chunks] Q: {question}")
    print(f"  sources: {retrieve_sources(question)}")
    print(f"  A: {answer(question)}")
