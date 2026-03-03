"""
Free TTS via Google Translate gTTS (no API key required).

Synthesis runs in a thread-pool executor because gTTS.write_to_fp() is
synchronous + does network I/O, which would otherwise block the event loop.
"""
import asyncio
import io
import logging

logger = logging.getLogger(__name__)


class GTTSClient:
    mime_type = "audio/mpeg"

    def __init__(self, language: str = "en"):
        self.language = language

    def _synthesize_sync(self, text: str) -> bytes:
        from gtts import gTTS
        tts = gTTS(text=text, lang=self.language, slow=False)
        buf = io.BytesIO()
        tts.write_to_fp(buf)
        return buf.getvalue()

    async def synthesize(self, text: str) -> bytes:
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, self._synthesize_sync, text)
        logger.info(f"gTTS: {len(text)} chars → {len(audio)} bytes")
        return audio


__all__ = ["GTTSClient"]
