# LiveKit Voice Agent

A full-stack, real-time AI voice agent built with **LiveKit**, **Deepgram**, **Anthropic Claude**, and **React**. Speak naturally into your microphone and hear AI-generated responses streamed back to you with low latency — just like a real phone call.

---

## Features

- **Real-time voice conversation** — microphone audio streams through LiveKit WebRTC to the agent and back
- **Full STT → LLM → TTS pipeline** — Deepgram WebSocket streaming STT, Claude LLM, configurable TTS
- **Multiple TTS providers** — PyTTSX3 (offline), gTTS (free), Google Cloud TTS, ElevenLabs
- **Multiple LLM providers** — Anthropic Claude (default), Google Gemini
- **Voice Recording mode** — record a clip, send through the pipeline, hear the response
- **Quick Text Test** — type text directly, skip STT, test LLM + TTS instantly
- **Real-time pipeline dashboard** — see STT / LLM / TTS latency for every request
- **Live event log** — WebSocket-streamed backend events shown in the browser UI
- **Auto-reconnect** — agent reconnects to LiveKit automatically on disconnect; HTTP API stays alive

---

## Architecture

```
Browser (React + LiveKit JS SDK)
        │  WebRTC audio (microphone)
        ▼
LiveKit Cloud / Server
        │  audio frames (16 kHz PCM)
        ▼
Python Agent (aiohttp + livekit.rtc)
        │
        ├─► Deepgram WebSocket STT ──► transcript
        │
        ├─► Claude / Gemini LLM ──────► response text
        │
        └─► TTS (PyTTSX3 / gTTS /
              Google Cloud / ElevenLabs) ──► WAV/MP3 bytes
                      │
                      └─► LiveKit audio track ──► Browser speakers
```

### Services

| Service | Directory | Port | Description |
|---|---|---|---|
| Python Agent | `src/` | `8080` | STT → LLM → TTS pipeline + HTTP API + WebSocket events |
| Token Server | `token-server/` | `3001` | Node.js JWT token minting for LiveKit |
| Frontend | `frontend/` | `5173` | React + Vite UI with LiveKit JS SDK |

---

## Tech Stack

