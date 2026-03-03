"""
Deepgram client wrapper.

This file provides a simple REST-based transcription helper and a stub for a
real-time streaming implementation (WebSocket). Replace or extend the
`stream_transcribe` method with Deepgram's WebSocket streaming when building
real-time call handling.
"""
import aiohttp
import asyncio
from typing import Optional


class DeepgramClient:
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.deepgram.com/v1/listen"

    async def transcribe_file(self, audio_bytes: bytes, mimetype: str = "audio/wav") -> str:
        """Transcribe an audio blob via Deepgram's REST endpoint (simple, non-streaming).

        Returns the transcript text.
        """
        headers = {
            "Authorization": f"Token {self.api_key}",
            "Content-Type": mimetype,
        }
        async with aiohttp.ClientSession() as session:
            async with session.post(self.base_url, data=audio_bytes, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    raise RuntimeError(f"Deepgram error {resp.status}: {text}")
                data = await resp.json()
                # Deepgram returns alternatives / channels; adapt as needed
                try:
                    return data.get("results", {}).get("channels", [])[0].get("alternatives", [])[0].get("transcript", "")
                except Exception:
                    return data.get("transcript", "")

    async def stream_transcribe(self):
        """
        Placeholder for a real-time streaming implementation using Deepgram's WebSocket API.
        For production call handling you should implement a WebSocket client that sends
        small audio frames and reads incremental transcripts.
        """
        raise NotImplementedError("Implement WebSocket streaming for low-latency transcription")


__all__ = ["DeepgramClient"]
