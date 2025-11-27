# prompts.py

REALISTIC_PROMPT = """
You are writing a short, realistic, kid-safe post for a social-media-style feed. 
Your goal is to produce a natural 1–3 sentence post that feels like something a real kid or teen might share, 
while subtly modeling healthy social behaviors based on the child’s adaptive skill profile.

--- ADAPTIVE CONTEXT ---
{adaptive_context}
(This describes the child's strengths and weaknesses in: boundary-setting, emotional clarity, info-sharing safety, peer-pressure resistance, and curiosity. Use this ONLY to shape the behavior the author models, NOT to comment on the child.)

--- WRITING CONTEXT ---
- Child age: {child_age}
- Topic: {topic}
- Child interests: {child_interests}
- Post flavor: {post_flavor}  # "personal update" or "kid-friendly news"
- Author persona: {author_name} (personality traits: {personality_tags})
- Optional sub-flavor: {sub_flavor}
- Additional news context (may be empty if not news-related): {news_context}

--- CONTENT REQUIREMENTS ---
- Write 1–3 natural, conversational sentences.
- Tone: warm, friendly, grounded; not babyish or sarcastic.
- Include at least one specific detail related to the topic (e.g., a game mechanic, a mission name, an animal behavior, a science fact).
- Do NOT overshare personal details such as locations, full schedules, or identifying information.
- Never mention AI, simulations, or that the feed is fictional.

--- STYLE RULES (REALISTIC MODE) ---
- Sound like a real person speaking casually online.
- Minimal emoji use (0–1 total).
- Avoid overly dramatic punctuation or exaggeration.
- Use concrete nouns and simple emotional vocabulary.

--- ADAPTIVITY RULES ---
Use the adaptive context to shape how the author behaves:
- Low boundary-setting → The author briefly mentions choosing a limit or checking before agreeing.
- Low info-sharing safety → The author avoids giving specifics and may mention being careful without lecturing.
- Low peer-pressure resistance → The author casually redirects or declines a suggestion in the story.
- Low emotional clarity → The author names their feelings in simple, relatable terms.
- High curiosity → The post may add a small question or note of exploration.

Do NOT talk *about* these skills. Only demonstrate them through the author's behavior.

--- FLAVOR RULES ---
If "personal update":
- Share a small moment, observation, or story involving the topic.
- Include a detail that conveys personality or thoughtfulness.
- Optionally add a small question or reflection.

If "kid-friendly news":
- Share a real or plausible positive development or cool fact about the topic.
- Keep it simple, accurate, and age-appropriate.
- No scary or intense content.

--- OUTPUT ---
Return ONLY the final post text with no labels or explanations.
""".strip()


GAMIFIED_PROMPT = """
You are writing a playful, clearly fictional and game-like post for a kid-safe social-media simulator.
The post should feel fun, stylized, and expressive while still being respectful and easy to read.

--- ADAPTIVE CONTEXT ---
{adaptive_context}
(Use this ONLY to shape the behavior the author models, not to comment on the child.)

--- WRITING CONTEXT ---
- Child age: {child_age}
- Topic: {topic}
- Child interests: {child_interests}
- Post flavor: {post_flavor}
- Author persona: {author_name} (personality traits: {personality_tags})
- Optional sub-flavor: {sub_flavor}

--- CONTENT REQUIREMENTS ---
- Length: 1–3 short, energetic sentences.
- Include at least one specific detail related to the topic (e.g., a level name, creature type, tool, phenomenon).
- Keep everything positive or neutral.
- Avoid real-life personal information.
- Never mention AI or simulations explicitly.

--- STYLE RULES (GAMIFIED MODE) ---
- Tone: cartoonish, fun, slightly exaggerated.
- Use 1–3 emojis placed purposefully (often at sentence edges).
- Light use of sound effects, sparkles, or playful metaphors (e.g., “boost mode,” “spark-charge”).
- Still coherent and not chaotic; avoid long emoji strings.
- No scary or intense content.

--- ADAPTIVITY RULES ---
Use the adaptive context to shape character behavior:
- Low boundary-setting → The character lightly “defends their quest line” or “chooses the safe path.”
- Low info-sharing safety → The character mentions keeping things “mysterious” or “protected,” without real-life specifics.
- Low peer-pressure resistance → The character shows choosing their own move instead of following the crowd.
- Low emotional clarity → The character expresses simple feelings (“felt kinda jittery but powered up”).
- High curiosity → The post may invite an imaginative question or exploration.

Do NOT explain these behaviors; show them in-character.

--- FLAVOR RULES ---
If "personal update":
- Share a quirky moment or playful micro-story about the topic.
- Use imaginative metaphors or humorous exaggerations.

If "kid-friendly news":
- Present the news as a fun fact or “quest update.”
- Highlight wonder, curiosity, or teamwork.

--- OUTPUT ---
Return ONLY the final post text with no labels or explanations.
""".strip()
