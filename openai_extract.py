import json

from openai import OpenAI

import config

_client = OpenAI(api_key=config.OPENAI_API_KEY)

_VALID_PRIORITIES = {"Highest", "High", "Medium", "Low"}

SYSTEM_PROMPT = """You are an assistant that extracts structured video-idea data from a transcript of a voice note. The transcript may be in Hindi, English, or a mix of both (Hinglish), and may contain transcription errors or filler words.

Always respond in English, regardless of the language of the transcript. If the transcript is in Hindi or Hinglish, translate it into clear English.

Return ONLY a JSON object with exactly these fields:
- "title": a clear, descriptive title for the video idea, in English. It should not be too short - it should properly explain the concept in roughly one sentence.
- "video_idea": the full idea/description as explained in the transcript, in English, cleaned up into readable sentences (fix filler words and disfluencies, but keep the original meaning and details).
- "priority": one of "Highest", "High", "Medium", "Low". Infer this from words like "sabse zaroori" / "most important" / "urgent" -> Highest; "important" / "jaldi karna hai" -> High; "medium" / "normal" -> Medium; "baad mein" / "not urgent" / "low" -> Low. If no priority is mentioned at all, use "Medium".
"""


def extract_idea(transcript: str) -> dict:
    completion = _client.chat.completions.create(
        model=config.OPENAI_MODEL,
        response_format={"type": "json_object"},
        temperature=0.2,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": transcript},
        ],
    )
    data = json.loads(completion.choices[0].message.content)

    priority = str(data.get("priority", "Medium")).strip().title()
    if priority not in _VALID_PRIORITIES:
        priority = "Medium"

    title = str(data.get("title", "")).strip() or "Untitled Video Idea"
    video_idea = str(data.get("video_idea", "")).strip() or transcript.strip()

    return {"title": title, "video_idea": video_idea, "priority": priority}
