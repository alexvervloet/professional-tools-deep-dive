"""
Chapter 1 baseline — the provider layer you wrote by hand.
==========================================================

This is the from-scratch version, ported (and condensed) from the OpenAI and
Claude API dives. Three capabilities — chat, streaming, tool calling — against
three providers: OpenAI, Anthropic, and a local Ollama model.

Read it before reading with_tool.py, and notice what you're maintaining:

  - TWO SDKs with different message shapes. OpenAI wants tools wrapped in
    {"type": "function", "function": {...}}; Anthropic wants {name,
    description, input_schema} at the top level. The tool-result turn differs
    too (role="tool" vs a user turn carrying tool_result blocks).
  - TWO streaming event shapes (chunk.choices[0].delta.content vs
    content_block_delta events).
  - Ollama rides OpenAI's SDK via its /v1 compatibility endpoint — one shape
    fewer, which is itself a lesson in why everyone converged on that shape.
  - A hand-maintained PRICING table (from the dives' utils/pricing.py) that is
    out of date the day a provider changes a price.

None of this is *hard*. It's ~180 lines and you understand every one. The
question with_tool.py answers is what it costs to make this someone else's
~180 lines (per provider, times every provider they support).

Run it:

    secrun python ch01-litellm/hand_rolled.py
"""

import json
import os
import sys
from dataclasses import dataclass

import anthropic
from dotenv import load_dotenv
from openai import OpenAI

OPENAI_MODEL = "gpt-4o-mini"
ANTHROPIC_MODEL = "claude-haiku-4-5"
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_BASE_URL = "http://localhost:11434/v1"


# --- Pricing: hand-maintained, per the API dives' utils/pricing.py. ---------
# ⚠️ Snapshot as of 2026-07-14; check the providers' pricing pages.
@dataclass(frozen=True)
class ModelPrice:
    input_per_1m: float
    output_per_1m: float


PRICING: dict[str, ModelPrice] = {
    OPENAI_MODEL: ModelPrice(input_per_1m=0.15, output_per_1m=0.60),
    ANTHROPIC_MODEL: ModelPrice(input_per_1m=1.00, output_per_1m=5.00),
    OLLAMA_MODEL: ModelPrice(input_per_1m=0.0, output_per_1m=0.0),  # your electricity
}


def estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    price = PRICING[model]
    return (
        input_tokens / 1_000_000 * price.input_per_1m
        + output_tokens / 1_000_000 * price.output_per_1m
    )


# --- The one tool both providers get offered, in ONE neutral shape. ---------
# Each provider branch below re-dresses it in that provider's required format.
def get_current_weather(city: str) -> str:
    fake_db = {"Paris": "18°C, light rain", "Tokyo": "27°C, sunny"}
    return fake_db.get(city, "unknown")


TOOL_NAME = "get_current_weather"
TOOL_DESCRIPTION = "Get the current weather for a city."
TOOL_PARAMETERS = {
    "type": "object",
    "properties": {"city": {"type": "string", "description": "City name, e.g. Paris"}},
    "required": ["city"],
}


# --- chat: one function, a branch per provider. -----------------------------
def chat(provider: str, prompt: str) -> tuple[str, int, int]:
    """Return (reply_text, input_tokens, output_tokens)."""
    if provider == "openai":
        response = OpenAI().chat.completions.create(
            model=OPENAI_MODEL, messages=[{"role": "user", "content": prompt}]
        )
        usage = response.usage
        assert usage is not None
        return response.choices[0].message.content or "", usage.prompt_tokens, usage.completion_tokens

    if provider == "anthropic":
        response = anthropic.Anthropic().messages.create(
            model=ANTHROPIC_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        text = next((b.text for b in response.content if b.type == "text"), "")
        return text, response.usage.input_tokens, response.usage.output_tokens

    if provider == "ollama":
        response = OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama").chat.completions.create(
            model=OLLAMA_MODEL, messages=[{"role": "user", "content": prompt + " /no_think"}]
        )
        usage = response.usage
        assert usage is not None
        return response.choices[0].message.content or "", usage.prompt_tokens, usage.completion_tokens

    raise ValueError(f"unknown provider: {provider}")


