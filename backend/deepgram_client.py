"""
AURA — Deepgram Streaming STT Client
Streams audio from browser → Deepgram WebSocket → returns transcripts
"""

import os
import asyncio
from deepgram import (
    DeepgramClient,
    LiveTranscriptionEvents,
    LiveOptions,
)

DEEPGRAM_API_KEY = os.environ.get("DEEPGRAM_API_KEY", "")


class DeepgramStreamer:
    """Manages a live Deepgram WebSocket connection for one session."""

    def __init__(self, on_transcript):
        """
        on_transcript: async callable(transcript: str, is_final: bool)
        """
        self.on_transcript = on_transcript
        self.client = DeepgramClient(DEEPGRAM_API_KEY)
        self.connection = None
        self._final_transcript = ""

    async def start(self):
        """Open streaming connection to Deepgram."""
        self.connection = self.client.listen.asyncwebsocket.v("1")

        async def on_message(self_dg, result, **kwargs):
            sentence = result.channel.alternatives[0].transcript
            if not sentence:
                return

            if result.is_final:
                self._final_transcript += sentence + " "
                # Check if speech_final (endpointing detected pause)
                if hasattr(result, 'speech_final') and result.speech_final:
                    transcript = self._final_transcript.strip()
                    self._final_transcript = ""
                    if transcript:
                        await self.on_transcript(transcript, True)
                else:
                    await self.on_transcript(sentence, False)

        async def on_utterance_end(self_dg, result, **kwargs):
            """Fired when Deepgram detects end of utterance."""
            transcript = self._final_transcript.strip()
            self._final_transcript = ""
            if transcript:
                await self.on_transcript(transcript, True)

        async def on_error(self_dg, error, **kwargs):
            print(f"[Deepgram Error] {error}")

        self.connection.on(LiveTranscriptionEvents.Transcript, on_message)
        self.connection.on(LiveTranscriptionEvents.UtteranceEnd, on_utterance_end)
        self.connection.on(LiveTranscriptionEvents.Error, on_error)

        options = LiveOptions(
            model="nova-2",
            language="en-US",
            smart_format=True,
            encoding="linear16",
            sample_rate=16000,
            channels=1,
            interim_results=True,
            endpointing=300,
            utterance_end_ms="1000",
        )

        started = await self.connection.start(options)
        if not started:
            raise RuntimeError("Failed to start Deepgram connection")
        return True

    async def send_audio(self, audio_bytes: bytes):
        """Send raw audio chunk to Deepgram."""
        if self.connection:
            await self.connection.send(audio_bytes)

    async def stop(self):
        """Close the Deepgram connection."""
        if self.connection:
            try:
                await self.connection.finish()
            except Exception:
                pass
