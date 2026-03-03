"""
Cartesia TTS client wrapper (free tier available).

Cartesia.ai provides free TTS with high-quality voices and natural speech.
Sign up at: https://cartesia.ai
"""
import aiohttp
import logging

logger = logging.getLogger(__name__)


class CartesiaTTS:
    """Text-to-Speech client using Cartesia API (free tier available)."""
    
    def __init__(self, api_key: str, voice_id: str = "79a125e8-cd45-4c13-8a67-188112f4dd22"):
        """
        Initialize Cartesia TTS client.
        
        Args:
            api_key: Cartesia API key (free tier available at https://cartesia.ai)
            voice_id: Voice ID to use for synthesis (default: Bam - a clear, natural male voice)
        """
        self.api_key = api_key
        self.voice_id = voice_id
        self.base_url = "https://api.cartesia.ai/api/tts"
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech using Cartesia.
        
        Args:
            text: Text to synthesize
        
        Returns:
            WAV audio bytes
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/wav"
            }
            
            payload = {
                "model_id": "sonic-english",
                "transcript": text,
                "voice": {
                    "mode": "id",
                    "id": self.voice_id
                },
                "output_format": {
                    "container": "wav",
                    "encoding": "pcm",
                    "sample_rate": 16000
                }
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(self.base_url, json=payload, headers=headers) as resp:
                    if resp.status != 200:
                        error_text = await resp.text()
                        logger.error(f"Cartesia TTS error {resp.status}: {error_text}")
                        raise RuntimeError(f"Cartesia TTS error {resp.status}: {error_text}")
                    
                    audio_bytes = await resp.read()
                    logger.info(f"✓ Cartesia TTS: synthesized {len(text)} chars → {len(audio_bytes)} bytes")
                    return audio_bytes
        
        except Exception as e:
            logger.error(f"Cartesia synthesis error: {e}")
            raise RuntimeError(f"Cartesia TTS error: {str(e)}")


__all__ = ["CartesiaTTS"]