# --- streaming: two different event shapes to learn. ------------------------
def stream(provider: str, prompt: str) -> str:
    """Print tokens as they arrive; return the full text."""
    pieces: list[str] = []

    if provider in ("openai", "ollama"):
        client = (
            OpenAI()
            if provider == "openai"
            else OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        )
        model = OPENAI_MODEL if provider == "openai" else OLLAMA_MODEL
        text = prompt if provider == "openai" else prompt + " /no_think"
        for chunk in client.chat.completions.create(
            model=model, messages=[{"role": "user", "content": text}], stream=True
        ):
            delta = chunk.choices[0].delta.content if chunk.choices else None
            if delta:
                pieces.append(delta)
                print(delta, end="", flush=True)

    elif provider == "anthropic":
        with anthropic.Anthropic().messages.stream(
            model=ANTHROPIC_MODEL,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        ) as events:
            for delta in events.text_stream:
                pieces.append(delta)
                print(delta, end="", flush=True)
    else:
        raise ValueError(f"unknown provider: {provider}")

    print()
    return "".join(pieces)


# --- tool calling: the shapes really diverge here. ---------------------------
def tool_call(provider: str, prompt: str) -> str:
    """Run the full ask → tool_use → tool_result → answer dance."""
    if provider in ("openai", "ollama"):
        client = (
            OpenAI()
            if provider == "openai"
            else OpenAI(base_url=OLLAMA_BASE_URL, api_key="ollama")
        )
        model = OPENAI_MODEL if provider == "openai" else OLLAMA_MODEL
        tools = [{
            "type": "function",
            "function": {
                "name": TOOL_NAME,
                "description": TOOL_DESCRIPTION,
                "parameters": TOOL_PARAMETERS,
            },
        }]
        messages = [{"role": "user", "content": prompt}]
        first = client.chat.completions.create(model=model, messages=messages, tools=tools)
        call = (first.choices[0].message.tool_calls or [None])[0]
        if call is None:
            return first.choices[0].message.content or ""
        result = get_current_weather(**json.loads(call.function.arguments))
        messages.append(first.choices[0].message)  # the assistant turn with the call
        messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
        second = client.chat.completions.create(model=model, messages=messages, tools=tools)
        return second.choices[0].message.content or ""

    if provider == "anthropic":
        client = anthropic.Anthropic()
        tools = [{
            "name": TOOL_NAME,
            "description": TOOL_DESCRIPTION,
            "input_schema": TOOL_PARAMETERS,
        }]
        messages = [{"role": "user", "content": prompt}]
        first = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=512, tools=tools, messages=messages
        )
        block = next((b for b in first.content if b.type == "tool_use"), None)
        if block is None:
            return next((b.text for b in first.content if b.type == "text"), "")
        result = get_current_weather(**block.input)  # type: ignore[arg-type]
        messages.append({"role": "assistant", "content": first.content})
        messages.append({
            "role": "user",
            "content": [{"type": "tool_result", "tool_use_id": block.id, "content": result}],
        })
        second = client.messages.create(
            model=ANTHROPIC_MODEL, max_tokens=512, tools=tools, messages=messages
        )
        return next((b.text for b in second.content if b.type == "text"), "")

    raise ValueError(f"unknown provider: {provider}")


if __name__ == "__main__":
    load_dotenv()
    if not (os.getenv("OPENAI_API_KEY") and os.getenv("ANTHROPIC_API_KEY")):
        sys.exit("Run via secrun so OPENAI_API_KEY and ANTHROPIC_API_KEY are set (see SECRETS.md).")

    question = "In one sentence, what is an LLM gateway?"
    for provider in ("openai", "anthropic", "ollama"):
        print(f"\n=== {provider} ===")
        reply, tokens_in, tokens_out = chat(provider, question)
        model = {"openai": OPENAI_MODEL, "anthropic": ANTHROPIC_MODEL, "ollama": OLLAMA_MODEL}[provider]
        cost = estimate_cost(model, tokens_in, tokens_out)
        print(f"[chat] {reply.strip()}")
        print(f"[usage] {tokens_in} in / {tokens_out} out  -> ${cost:.6f} (hand table)")
        print("[stream] ", end="")
        stream(provider, "Count from 1 to 5, digits only.")
        print(f"[tool] {tool_call(provider, 'What is the weather in Tokyo?').strip()}")
