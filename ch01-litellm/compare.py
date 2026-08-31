"""
Chapter 1 measurement: where the two implementations actually differ.

hand_rolled.py and with_tool.py both work. This script measures the seams:

  1. Cost accounting: same request, same token counts. Does LiteLLM's
     maintained pricing map agree with the hand-updated table?
  2. Error surfacing: the same mistake (a model that doesn't exist) through
     the raw SDK vs through the router. What exception do you debug from?
  3. The silent route difference: the same local model through LiteLLM's two
     ollama prefixes vs Ollama's own OpenAI-compat endpoint, on a tool call.

Run it:

    secrun python ch01-litellm/compare.py
"""

import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

import hand_rolled
import with_tool
from litellm import completion

load_dotenv()
if not (os.getenv("OPENAI_API_KEY") and os.getenv("ANTHROPIC_API_KEY")):
    sys.exit("Run via secrun so OPENAI_API_KEY and ANTHROPIC_API_KEY are set (see ../docs/SECRETS.md).")

QUESTION = "In one sentence, what is an LLM gateway?"


print("── 1. Cost accounting: hand table vs litellm map (same run, same tokens)")
MODEL_KEYS = {"openai": hand_rolled.OPENAI_MODEL, "anthropic": hand_rolled.ANTHROPIC_MODEL}
for provider, price_key in MODEL_KEYS.items():
    _, tokens_in, tokens_out, litellm_cost = with_tool.chat(provider, QUESTION)
    hand_cost = hand_rolled.estimate_cost(price_key, tokens_in, tokens_out)
    delta = "agree" if abs(hand_cost - litellm_cost) < 1e-9 else f"DIFFER by ${abs(hand_cost - litellm_cost):.6f}"
    print(f"  {provider:10} {tokens_in:>3} in /{tokens_out:>4} out   "
          f"hand ${hand_cost:.6f}   litellm ${litellm_cost:.6f}   -> {delta}")


print("\n── 2. Error surfacing: ask for a model that doesn't exist")
BAD = "gpt-4o-mini-does-not-exist"


def probe(label: str, fn) -> None:
    try:
        fn()
        print(f"  {label:28} -> no error (?)")
    except Exception as e:
        first_line = str(e).splitlines()[0][:90]
        print(f"  {label:28} -> {type(e).__name__}: {first_line}")


probe("raw SDK", lambda: OpenAI().chat.completions.create(
    model=BAD, messages=[{"role": "user", "content": "hi"}]))
probe("litellm, bare name", lambda: completion(
    model=BAD, messages=[{"role": "user", "content": "hi"}]))
probe("litellm, 'openai/' prefix", lambda: completion(
    model=f"openai/{BAD}", messages=[{"role": "user", "content": "hi"}]))


print("\n── 3. Same local model, three routes, same tool call")
TOOL_PROMPT = "What is the weather in Tokyo?"
print(f"  {'hand-rolled (ollama /v1)':28} -> {hand_rolled.tool_call('ollama', TOOL_PROMPT).strip()[:80]!r}")
for prefix in ("ollama/", "ollama_chat/"):
    with_tool.MODELS["ollama"] = prefix + hand_rolled.OLLAMA_MODEL
    reply = with_tool.tool_call("ollama", TOOL_PROMPT)
    print(f"  {'litellm ' + prefix:28} -> {reply.strip()[:80]!r}")


print("\n── code you maintain (crude, but the shape is right)")
for name in ("hand_rolled.py", "with_tool.py"):
    lines = len(Path(__file__).with_name(name).read_text().splitlines())
    print(f"  {name:16} {lines:>4} lines", end="")
print("   (hand-rolled covers 3 providers; the port's shape is flat in providers)")
