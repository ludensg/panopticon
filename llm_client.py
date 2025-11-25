# llm_client.py

import os
from typing import Optional

from openai import OpenAI


# You must set OPENAI_API_KEY in your environment
# e.g. `export OPENAI_API_KEY="sk-..."` in your shell
_client: Optional[OpenAI] = None


def get_client() -> OpenAI:
    global _client
    if _client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment.")
        _client = OpenAI(api_key=api_key)
    return _client


def call_llm(prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    Simple wrapper around OpenAI chat completion.
    If you want to mock during development, stub this function.
    """
    client = get_client()

    response = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": "You are a friendly assistant for a child-safe social media simulator."},
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()
