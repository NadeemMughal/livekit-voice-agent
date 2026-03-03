from pydantic_settings import BaseSettings
from pydantic import Field


class AgentConfig(BaseSettings):
    DEEPGRAM_API_KEY: str = Field(..., env="DEEPGRAM_API_KEY")
    LIVEKIT_API_KEY: str = Field(None, env="LIVEKIT_API_KEY")
    LIVEKIT_API_SECRET: str = Field(None, env="LIVEKIT_API_SECRET")
    LIVEKIT_URL: str = Field(None, env="LIVEKIT_URL")
    LIVEKIT_ROOM: str = Field("test-room", env="LIVEKIT_ROOM")
    
    # LLM provider selection: 'Claude' or 'Gemini'
    LLM_PROVIDER: str = Field("Claude", env="LLM_PROVIDER")
    
    # Anthropic Claude
    ANTHROPIC_API_KEY: str = Field(None, env="ANTHROPIC_API_KEY")
    CLAUDE_MODEL: str = Field("claude-3-5-sonnet-20241022", env="CLAUDE_MODEL")
    
    # Google Gemini (optional)
    GEMINI_API_KEY: str = Field(None, env="GEMINI_API_KEY")
    MODEL_GEMINI: str = Field("gemini-2.0-flash", env="MODEL_GEMINI")
    
    # TTS provider: 'PyTTSX3' (offline), 'gTTS' (free), 'GoogleCloud', 'ElevenLabs'
    TTS_PROVIDER: str = Field("gTTS", env="TTS_PROVIDER")
    TTS_LANGUAGE: str = Field("en", env="TTS_LANGUAGE")
    
    # ElevenLabs TTS  
    ELEVENLABS_API_KEY: str = Field(None, env="ELEVENLABS_API_KEY")
    ELEVEN_VOICE_ID: str = Field("alloy", env="ELEVEN_VOICE_ID")
    
    # Google Cloud TTS (free tier: 1M chars/month)
    GOOGLE_CLOUD_TTS_CREDENTIALS_PATH: str = Field(None, env="GOOGLE_CLOUD_TTS_CREDENTIALS_PATH")
    GOOGLE_CLOUD_TTS_VOICE: str = Field("en-US-Neural2-C", env="GOOGLE_CLOUD_TTS_VOICE")

    class Config:
        env_file = ".env"


__all__ = ["AgentConfig"]
