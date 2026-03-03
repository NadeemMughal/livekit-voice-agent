"""
Offline TTS using pyttsx3 (completely free, no API key required).

Synthesis runs in a thread-pool executor so it never blocks the asyncio
event loop — fixes the 20-second freeze on long responses.
Works on Windows (SAPI5), macOS (NSSpeechSynthesizer), Linux (espeak).
"""
import asyncio
import logging
import os
import tempfile

logger = logging.getLogger(__name__)


class PyTTSX3Client:
    mime_type = "audio/wav"

    def __init__(self, rate: int = 175, volume: float = 1.0):
        self._rate = rate
        self._volume = volume

    def _synthesize_sync(self, text: str) -> bytes:
        """Blocking synthesis — always called inside a thread-pool worker."""
        import pyttsx3
        engine = pyttsx3.init()
        engine.setProperty("rate", self._rate)
        engine.setProperty("volume", self._volume)
        tmp = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            engine.save_to_file(text, tmp_path)
            engine.runAndWait()
            engine.stop()
            with open(tmp_path, "rb") as f:
                return f.read()
        finally:
            try:
                os.unlink(tmp_path)
            except OSError:
                pass

    async def synthesize(self, text: str) -> bytes:
        loop = asyncio.get_event_loop()
        audio = await loop.run_in_executor(None, self._synthesize_sync, text)
        logger.info(f"pyttsx3: {len(text)} chars → {len(audio)} bytes")
        return audio


__all__ = ["PyTTSX3Client"]
