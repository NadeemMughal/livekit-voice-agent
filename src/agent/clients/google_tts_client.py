"""
Google Cloud Text-to-Speech client wrapper (free tier available).

Google Cloud TTS provides high-quality speech synthesis.
Free tier: 1 million characters per month.
"""
from google.cloud import texttospeech
import logging

logger = logging.getLogger(__name__)


class GoogleCloudTTS:
    """Text-to-Speech client using Google Cloud TTS (free tier available)."""
    
    def __init__(self, credentials_path: str = None, voice_name: str = "en-US-Neural2-C"):
        """
        Initialize Google Cloud TTS client.
        
        Args:
            credentials_path: Path to Google Cloud service account JSON file
            voice_name: Voice name (e.g., en-US-Neural2-C for female, en-US-Neural2-A for male)
        """
        self.voice_name = voice_name
        self.language_code = "en-US"
        
        # Initialize client
        if credentials_path:
            self.client = texttospeech.TextToSpeechClient.from_service_account_file(credentials_path)
        else:
            self.client = texttospeech.TextToSpeechClient()
    
    async def synthesize(self, text: str) -> bytes:
        """
        Synthesize text to speech using Google Cloud TTS.
        
        Args:
            text: Text to synthesize
        
        Returns:
            WAV audio bytes
        """
        try:
            input_text = texttospeech.SynthesisInput(text=text)
            
            voice = texttospeech.VoiceSelectionParams(
                language_code=self.language_code,
                name=self.voice_name,
            )
            
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
            )
            
            request = texttospeech.SynthesizeSpeechRequest(
                input=input_text,
                voice=voice,
                audio_config=audio_config,
            )
            
            response = self.client.synthesize_speech(request=request)
            audio_bytes = response.audio_content
            logger.info(f"✓ Google Cloud TTS: synthesized {len(text)} chars → {len(audio_bytes)} bytes")
            return audio_bytes
        
        except Exception as e:
            logger.error(f"Google Cloud TTS error: {e}")
            raise RuntimeError(f"Google Cloud TTS error: {str(e)}")


__all__ = ["GoogleCloudTTS"]
