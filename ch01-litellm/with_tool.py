"""
Chapter 1 port: the same provider layer through LiteLLM.

Same three capabilities as hand_rolled.py: chat, streaming, tool calling
same three providers. One request shape (OpenAI's), one response shape, for
everything. The provider branch you maintained by hand is now a model-name
prefix: "gpt-5.4-nano" vs "anthropic/claude-haiku-4-5" vs "ollama/qwen3:8b".

What LiteLLM does internally is exactly what hand_rolled.py does:
re-dressing your OpenAI-shaped request in each provider's required format and
translating the response back. You wrote that translation once for two
providers; LiteLLM maintains it for ~100. That's the whole product.

Also here, because they come with the router "for free":
  - completion_cost(): cost from LiteLLM's maintained pricing map, the
    hand-updated PRICING table in hand_rolled.py, as someone else's problem.
  - fallbacks: one kwarg to retry a request on a different provider when the
    first one fails. compare.py measures what this actually does to errors.

Run it:

    secrun python ch01-litellm/with_tool.py
"""

import json
import os
import sys

from dotenv import load_dotenv

import litellm
from litellm import completion, completion_cost

litellm.suppress_debug_info = True  # keep example output readable

MODELS = {
    "openai": "gpt-5.4-nano",
    "anthropic": "anthropic/claude-haiku-4-5",
    # NOT "ollama/qwen3:8b": that prefix routes through Ollama's generate API,
    # and the final turn of a tool call comes back as an EMPTY STRING: no
    # error, no warning (measured; see VERDICT.md). The prefix picks a code
    # path, not just a provider.
    "ollama": "ollama_chat/qwen3:8b",
}


def get_current_weather(city: str) -> str:
    fake_db = {"Paris": "18°C, light rain", "Tokyo": "27°C, sunny"}
    return fake_db.get(city, "unknown")


# One tool definition, OpenAI's shape, for every provider: LiteLLM translates.
TOOLS = [{
    "type": "function",
    "function": {
        "name": "get_current_weather",
        "description": "Get the current weather for a city.",
        "parameters": {
            "type": "object",
            "properties": {"city": {"type": "string", "description": "City name, e.g. Paris"}},
            "required": ["city"],
        },
    },
}]


def chat(provider: str, prompt: str) -> tuple[str, int, int, float]:
    """Return (reply_text, input_tokens, output_tokens, litellm_cost_usd)."""
    if provider == "ollama":
        prompt += " /no_think"
    response = completion(
        model=MODELS[provider], messages=[{"role": "user", "content": prompt}]
    )
    usage = response.usage
    cost = completion_cost(completion_response=response)
    return (
        response.choices[0].message.content or "",
        usage.prompt_tokens,
        usage.completion_tokens,
        cost,
    )


def stream(provider: str, prompt: str) -> str:
    """One event shape for every provider."""
    if provider == "ollama":
        prompt += " /no_think"
    pieces: list[str] = []
    for chunk in completion(
        model=MODELS[provider], messages=[{"role": "user", "content": prompt}], stream=True
    ):
        delta = chunk.choices[0].delta.content if chunk.choices else None
        if delta:
            pieces.append(delta)
            print(delta, end="", flush=True)
    print()
    return "".join(pieces)


def tool_call(provider: str, prompt: str) -> str:
    """The same dance as hand_rolled.py, but one code path for all providers."""
    messages = [{"role": "user", "content": prompt}]
    first = completion(model=MODELS[provider], messages=messages, tools=TOOLS)
    call = (first.choices[0].message.tool_calls or [None])[0]
    if call is None:
        return first.choices[0].message.content or ""
    result = get_current_weather(**json.loads(call.function.arguments))
    messages.append(first.choices[0].message.model_dump(exclude_none=True))
    messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
    second = completion(model=MODELS[provider], messages=messages, tools=TOOLS)
    return second.choices[0].message.content or ""


def chat_with_fallback(prompt: str) -> tuple[str, str]:
    """Ask a model that doesn't exist; let LiteLLM fall back to one that does.

    Returns (model_that_answered, reply). The point compare.py probes: what
    happened to the *error* from the first model? (Answer: you never see it
    unless you go looking; convenience and opacity are the same feature.)
    """
    response = completion(
        model="gpt-4o-mini-does-not-exist",
        messages=[{"role": "user", "content": prompt}],
        fallbacks=[MODELS["anthropic"]],
    )
    return response.model, response.choices[0].message.content or ""


if __name__ == "__main__":
    load_dotenv()
    if not (os.getenv("OPENAI_API_KEY") and os.getenv("ANTHROPIC_API_KEY")):
        sys.exit("Run via secrun so OPENAI_API_KEY and ANTHROPIC_API_KEY are set (see ../docs/SECRETS.md).")

    question = "In one sentence, what is an LLM gateway?"
    for provider in ("openai", "anthropic", "ollama"):
        print(f"\n=== {provider} ({MODELS[provider]}) ===")
        reply, tokens_in, tokens_out, cost = chat(provider, question)
        print(f"[chat] {reply.strip()}")
        print(f"[usage] {tokens_in} in / {tokens_out} out  -> ${cost:.6f} (litellm map)")
        print("[stream] ", end="")
        stream(provider, "Count from 1 to 5, digits only.")
        print(f"[tool] {tool_call(provider, 'What is the weather in Tokyo?').strip()}")

    print("\n=== fallback (nonexistent model -> anthropic) ===")
    model, reply = chat_with_fallback(question)
    print(f"[answered by] {model}")
    print(f"[reply] {reply.strip()}")
