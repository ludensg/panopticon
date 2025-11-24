# llm_client.py

import os
from openai import OpenAI

# Initialize client once (reads OPENAI_API_KEY from env)
client = OpenAI()

# Default model for feed generation
DEFAULT_MODEL = "gpt-4.1-mini"  # adjust if you prefer another model


def call_llm(prompt: str) -> str:
    """
    Call the OpenAI Chat Completions API with a simple user prompt.
    Returns the model's text response.
    """
    # Safety: in case key is missing, fail loudly
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        # Optional: you can raise or return a clear message
        # but raising is better so you don't silently fail.
        raise RuntimeError(
            "OPENAI_API_KEY is not set. Please export it in your environment."
        )

    # The OpenAI client picks up the key from the environment,
    # so we don't need to pass it here explicitly.
    response = client.chat.completions.create(
        model=DEFAULT_MODEL,
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        temperature=0.8,
    )

    # Extract the text
    content = response.choices[0].message.content
    return content.strip()
