"""
ElevenLabs TTS client (simple REST wrapper).

Produces audio bytes for given text using ElevenLabs API.
"""
import aiohttp
from typing import Optional


class ElevenLabsTTS:
    def __init__(self, api_key: str, voice_id: str = "alloy"):
        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = "https://api.elevenlabs.io/v1/text-to-speech"

    async def synthesize(self, text: str, model: str = "eleven_multilingual_v3") -> bytes:
        url = f"{self.base_url}/{self.voice_id}"
        headers = {
            "xi-api-key": self.api_key,
            "Accept": "audio/wav",
            "Content-Type": "application/json",
        }
        payload = {"text": text, "model": model}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    txt = await resp.text()
                    raise RuntimeError(f"ElevenLabs error {resp.status}: {txt}")
                return await resp.read()


__all__ = ["ElevenLabsTTS"]
