# Voice Agent scaffold

This repository provides a scaffolded, object-oriented Python implementation of a telephony voice agent that integrates:

- LiveKit for call/connectivity (wrapper)
- Deepgram for speech-to-text (STT)
- Gemini (Gemini 2.0 flash lite) for LLM responses
- ElevenLabs (Voice v3 conversational) for TTS
- WebRTC VAD for voice activity detection (VAD)

Files created:

- `src/agent/config.py` : configuration loader
- `src/agent/clients/` : STT/LLM/TTS client wrappers
- `src/agent/vad.py` : VAD wrapper
- `src/agent/livekit_client.py` : LiveKit integration placeholder
- `src/agent/voice_agent.py` : main orchestrator
- `src/main.py` : runner
- `.env.example` : environment variables to replace with your keys

Replace these values in `.env` (copy from `.env.example`):

- `DEEPGRAM_API_KEY` — Deepgram API key
- `ELEVENLABS_API_KEY` — ElevenLabs API key
- `GEMINI_API_KEY` — Google Gemini API key / service account credentials
- `LIVEKIT_API_KEY` and `LIVEKIT_API_SECRET` — LiveKit keys
- `LIVEKIT_URL` — LiveKit websocket/host

Quick start (example):

1. Create a virtualenv and install requirements:

```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r "d:/LiveKit Voice Agent/requirements.txt"
```

2. Copy `.env.example` to `.env` and fill API keys.

3. Run the agent (prototype):

```bash
python "d:/LiveKit Voice Agent/src/main.py"
```

Notes:

- Many methods in this scaffold are intentionally left as clear integration points (TODOs) for your production credentials and real streaming integration (Deepgram realtime, LiveKit RTC sending/receiving). The structure follows OOP and dependency injection so you can replace implementations with production-grade streaming code.
