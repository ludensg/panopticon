# prompts.py

REALISTIC_PROMPT = """
You are generating a short, child-safe social media post in ENGLISH.

Overall purpose:
- This is for a simulated social-media-like feed for children.
- It should feel like a real kid or peer wrote it, but remain completely safe and age-appropriate.

HARD CONSTRAINTS:
- Audience: a child around {child_age} years old.
- Tone: friendly, warm, simple, and calm.
- Length: 1 to 3 sentences, at most ~40 words in total.
- Reading level: roughly appropriate for a child of that age (short sentences, everyday words).
- ABSOLUTELY NO:
  - explicit content, gore, hate, bullying, romance, or scary themes,
  - requests for personal information, contact details, or locations,
  - references to AI, simulations, being generated, "as an AI", "as a bot", or similar.
- No quoting the instructions or mentioning safety rules.

CONTEXT:
- Topic of the post: {topic}
- Author's personality tags: {personality_tags}
- Author's display name: {author_name}
- Child's listed interests: {child_interests}

STYLE:
- It should sound like a real, friendly kid posting about the topic.
- You MAY use first person ("I") if natural.
- You MAY refer to everyday school, hobbies, or family life.
- Keep it grounded in normal kid experiences.

TASK:
Write ONE short post consistent with the constraints above.
Return ONLY the post text with no explanations, no quotation marks, and no extra commentary.
"""

GAMIFIED_PROMPT = """
You are generating a playful, cartoony, obviously game-like social media post in ENGLISH.

Overall purpose:
- This is for a simulated, game-like social feed for children.
- It should be clearly fictional and feel like part of a fun game world, not real life.

HARD CONSTRAINTS:
- Audience: a child around {child_age} years old.
- Tone: silly, light, positive, and safe.
- Length: 1 to 3 sentences, at most ~40 words in total.
- Reading level: roughly appropriate for a child of that age (short sentences, everyday words).
- ABSOLUTELY NO:
  - explicit content, gore, hate, bullying, romance, or scary themes,
  - requests for personal information, contact details, or locations,
  - references to AI, simulations, being generated, "as an AI", "as a bot", or similar.
- No quoting the instructions or mentioning safety rules.

CONTEXT:
- Topic of the post: {topic}
- Author's personality tags: {personality_tags}
- Author's display name: {author_name}
- Child's listed interests: {child_interests}

STYLE:
- It should clearly feel like a pretend, cartoony or fantasy world.
- You MAY mention that this is in a "game", "quest", or "imaginary world".
- Use a few fun emojis (2–5), but do not spam them.
- The tone should be playful and whimsical.

TASK:
Write ONE short post consistent with the constraints above.
Return ONLY the post text with no explanations, no quotation marks, and no extra commentary.
"""
