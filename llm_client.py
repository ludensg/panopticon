import os
from typing import Optional, Literal

from openai import OpenAI
import ollama
from ollama import Client  # type: ignore

BackendLiteral = Literal["openai", "ollama"]

_openai_client: Optional[OpenAI] = None
_ollama_client: Optional[Client] = None


def get_openai_client() -> OpenAI:
    """
    Lazily construct a singleton OpenAI client.
    """
    global _openai_client
    if _openai_client is None:
        api_key = os.environ.get("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError("OPENAI_API_KEY is not set in environment.")
        _openai_client = OpenAI(api_key=api_key)
    return _openai_client


def call_openai(prompt: str, model: str = "gpt-4.1-mini") -> str:
    """
    Call an OpenAI chat model with a child-safe system prompt.
    """
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
    return (response.choices[0].message.content or "").strip()


def get_ollama_client() -> Client:
    """
    Lazily construct a singleton Ollama client.

    We derive the host from OLLAMA_HOST if set; we accept both:
      - 'http://localhost:11434'
      - 'localhost:11434'
    and normalize to a full URL for the Client.
    """
    global _ollama_client
    if _ollama_client is None:
        host_env = os.environ.get("OLLAMA_HOST", "http://localhost:11434").strip()

        # Normalize: if there's no scheme, assume http://
        if not host_env.startswith("http://") and not host_env.startswith("https://"):
            host_env = f"http://{host_env}"

        # You can also tweak timeout here if needed
        _ollama_client = Client(host=host_env, timeout=20.0)  # seconds

    return _ollama_client


def call_ollama(prompt: str, model: str = "tinyllama") -> str:
    """
    Call a local Ollama model via the Python client.

    Uses OLLAMA_HOST (normalized) as the server base URL, so it plays nicely
    with Docker + host networking.
    """
    client = get_ollama_client()

    try:
        resp = client.chat(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are a friendly assistant for a child-safe "
                        "social media simulator."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            stream=False,
            options={
                # Keep generations relatively short/fast for feed posts
                "temperature": 0.8,
                "num_predict": 256,
            },
        )
    except Exception as e:  # httpx errors, connection issues, etc.
        raise RuntimeError(f"Ollama chat failed: {e}") from e

    # Ollama returns a dict with 'message' containing 'content'
    message = resp.get("message") or {}
    content = message.get("content", "") or ""
    if not content:
        raise RuntimeError("Empty response from Ollama")

    return content.strip()


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
        model_name = model or os.environ.get("OLLAMA_MODEL", "tinyllama")
        return call_ollama(prompt, model=model_name)

    # default to openai
    model_name = model or os.environ.get("OPENAI_MODEL", "gpt-4.1-mini")
    return call_openai(prompt, model=model_name)
