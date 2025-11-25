# llm_client.py

import os
from typing import Optional, Literal

from openai import OpenAI
import ollama  # pip install ollama


BackendLiteral = Literal["openai", "ollama"]

_openai_client: Optional[OpenAI] = None


def get_openai_client() -> OpenAI:
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def call_openai(prompt: str, model: str = "gpt-4.1-mini") -> str:
    client = get_openai_client()
    response = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "You are a friendly assistant for a child-safe social media simulator.",
            },
            {"role": "user", "content": prompt},
        ],
        temperature=0.8,
        max_tokens=120,
    )
    return response.choices[0].message.content.strip()


def call_ollama(prompt: str, model: str = "llama3") -> str:
    """
    Call a local Ollama model via the Python client.
    Assumes the Ollama server is running on localhost.
    """
    # You can tweak temperature, num_predict, etc. via the 'options' dict.
    resp = ollama.chat(
        model=model,
        messages=[
            {"role": "system", "content": "You are a friendly assistant for a child-safe social media simulator."},
            {"role": "user", "content": prompt},
        ],
        options={
            "temperature": 0.8,
        },
    )
    # Ollama returns a dict with 'message' containing 'content'
    return resp["message"]["content"].strip()


def call_llm(
    prompt: str,
    backend: BackendLiteral = "openai",
    model: Optional[str] = None,
) -> str:
    """
    Unified entry point for the rest of the app.

    backend: "openai" or "ollama"
    model: optional model name; if None, use sensible defaults or env vars.
    """
    if backend == "ollama":
        model_name = model or os.environ.get("OLLAMA_MODEL", "llama3")
        return call_ollama(prompt, model=model_name)
    else:
        # default to openai
        model_name = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
        return call_openai(prompt, model=model_name)
