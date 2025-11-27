# prompts.py

REALISTIC_PROMPT = """
You are writing a short, kid-safe post for a social media-like feed.

Context:
- Child age: {child_age}
- Topic: {topic}
- Child interests: {child_interests}
- Post flavor: {post_flavor}  # either "personal update" or "kid-friendly news"
- Author persona: {author_name} (personality: {personality_tags})

Requirements:
- Length: 1–3 sentences.
- Tone: warm, engaging, not babyish or sarcastic.
- Language: clear, concrete, avoid slang that would age badly.
- Never mention AI, simulations, or that this is fake.

If the post flavor is "personal update":
- Write as if the author is sharing a small moment, idea, or tip about the topic.
- You can include a small thought, observation, or question that might invite comments.

If the post flavor is "kid-friendly news":
- Write in an informative style, like a friend sharing a cool thing they just learned.
- When possible, refer to a recent (2020s) positive or important development about the topic
  in a simple, reassuring way (no graphic, scary, or sensational details).
- Focus on what a child could learn or feel excited about.

Return ONLY the post text, no labels, no quotes.
"""

GAMIFIED_PROMPT = """
You are writing a playful, clearly game-like post for a kid-safe social media simulator.

Context:
- Child age: {child_age}
- Topic: {topic}
- Child interests: {child_interests}
- Post flavor: {post_flavor}  # "personal update" or "kid-friendly news"
- Author persona: {author_name} (personality: {personality_tags})

Requirements:
- Length: 1–3 short sentences.
- Tone: cartoonish, fun, emoji-friendly, but still respectful and not annoying.
- It should be obvious this is playful or game-like, not a real social network.
- Never mention AI, simulations, or that this is fake explicitly; let the over-the-top style hint it.
- Avoid scary content or anything intense.

If the post flavor is "personal update":
- Make it feel like a character sharing something silly or cool they did or noticed.

If the post flavor is "kid-friendly news":
- Present news-like information as a fun fact or story.
- Mention only positive or neutral aspects; no graphic or frightening details.
- Focus on wonder, curiosity, or teamwork.

Return ONLY the post text, no labels, no quotes.
"""
