# tinyprompts.py

REALISTIC_PROMPT = """
Write a kid-safe, realistic social post (1–2 natural sentences).

Use this only for shaping behavior, never mentioning it:
{adaptive_context}

CONTEXT:
Age: {child_age}
Topic: {topic}
Interests: {child_interests}
Flavor: {post_flavor}
Author: {author_name} ({personality_tags})
Sub-flavor: {sub_flavor}
News: {news_context}

RULES:
- Sound like a real kid/teen.
- Include one concrete topic detail.
- No personal info, no AI mentions.
- Warm, simple tone; 0–1 emoji.
- Show safe choices, simple feelings, curiosity, or gentle boundaries through behavior only.

OUTPUT: Only the post text.
""".strip()

GAMIFIED_PROMPT = """
Write a playful, game-like kid-safe post (1–2 short sentences).

Use this only for behavior, never mentioning it:
{adaptive_context}

CONTEXT:
Age: {child_age}
Topic: {topic}
Interests: {child_interests}
Flavor: {post_flavor}
Author: {author_name} ({personality_tags})
Sub-flavor: {sub_flavor}

RULES:
- Fun, cartoonish tone; 1–3 emojis.
- Include one concrete topic detail.
- Light effects/metaphors allowed.
- No personal info, no AI mentions.
- Show safe choices, simple feelings, curiosity, independence through behavior only.

OUTPUT: Only the post text.
""".strip()

