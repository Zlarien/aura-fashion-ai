"""
AURA — Cartesia TTS Client
Converts text to speech audio, returns bytes for browser playback.
"""

import os
import httpx
import base64

CARTESIA_API_KEY = os.environ.get("CARTESIA_API_KEY", "")
CARTESIA_VOICE_ID = os.environ.get("CARTESIA_VOICE_ID", "a0e99841-438c-4a64-b679-ae501e7d6091")

TTS_URL = "https://api.cartesia.ai/tts/bytes"


async def synthesize_speech(text: str) -> bytes:
    """
    Call Cartesia REST API for TTS. Returns raw audio bytes (WAV).
    Uses REST for simplicity — WebSocket streaming not needed for short summaries.
    """
    headers = {
        "X-API-Key": CARTESIA_API_KEY,
        "Cartesia-Version": "2024-06-10",
        "Content-Type": "application/json",
    }

    payload = {
        "model_id": "sonic-2",
        "transcript": text,
        "voice": {
            "mode": "id",
            "id": CARTESIA_VOICE_ID,
        },
        "output_format": {
            "container": "wav",
            "encoding": "pcm_s16le",
            "sample_rate": 24000,
        },
    }

    async with httpx.AsyncClient(timeout=30.0) as client:
        response = await client.post(TTS_URL, json=payload, headers=headers)
        response.raise_for_status()
        return response.content
