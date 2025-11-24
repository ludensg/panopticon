# prompts.py

GAMIFIED_PROMPT = """
You are generating a social media style post for a CHILD-FRIENDLY, CARTOONY digital world.

Context:
- The child is {child_age} years old.
- The main topic is: {topic}.
- The profile posting this is:
  - Name: {profile_name}
  - Personality: {personality_tags}
  - Avatar style: cartoony

Requirements:
- Write 1 short, fun, positive post this profile might share.
- Use very simple language appropriate for a {child_age}-year-old.
- Include 1–2 emojis that match the tone.
- Do NOT mention that this is a simulation or that you are AI.
- Avoid anything scary, violent, or adult.

Respond with ONLY the text of the post.
"""

REALISTIC_PROMPT = """
You are generating a social media style post for a CHILD-SAFE but REALISTIC social feed.

Context:
- The child is {child_age} years old.
- The main topic is: {topic}.
- The profile posting this is:
  - Name: {profile_name}
  - Personality: {personality_tags}
  - Avatar style: realistic

Requirements:
- Write 1 short, natural-sounding post that a real kid around {child_age} might share.
- Keep it friendly, encouraging, and appropriate for children.
- You may include 1 emoji, but do not overdo it.
- Do NOT mention AI, simulations, or anything meta.
- Avoid complex or negative topics; stay curious and kind.

Respond with ONLY the text of the post.
"""
