## LiveKit Voice Agent - Complete Setup Guide

This is a production-ready voice agent scaffold with:
- **Backend**: Python asyncio agent with Deepgram STT, Gemini LLM, ElevenLabs TTS, VAD
- **Frontend**: React Vite app for testing with live logs
- **Token Server**: Express.js server for minting LiveKit access tokens
- **Logging**: Structured events with latency tracking

### Prerequisites

1. **API Keys** (required for production):
   - [Deepgram](https://console.deepgram.com) API key
   - [Google Gemini](https://ai.google.dev) API credentials
   - [ElevenLabs](https://elevenlabs.io) API key
   - [LiveKit](https://livekit.io) API key, secret, and server URL

2. **Software**:
   - Python 3.10+ with pip
   - Node.js 16+ with npm
   - Windows PowerShell or bash terminal

### Quick Start (3 Steps)

#### Step 1: Setup Backend

```powershell
cd "d:/LiveKit Voice Agent"
python -m venv .venv
.venv\Scripts\activate
pip install --upgrade pip
pip install -r requirements.txt
```

Create `.env` from `.env.example`:
```powershell
copy .env.example .env
```

Edit `.env` and fill in your API keys:
```
DEEPGRAM_API_KEY=your_key_here
ELEVENLABS_API_KEY=your_key_here
GEMINI_API_KEY=your_key_here
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://your-livekit-instance.com
MODEL_GEMINI=gbf-2.0-flash-lite
ELEVEN_VOICE_ID=alloy
```

#### Step 2: Setup Token Server

```powershell
cd "d:/LiveKit Voice Agent/token-server"
npm install
```

Create `.env` in token-server folder:
```
LIVEKIT_API_KEY=your_api_key
LIVEKIT_API_SECRET=your_api_secret
LIVEKIT_URL=wss://your-livekit-instance.com
PORT=3001
```

#### Step 3: Setup Frontend

```powershell
cd "d:/LiveKit Voice Agent/frontend"
npm install
```

### Run Everything

**Terminal 1 - Backend Agent**:
```powershell
cd "d:/LiveKit Voice Agent"
.venv\Scripts\activate
python src/main.py
```

**Terminal 2 - Token Server**:
```powershell
cd "d:/LiveKit Voice Agent/token-server"
node index.js
```

**Terminal 3 - Frontend Dev Server**:
```powershell
cd "d:/LiveKit Voice Agent/frontend"
npm run dev
```

Open browser: http://localhost:5173/
- Enter room name (e.g., "test-room")
- Click "▶️ Connect & Publish Mic"
- Speak! Logs will show STT→LLM→TTS pipeline with latencies

### Architecture

```
Frontend (React)
    ├─ Requests token from Token Server
    ├─ Connects to LiveKit room
    └─ Publishes microphone + displays logs

Token Server (Node.js)
    └─ Mints short-lived JWT tokens using LiveKit API

Backend (Python)
    ├─ Joins same LiveKit room
    ├─ Subscribes to participant audio
    ├─ Streams to Deepgram (STT)
    ├─ Sends transcript to Gemini (LLM)
    ├─ Synthesizes response with ElevenLabs (TTS)
    └─ Publishes TTS audio back to room

LiveKit Server
    └─ Routes audio between frontend, backend, and any other participants
```

### Logging & Events

The backend emits structured events with latency:
- **VAD**: `log_vad(True/False)`  — voice activity detected
- **STT**: `log_stt_start()` / `log_stt_end(transcript, duration_ms)`
- **LLM**: `log_llm_start(prompt)` / `log_llm_end(response, duration_ms)`
- **TTS**: `log_tts_start(text)` / `log_tts_end(duration_ms, bytes)`
- **Interrupt**: `request_interrupt()` — stops current processing
- **Error**: `log_error(msg, exception)`

Frontend UI shows all events with color-coded types:
- 🟢 **Success** (green): connected, published
- 🔵 **Info** (light gray): normal events
- 🟡 **Warning** (orange): disconnects, interrupts
- 🔴 **Error** (red): API failures, exceptions

### Configuration & Customization

| Setting | File | Description |
|---------|------|-------------|
| `DEEPGRAM_API_KEY` | `.env` | STT provider key |
| `GEMINI_API_KEY` | `.env` | LLM provider key |
| `ELEVENLABS_API_KEY` | `.env` | TTS provider key |
| `LIVEKIT_URL` | `.env`, `token-server/.env` | WebSocket URL to LiveKit server |
| `MODEL_GEMINI` | `.env` | LLM model ID (e.g., `gbf-2.0-flash-lite`) |
| `ELEVEN_VOICE_ID` | `.env` | TTS voice ID (e.g., `alloy`, `fable`) |
| React dev port | `frontend/vite.config.js` | Default 5173 |
| Token server port | `token-server/index.js` | Default 3001 |

### Troubleshooting

**"No module named 'pkg_resources'"**:
- Fallback VAD stub is used. For native support, install build tools or run on Linux.

**Token request fails from frontend**:
- Check token server is running: http://localhost:3001/health
- Verify `.env` in `token-server/` folder is set

**Backend can't connect to LiveKit**:
- Verify `LIVEKIT_URL` and API credentials are correct
- Check LiveKit server is accessible from your machine

**No audio published**:
- Check browser microphone permissions
- Look at browser console for errors
- Verify LiveKit room name matches in frontend

### OOP Architecture

- **`VoiceAgent`**: Main orchestrator class (dependency injection)
- **`DeepgramClient`**: REST transcription
- **`DeepgramWebsocketClient`**: Real-time streaming STT
- **`GeminiClient`**: LLM response generation
- **`ElevenLabsTTS`**: Text-to-speech synthesis
- **`LiveKitClient`**: LiveKit room management
- **`VAD`**: Voice activity detection (with fallback)
- **`WebSocketLogger`**: Structured event logging

All clients are injectable, so you can swap implementations for testing or production variations.

### What's Implemented

✅ Real LiveKit join/subscribe  
✅ Deepgram streaming WebSocket STT  
✅ Gemini LLM integration   
✅ ElevenLabs TTS  
✅ VAD with fallback  
✅ Token minting server  
✅ Frontend UI with live logs  
✅ Latency tracking per component  
✅ Interrupt handling  
✅ Structured logging  
✅ OOP with dependency injection  

### Next Steps for Production

1. **Authentication**: Use OAuth/JWT for frontend token requests (not plain endpoint)
2. **Database**: Store conversation history, user analytics
3. **Scaling**: Deploy LiveKit server, use container orchestration (K8s)
4. **Error Recovery**: Reconnection logic, exponential backoff, dead-letter queues
5. **Testing**: Add unit/integration tests for each client
6. **Monitoring**: Prometheus metrics, distributed tracing
7. **Security**: HTTPS, rate limiting, API key rotation
8. **Audio Quality**: Jitter buffer, AEC (acoustic echo cancellation), bandwidth adaptation

Good luck! 🚀