| Layer | Technology |
|---|---|
| **Real-time transport** | [LiveKit](https://livekit.io) (WebRTC) |
| **STT** | [Deepgram](https://deepgram.com) (streaming WebSocket) |
| **LLM** | [Anthropic Claude](https://anthropic.com) / [Google Gemini](https://ai.google.dev) |
| **TTS** | PyTTSX3 · gTTS · Google Cloud TTS · ElevenLabs |
| **Backend** | Python 3.12+ · aiohttp · asyncio |
| **Token server** | Node.js · Express · livekit-server-sdk |
| **Frontend** | React 18 · Vite · livekit-client |

---

## Prerequisites

- Python 3.12+
- Node.js 18+
- A [LiveKit](https://cloud.livekit.io) account (free cloud tier works)
- A [Deepgram](https://console.deepgram.com) API key (free tier works)
- An [Anthropic](https://console.anthropic.com) API key **or** a [Gemini](https://ai.google.dev) API key

---

## Setup

### 1. Clone the repository

```bash
git clone https://github.com/NadeemMughal/livekit-voice-agent.git
cd livekit-voice-agent
```

### 2. Configure environment variables

```bash
cp .env.example .env
```

Open `.env` and fill in your API keys:

```env
# Required
DEEPGRAM_API_KEY=your_deepgram_key

# LLM — pick one
ANTHROPIC_API_KEY=your_anthropic_key      # Claude (default)
GEMINI_API_KEY=your_gemini_key            # Gemini (optional)
LLM_PROVIDER=Claude                       # or Gemini

# LiveKit
LIVEKIT_API_KEY=your_livekit_api_key
LIVEKIT_API_SECRET=your_livekit_api_secret
LIVEKIT_URL=wss://your-project.livekit.cloud
LIVEKIT_ROOM=test-room

# TTS — pick one
TTS_PROVIDER=PyTTSX3                      # offline, no key needed
# TTS_PROVIDER=gTTS                       # free, needs internet
# TTS_PROVIDER=ElevenLabs
# ELEVENLABS_API_KEY=your_elevenlabs_key
# TTS_PROVIDER=GoogleCloud
# GOOGLE_CLOUD_TTS_CREDENTIALS_PATH=path/to/credentials.json
```

### 3. Install Python dependencies

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

# macOS / Linux
source .venv/bin/activate

pip install -r requirements.txt
```

### 4. Install Node.js dependencies

```bash
cd token-server && npm install && cd ..
cd frontend && npm install && cd ..
```

---

## Running

Open **3 terminals** and run one command in each:

**Terminal 1 — Python Agent**
```bash
# Windows
.venv\Scripts\python.exe src/main.py

# macOS / Linux
.venv/bin/python src/main.py
```

**Terminal 2 — Token Server**
```bash
cd token-server
node index.js
```

**Terminal 3 — Frontend**
```bash
cd frontend
npm run dev
```

Then open [http://localhost:5173](http://localhost:5173) in your browser.

---

## Usage

### Quick Text Test
Type any message in the **Quick Test** panel and press **Send** or Enter. The text goes directly to the LLM → TTS pipeline and plays back through your browser's audio player. No microphone needed.

### Voice Recording
Click **Start Recording**, speak, then click **Stop**. The recording is sent to the full **STT → LLM → TTS** pipeline and the response plays back automatically.

### Real-time LiveKit Voice
1. Enter a room name (default: `test-room`) and click **Connect**
2. Allow microphone access when prompted
3. Speak — your voice streams live through LiveKit to the agent
4. The agent transcribes with Deepgram, generates a response with Claude, synthesizes speech, and streams it back through LiveKit to your speakers

---

## HTTP API Reference

The Python agent exposes a REST API on `http://localhost:8080`:

| Method | Endpoint | Description |
|---|---|---|
| `GET` | `/health` | Health check |
| `POST` | `/test` | `{ "text": "..." }` → LLM → TTS → returns audio bytes |
| `POST` | `/process-audio` | Multipart audio upload → STT → LLM → TTS → returns audio bytes |
| `WS` | `/ws` | Real-time pipeline events (STT / LLM / TTS timing) |

### Example — test endpoint

```bash
curl -X POST http://localhost:8080/test \
  -H "Content-Type: application/json" \
  -d '{"text": "What is the capital of France?"}' \
  --output response.wav
```

---

## Project Structure

```
livekit-voice-agent/
├── src/
│   ├── main.py                        # Entry point — HTTP API + LiveKit loop
│   └── agent/
│       ├── config.py                  # Pydantic settings (reads .env)
│       ├── voice_agent.py             # STT → LLM → TTS orchestrator
│       ├── livekit_client.py          # LiveKit room join, audio send/receive
│       ├── vad.py                     # Voice activity detection
│       ├── ws_logger.py               # WebSocket event broadcaster
│       └── clients/
│           ├── deepgram_client.py     # Deepgram REST STT
│           ├── deepgram_ws_client.py  # Deepgram WebSocket streaming STT
│           ├── claude_client.py       # Anthropic Claude LLM
│           ├── gemini_client.py       # Google Gemini LLM
│           ├── pyttsx3_client.py      # Offline TTS
│           ├── gtts_client.py         # gTTS (free)
│           ├── google_tts_client.py   # Google Cloud TTS
│           └── elevenlabs_client.py   # ElevenLabs TTS
├── token-server/
│   ├── index.js                       # Express server — LiveKit JWT minting
│   └── package.json
├── frontend/
│   ├── src/
│   │   ├── App.jsx                    # Main React UI
│   │   └── styles.css                 # Styles
│   ├── index.html
│   └── package.json
├── .env.example                       # Template — copy to .env and fill in keys
├── .gitignore
└── requirements.txt
```

---

## Configuration Reference

All settings are in `.env` and loaded by `src/agent/config.py`:

| Variable | Default | Description |
|---|---|---|
| `DEEPGRAM_API_KEY` | — | **Required.** Deepgram API key |
| `LLM_PROVIDER` | `Claude` | `Claude` or `Gemini` |
| `ANTHROPIC_API_KEY` | — | Required when `LLM_PROVIDER=Claude` |
| `CLAUDE_MODEL` | `claude-3-5-sonnet-20241022` | Claude model ID |
| `GEMINI_API_KEY` | — | Required when `LLM_PROVIDER=Gemini` |
| `MODEL_GEMINI` | `gemini-2.0-flash` | Gemini model ID |
| `TTS_PROVIDER` | `gTTS` | `PyTTSX3`, `gTTS`, `GoogleCloud`, `ElevenLabs` |
| `TTS_LANGUAGE` | `en` | Language code for gTTS |
| `ELEVENLABS_API_KEY` | — | Required when `TTS_PROVIDER=ElevenLabs` |
| `ELEVEN_VOICE_ID` | `alloy` | ElevenLabs voice ID |
| `GOOGLE_CLOUD_TTS_CREDENTIALS_PATH` | — | Path to Google Cloud JSON credentials |
| `GOOGLE_CLOUD_TTS_VOICE` | `en-US-Neural2-C` | Google Cloud voice name |
| `LIVEKIT_URL` | — | **Required.** LiveKit server WebSocket URL |
| `LIVEKIT_API_KEY` | — | **Required.** LiveKit API key |
| `LIVEKIT_API_SECRET` | — | **Required.** LiveKit API secret |
| `LIVEKIT_ROOM` | `test-room` | Default room name |

---

## License

MIT License — free to use, modify, and distribute.

---

## Author

**Muhammad Nadeem** — AI / ML Engineer

- Website: [nadeem.cloud](https://nadeem.cloud)
- LinkedIn: [muhammad-nadeem-ai-ml-engineer](https://www.linkedin.com/in/muhammad-nadeem-ai-ml-engineer/)
- GitHub: [NadeemMughal](https://github.com/NadeemMughal)
