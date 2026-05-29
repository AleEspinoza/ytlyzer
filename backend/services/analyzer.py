import os
import json
from anthropic import AnthropicVertex

_client = None


def _get_client() -> AnthropicVertex:
    global _client
    if _client is None:
        _client = AnthropicVertex(
            region=os.environ["GCP_REGION"],
            project_id=os.environ["GCP_PROJECT_ID"],
        )
    return _client


async def analyze_transcript(
    transcript: str,
    segments: list[dict],
    query: str,
) -> list[dict]:
    """
    Send the transcript and segments to Claude and ask it to identify
    the fragments most relevant to the user's query.

    Returns a list of matching fragments with start/end timestamps and text.
    """
    segments_json = json.dumps(segments, ensure_ascii=False)

    prompt = f"""You are analyzing a YouTube video transcript to find fragments relevant to a user's query.

USER QUERY: {query}

TRANSCRIPT SEGMENTS (JSON array with start/end times in seconds):
{segments_json}

FULL TRANSCRIPT:
{transcript}

Instructions:
- Identify all segments that are relevant to the user's query.
- Return ONLY a JSON array of matching segments. Each item must have:
  - "start": start time in seconds (number)
  - "end": end time in seconds (number)
  - "text": the spoken text of that segment (string)
  - "reason": one sentence explaining why this fragment matches the query (string)
- If no segments match, return an empty array: []
- Do not include any explanation outside the JSON array.
"""

    client = _get_client()
    message = client.messages.create(
        model="claude-opus-4-6",
        max_tokens=4096,
        messages=[{"role": "user", "content": prompt}],
    )

    raw = message.content[0].text.strip()

    # Strip markdown code fences if present
    if raw.startswith("```"):
        raw = raw.split("```")[1]
        if raw.startswith("json"):
            raw = raw[4:]
        raw = raw.strip()

    fragments = json.loads(raw)
    return fragments
