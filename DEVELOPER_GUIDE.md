# Developer Learning Guide — LiveKit Voice Agent

> A deep technical guide covering every technology, library, and architectural decision in this project. Written for developers who want to understand the **why** and **how** behind each component.

---

## Table of Contents

1. [What is LiveKit?](#1-what-is-livekit)
2. [How LiveKit Works in a Voice Agent](#2-how-livekit-works-in-a-voice-agent)
3. [Project Architecture Overview](#3-project-architecture-overview)
4. [Full Data Flow — Three Modes](#4-full-data-flow--three-modes)
5. [Python Backend — Every Library Explained](#5-python-backend--every-library-explained)
6. [Node Token Server — Every Library Explained](#6-node-token-server--every-library-explained)
7. [React Frontend — Every Library Explained](#7-react-frontend--every-library-explained)
8. [Key Engineering Patterns](#8-key-engineering-patterns)
9. [AI / ML Providers Deep Dive](#9-ai--ml-providers-deep-dive)
10. [Audio Pipeline — How Sound Travels](#10-audio-pipeline--how-sound-travels)
11. [Why Each Design Decision Was Made](#11-why-each-design-decision-was-made)

---

## 1. What is LiveKit?

### The Simple Explanation

LiveKit is a **real-time communication infrastructure** platform. Think of it like a phone network — but for software. It lets people (and AI agents) connect together and send audio/video back and forth in real-time over the internet.

Without LiveKit (or something like it), you cannot do real human-to-AI voice conversations in a browser — the browser has no native way to stream audio to a Python server in real-time.

### The Technical Explanation

LiveKit is built on **WebRTC** (Web Real-Time Communication) — the same protocol that powers Google Meet, Zoom, and Discord.

WebRTC handles the hardest parts of real-time audio:
- **NAT traversal** — Getting through firewalls and routers
- **Jitter buffering** — Smoothing out network delays
- **Packet loss concealment** — Hiding dropped packets
- **Echo cancellation** — Removing microphone feedback
- **Noise suppression** — Filtering background noise
- **Adaptive bitrate** — Reducing quality when network is slow

LiveKit provides a **managed server (SFU — Selective Forwarding Unit)** that sits between participants and routes audio/video streams between them. You don't manage servers — LiveKit cloud does it for you.

```
Browser Mic  ──audio──►  LiveKit Cloud  ──audio──►  Python Agent
                              │
Python TTS   ──audio──►  LiveKit Cloud  ──audio──►  Browser Speakers
```

### LiveKit Concepts You Must Know

| Concept | What It Is | In This Project |
|---|---|---|
| **Room** | A virtual meeting space | `test-room` |
| **Participant** | Anyone in the room (human or bot) | Browser user + `voice-agent` |
| **Track** | A single audio or video stream | Microphone = 1 audio track |
| **Publication** | Publishing your track to the room | Agent publishes TTS audio |
| **Subscription** | Receiving someone else's track | Agent subscribes to browser mic |
| **Token (JWT)** | Proof you're allowed in the room | Minted by token-server |
| **SFU** | Server that routes tracks between participants | LiveKit Cloud |

### LiveKit vs Alternatives

| Platform | What It Is | Difference |
|---|---|---|
| **LiveKit** | Open-source WebRTC SFU, cloud hosted | Full control, Python SDK, AI-friendly |
| **Twilio** | Proprietary telecom platform | Expensive at scale, less AI integration |
| **Agora** | Proprietary RTC | Closed-source, no Python agent SDK |
| **Daily.co** | WebRTC API | Less flexible for custom AI pipelines |
| **Raw WebRTC** | Browser API | No server, impossible for P2P with AI bots |

---

## 2. How LiveKit Works in a Voice Agent

### The Problem LiveKit Solves

Without LiveKit, you'd face this impossible situation:

```
Browser Mic → ??? → Python server → ??? → Browser Speakers
```

The browser can only speak HTTP. HTTP is request-response — you send a file, you get a file back. It was never designed for continuous real-time audio streaming in both directions simultaneously.

WebRTC solves this, but raw WebRTC requires:
- Signaling server
- ICE/STUN/TURN servers for NAT traversal
- Peer-to-peer negotiation
- Codec negotiation
- Packet loss handling

LiveKit wraps all of this complexity behind a clean SDK.

### The LiveKit Architecture in This Project

```
┌─────────────────────────────────────────────────────────────────┐
│                         LiveKit Cloud                           │
│                  wss://first-5keutiq9.livekit.cloud             │
│                                                                  │
│   Participant: "user-1749830234"    Participant: "voice-agent"   │
│   (Browser)                         (Python)                    │
│                                                                  │
│   Track: mic-audio  ──────────────────────────────────────────► │
│   (browser publishes)                (Python subscribes)        │
│                                                                  │
│   Track: agent-voice ◄────────────────────────────────────────  │
│   (browser subscribes)               (Python publishes)         │
└─────────────────────────────────────────────────────────────────┘
```

### Step-by-Step: How a Voice Turn Works

```
1. Browser publishes mic track
        ↓ (WebRTC audio, ~20ms frames of 16kHz PCM)
2. LiveKit Cloud receives and routes to Python agent
        ↓
3. Python agent's receive_audio_frames() gets each 20ms frame
        ↓
4. VAD checks if the frame contains speech
        ↓ (only speech frames proceed)
5. Deepgram WebSocket receives raw PCM audio
        ↓ (streaming transcription, word by word)
6. When Deepgram detects end-of-utterance → sends final transcript
        ↓
7. Claude generates a short spoken response
        ↓
8. PyTTSX3/gTTS converts text to WAV audio bytes
        ↓
9. Python agent publishes WAV frames to LiveKit as "agent-voice" track
        ↓ (WebRTC audio, ~20ms frames)
10. LiveKit routes to browser
        ↓
11. Browser subscribes to "agent-voice" track → audio element plays
```

### The JWT Token System

LiveKit rooms are secured. To join, you need a **JWT (JSON Web Token)** — a cryptographically signed proof that you're allowed in.

```
Browser → POST /token to Token Server (Node.js)
             ↓
Token Server signs JWT with LIVEKIT_API_SECRET
             ↓
Browser receives { token: "eyJ...", url: "wss://..." }
             ↓
Browser calls room.connect(url, token)
             ↓
LiveKit Cloud verifies the JWT signature → allows room join
```

The Python agent generates its own token directly (it has the API keys) and doesn't need the token server.

---

## 3. Project Architecture Overview

### Three Services, One Pipeline

```
┌──────────────────────────────────────────────────────────────────────┐
│                                                                       │
│  ┌─────────────────────┐  ┌──────────────────┐  ┌─────────────────┐ │
│  │    Python Agent     │  │  React Frontend  │  │  Token Server   │ │
│  │    Port: 8080       │  │  Port: 5173      │  │  Port: 3001     │ │
│  │    Language: Python │  │  Language: JS    │  │  Language: Node │ │
│  └────────┬────────────┘  └────────┬─────────┘  └────────┬────────┘ │
│           │                        │                      │          │
│           │◄────── HTTP ─────────►│◄──── HTTP ──────────►│          │
│           │     /test              │      /token          │          │
│           │     /process-audio     │                      │          │
│           │     /ws (WebSocket)    │                      │          │
│           │                        │                      │          │
│           │◄─────────── LiveKit Cloud ───────────────────►│          │
│           │         WebRTC (real-time audio)              │          │
│                                                                       │
│                    ┌──────────────────────┐                          │
│                    │   External APIs       │                          │
│                    │ - Deepgram (STT)      │                          │
│                    │ - Anthropic (Claude)  │                          │
│                    │ - LiveKit Cloud       │                          │
│                    └──────────────────────┘                          │
└──────────────────────────────────────────────────────────────────────┘
```

### File Structure Explained

```
src/
├── main.py                    ← HTTP server + reconnection loop
└── agent/
    ├── config.py              ← All settings from .env
    ├── voice_agent.py         ← The main orchestrator (conductor)
    ├── livekit_client.py      ← WebRTC audio send/receive
    ├── vad.py                 ← Is this frame speech or silence?
    ├── ws_logger.py           ← Stream events to frontend
    └── clients/               ← One file per external service
        ├── deepgram_client.py     ← REST: transcribe a file
        ├── deepgram_ws_client.py  ← WebSocket: stream transcription
        ├── claude_client.py       ← Anthropic Claude LLM
        ├── gemini_client.py       ← Google Gemini LLM
        ├── pyttsx3_client.py      ← Offline TTS (no API key)
        ├── gtts_client.py         ← Free TTS (Google Translate)
        ├── google_tts_client.py   ← Google Cloud TTS (paid)
        └── elevenlabs_client.py   ← ElevenLabs TTS (premium)

token-server/
└── index.js                   ← Express server, JWT minting only

frontend/src/
├── App.jsx                    ← All React UI + LiveKit client logic
└── styles.css                 ← Dark theme, pipeline visualization
```

---

## 4. Full Data Flow — Three Modes

### Mode 1: Quick Text Test

```
User types "What is Python?"
      ↓
POST http://localhost:8080/test
      { "text": "What is Python?" }
      ↓
[main.py] handle_test_pipeline()
      ↓
[claude_client.py] AsyncAnthropic.messages.create(...)
      ← "Python is a high-level programming language..."
      ↓
[ws_logger] broadcast: { event_type: "llm_end", duration_ms: 1700 }
      ↓ (frontend log panel updates)
[pyttsx3_client.py] run_in_executor(_synthesize_sync)
      ← WAV bytes (audio file in memory)
      ↓
[ws_logger] broadcast: { event_type: "tts_end", audio_bytes: 85000 }
      ↓ (frontend pipeline panel updates)
HTTP response: WAV audio bytes
      ↓
[App.jsx] URL.createObjectURL(blob) → <audio>.play()
      ← User hears the response
```

### Mode 2: Voice Recording (mic → STT → LLM → TTS)

```
User clicks "Start Recording"
      ↓
[App.jsx] navigator.mediaDevices.getUserMedia({ audio: true })
      ↓
MediaRecorder records WebM/Opus audio in 100ms chunks
      ↓
User clicks "Stop Recording"
      ↓
Blob assembled from chunks (type: audio/webm;codecs=opus)
      ↓
FormData: audio field = recording.webm
      ↓
POST http://localhost:8080/process-audio
      ↓
[main.py] reads multipart audio bytes
      ↓
[deepgram_client.py] POST https://api.deepgram.com/v1/listen
      ← { transcript: "What is Python?" }
      ↓
[ws_logger] broadcast: { event_type: "stt_end", transcript: "..." }
      ↓
[voice_agent.py] _process_transcript("What is Python?")
      ↓
[claude_client.py] → response text
      ↓
[pyttsx3_client.py] → WAV bytes
      ↓
HTTP response: WAV bytes + header X-Transcript: "What is Python?"
      ↓
[App.jsx] plays audio, logs transcript
```

### Mode 3: Real-Time LiveKit Voice

```
User clicks "Connect"
      ↓
[App.jsx] POST http://localhost:3001/token
      { room: "test-room", identity: "user-1234567890" }
      ↓
[index.js] AccessToken.toJwt() → signed JWT
      ← { token: "eyJhbGci...", url: "wss://..." }
      ↓
[App.jsx] room.connect(url, token)
      ↓ (WebRTC handshake with LiveKit Cloud)
[App.jsx] createLocalAudioTrack() → room.localParticipant.publishTrack()
      ↓ (browser mic now streaming to LiveKit)

SIMULTANEOUSLY, Python agent:
      ↓
[livekit_client.py] connect() → joins same room as "voice-agent"
      ↓
[livekit_client.py] publishes "agent-voice" AudioTrack
      ↓ (browser's TrackSubscribed fires → attachAgentAudio())
[voice_agent.py] handle_call()
      ↓
[deepgram_ws_client.py] connect() → wss://api.deepgram.com/v1/listen
      ↓ (WebSocket open — ready to receive audio)
[livekit_client.py] receive_audio_frames(on_frame)
      ↓ (loop: every 20ms, get PCM frame from browser mic)

USER SPEAKS:
      ↓
AudioFrame (20ms PCM @ 16kHz mono)
      ↓
[vad.py] is_speech(frame) → True (frame is not silent)
      ↓
[deepgram_ws_client.py] send_audio(frame)
      ↓ (raw bytes sent over Deepgram WebSocket)

After ~1 second of silence:
Deepgram sends: { is_final: true, channel: { alternatives: [{ transcript: "Hello" }] } }
      ↓
[voice_agent.py] on_transcript() → "Hello" (not empty, is_final=true)
      ↓
[voice_agent.py] _process_transcript("Hello")
      ↓
[claude_client.py] → "Hi there! How can I help you today?"
      ↓
[pyttsx3_client.py] → WAV bytes
      ↓
[livekit_client.py] send_audio(wav_bytes)
      → parse WAV → extract PCM → split into 20ms frames
      → each frame: AudioSource.capture_frame(AudioFrame)
      ↓ (frames flow through LiveKit to browser)
[App.jsx] <audio> element plays — user hears agent response
```

---

## 5. Python Backend — Every Library Explained

### `aiohttp` — Async HTTP Server and Client

**What it is:** An HTTP library built entirely for Python's `asyncio`. Regular `requests` is blocking (freezes the event loop). `aiohttp` is non-blocking.

**Used for:**
1. Running the HTTP API server on port 8080
2. Making HTTP requests to Deepgram REST API
3. Opening WebSocket connection to Deepgram streaming API

```python
# As a server:
app = web.Application()
app.router.add_post("/test", handle_test_pipeline)
runner = web.AppRunner(app)
await runner.setup()
await web.TCPSite(runner, "localhost", 8080).start()

# As an HTTP client:
async with aiohttp.ClientSession() as session:
    async with session.post(url, data=audio_bytes, headers=headers) as resp:
        data = await resp.json()

# As a WebSocket client:
self._ws = await self._session.ws_connect(url, headers=headers)
async for msg in self._ws:
    if msg.type == aiohttp.WSMsgType.TEXT:
        data = msg.json()
```

**Why not Flask/FastAPI?**
Flask and FastAPI use WSGI/ASGI — they're designed for request-response. `aiohttp` natively supports long-running WebSocket connections and concurrent async tasks alongside the HTTP server in the same event loop — which is critical when the agent is also running LiveKit in the same process.

---

### `asyncio` — Python's Async Event Loop

**What it is:** Python's built-in library for writing concurrent code using `async/await`. Instead of using threads, asyncio runs everything in a single thread using cooperative multitasking.

**Key concepts in this project:**

```python
# Run a coroutine (async function)
await some_async_function()

# Create a background task (fire and forget)
asyncio.create_task(some_coroutine())

# Run blocking code without freezing the event loop
loop = asyncio.get_event_loop()
result = await loop.run_in_executor(None, blocking_function, args)

# Keep the loop alive
while self._connected:
    await asyncio.sleep(0.5)  # yield control, don't busy-wait
```

**The Golden Rule:** Never block the event loop. If a function takes more than a few milliseconds (file I/O, pyttsx3 synthesis, gTTS network call), it MUST run in `run_in_executor()`.

---

### `pydantic` and `pydantic-settings` — Configuration and Validation

**What it is:** Pydantic validates Python data against type annotations at runtime. `pydantic-settings` extends it to read from `.env` files and environment variables.

```python
from pydantic_settings import BaseSettings
from pydantic import Field

class AgentConfig(BaseSettings):
    DEEPGRAM_API_KEY: str          # required — will raise if missing
    LIVEKIT_ROOM: str = "test-room"  # optional with default

    class Config:
        env_file = ".env"
```

When you call `AgentConfig()`, it automatically reads `.env`, maps variables by name, validates types, and raises a clear error if something required is missing. No more `os.environ.get("KEY", "")` and silent failures.

---

### `python-dotenv` — Environment File Loader

**What it is:** Reads key=value pairs from a `.env` file and loads them into `os.environ`.

```python
from dotenv import load_dotenv
load_dotenv()  # reads .env, sets os.environ
```

This runs before `AgentConfig()` so pydantic-settings can find the values. The `.env` file is never committed to git — the `.env.example` shows what keys are needed.

---

### `livekit` and `livekit-agents` — Python LiveKit SDK

**What it is:** The official Python SDK for LiveKit. Provides `livekit.rtc` (real-time communication) and `livekit.api` (token generation and management).

**Core Classes Used:**

```python
from livekit import rtc
from livekit.api import AccessToken, VideoGrants

# Room — the connection to LiveKit Cloud
room = rtc.Room()
await room.connect(url, token)

# AudioSource — where you push audio TO LiveKit
src = rtc.AudioSource(sample_rate=22050, num_channels=1)

# LocalAudioTrack — wraps the source into a publishable track
track = rtc.LocalAudioTrack.create_audio_track("agent-voice", src)
await room.local_participant.publish_track(track)

# AudioFrame — one chunk of raw PCM audio
frame = rtc.AudioFrame(
    data=pcm_bytes,           # raw signed 16-bit samples
    sample_rate=22050,        # Hz
    num_channels=1,           # mono
    samples_per_channel=480,  # 20ms at 24kHz
)
await src.capture_frame(frame)  # push to LiveKit

# AudioStream — receive audio FROM a remote track
stream = rtc.AudioStream(remote_track, sample_rate=16000, num_channels=1)
async for event in stream:
    if isinstance(event, rtc.AudioFrameEvent):
        pcm_bytes = bytes(event.frame.data)

# Event system
@room.on("track_subscribed")
def handler(track, publication, participant):
    pass

@room.on("disconnected")
def handler(reason=None):
    pass
```

**Token Generation (Agent Side):**
```python
from livekit.api import AccessToken, VideoGrants

token = (
    AccessToken(api_key=LIVEKIT_API_KEY, api_secret=LIVEKIT_API_SECRET)
    .with_identity("voice-agent")
    .with_grants(VideoGrants(room_join=True, room="test-room", can_publish=True, can_subscribe=True))
    .to_jwt()
)
```

---

### `anthropic` — Claude LLM SDK

**What it is:** Anthropic's official Python SDK for the Claude API. Uses `AsyncAnthropic` for non-blocking API calls.

```python
import anthropic

client = anthropic.AsyncAnthropic(api_key=api_key)

message = await client.messages.create(
    model="claude-sonnet-4-0",
    max_tokens=150,           # keep voice replies short
    system="You are a voice assistant. Reply in 1-2 sentences.",
    messages=[
        {"role": "user", "content": "What is Python?"}
    ],
)

response_text = message.content[0].text
```

**Why `AsyncAnthropic` not `Anthropic`?**
`Anthropic` (sync) uses `requests` internally — it blocks the event loop for the entire API call (~1-2 seconds). `AsyncAnthropic` uses `httpx` with async — the event loop stays responsive during the API call.

**Why `max_tokens=150`?**
Voice responses must be short. 150 tokens ≈ 2-3 sentences. Long LLM responses would take 3+ seconds to synthesize into speech, making the conversation feel unnatural.

---

### `pyttsx3` — Offline Text-to-Speech

**What it is:** A cross-platform TTS library that uses the operating system's built-in speech engine. On Windows it uses SAPI5, on macOS it uses NSSpeechSynthesizer, on Linux it uses eSpeak. Zero cost, zero API key, works offline.

```python
import pyttsx3

engine = pyttsx3.init()
engine.setProperty("rate", 175)    # words per minute
engine.setProperty("volume", 1.0)  # 0.0 to 1.0

# Save speech to a WAV file
engine.save_to_file("Hello world", "/tmp/output.wav")
engine.runAndWait()  # blocking! run in executor
engine.stop()
```

**Critical issue — Why it must run in executor:**
`pyttsx3.runAndWait()` blocks the calling thread until synthesis is complete. On a long string, this takes 5-20 seconds. If called directly in an async function, the entire event loop freezes — no HTTP requests can be served, no LiveKit frames can be received. Solution:

```python
async def synthesize(self, text: str) -> bytes:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self._synthesize_sync, text)
```

`run_in_executor` runs `_synthesize_sync` in a thread pool. The event loop continues handling other work while the thread synthesizes audio.

**Why create a new engine per call?**
`pyttsx3` has COM threading issues on Windows — reusing the same engine across async calls causes crashes. Creating a new engine per synthesis call is safer.

---

### `gTTS` — Google Translate Text-to-Speech

**What it is:** A wrapper around the unofficial Google Translate TTS endpoint. Sends text to Google and gets MP3 audio back. Free, natural-sounding, but requires internet.

```python
from gtts import gTTS
import io

tts = gTTS(text="Hello world", lang="en", slow=False)
buf = io.BytesIO()
tts.write_to_fp(buf)   # blocking network call — run in executor
audio_bytes = buf.getvalue()
```

**Same executor pattern as pyttsx3** — `write_to_fp()` makes a blocking HTTP request.

---

### `webrtcvad` — Voice Activity Detection

**What it is:** A Python wrapper around Google's WebRTC Voice Activity Detection algorithm. Analyzes a 10/20/30ms frame of PCM audio and returns True if speech is detected.

```python
import webrtcvad

vad = webrtcvad.Vad(aggressiveness=2)  # 0=least, 3=most aggressive
is_speech = vad.is_speech(frame_bytes, sample_rate=16000)
```

**Why VAD?**
Without VAD, every 20ms of audio (including silence) would be sent to Deepgram's WebSocket. This:
- Wastes API quota
- Makes Deepgram produce empty transcripts continuously
- Wastes bandwidth

With VAD, only frames where the user is actually speaking are forwarded to Deepgram. The fallback (when webrtcvad is not installed) passes all non-empty frames through — less efficient but functional.

**Aggressiveness levels:**
- 0 — Liberal, captures almost all audio (lots of false positives)
- 1 — Moderate
- 2 — Standard (used here)
- 3 — Aggressive, only very clear speech passes (misses quiet voices)

---

### `wave` — WAV File Parser (Python Standard Library)

**What it is:** Python's built-in WAV file reader. Used in `livekit_client.py` to parse TTS output before streaming to LiveKit.

```python
import wave
import io

with wave.open(io.BytesIO(audio_bytes)) as wf:
    sample_rate = wf.getframerate()   # e.g., 22050 Hz
    num_channels = wf.getnchannels()  # 1 = mono
    sampwidth = wf.getsampwidth()     # 2 = 16-bit
    pcm_data = wf.readframes(wf.getnframes())  # raw PCM bytes
```

LiveKit's `AudioFrame` requires raw PCM (no headers) — the WAV header must be stripped. `wave` does this parsing.

---

### `numpy` — Numerical Arrays

**What it is:** The fundamental Python library for numerical computation. Used here for audio sample manipulation.

Audio PCM data is a sequence of 16-bit integer samples. numpy makes it easy to reshape, convert, and slice this data efficiently.

---

## 6. Node Token Server — Every Library Explained

### `express` — HTTP Framework

**What it is:** The most popular Node.js web framework. Minimal and flexible.

```javascript
const express = require('express')
const app = express()

app.use(express.json())  // parse JSON request bodies

app.post('/token', (req, res) => {
    const { room, identity } = req.body
    res.json({ token: jwt, url: wsUrl })
})

app.listen(3001)
```

**Why a separate Node.js service for tokens?**
The Python agent already handles all AI processing. Token generation is a simple operation but requires `livekit-server-sdk` which has the best support in JavaScript/TypeScript. Keeping it separate also means the frontend can always get tokens even if the Python agent is restarting.

---

### `livekit-server-sdk` (Node.js) — JWT Token Generation

**What it is:** The official LiveKit server SDK for Node.js. Used to mint short-lived JWT access tokens.

```javascript
const { AccessToken } = require('livekit-server-sdk')

const token = new AccessToken(LIVEKIT_API_KEY, LIVEKIT_API_SECRET, {
    identity: "user-123",
    name: "User",
})

token.addGrant({
    room: "test-room",
    roomJoin: true,
    canPublish: true,    // user can send their mic
    canSubscribe: true,  // user can hear others
})

const jwt = token.toJwt()
// eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**How JWT security works:**
- The token is signed with `LIVEKIT_API_SECRET` (HMAC-SHA256)
- Anyone who modifies the token (e.g., changes the room name) breaks the signature
- LiveKit Cloud verifies the signature on every connection attempt
- Tokens are short-lived — they expire after a set time

---

### `cors` — Cross-Origin Resource Sharing

**What it is:** Express middleware that adds CORS headers to responses.

**Why needed:** Browsers block JavaScript from making HTTP requests to a different domain/port than the page was served from (Same-Origin Policy). The frontend runs on port 5173, the token server on port 3001 — different ports = different origins = blocked by default.

```javascript
const cors = require('cors')
app.use(cors())  // allows all origins — fine for local dev
```

---

### `dotenv` (Node.js) — Environment Variables

**What it is:** Same concept as Python's `python-dotenv`. Reads `.env` and populates `process.env`.

```javascript
require('dotenv').config()
const API_KEY = process.env.LIVEKIT_API_KEY
```

---

## 7. React Frontend — Every Library Explained

### `react` and `react-dom` — UI Framework

**What it is:** Facebook's JavaScript library for building user interfaces. Components are functions that return JSX (HTML-like syntax). State changes trigger re-renders automatically.

**Hooks used in this project:**

```javascript
// useState — reactive state variables
const [connected, setConnected] = useState(false)
// When setConnected(true) is called, React re-renders the component

// useRef — persistent values that DON'T trigger re-render
const roomRef = useRef(null)       // holds LiveKit Room object
const agentAudioSids = useRef(new Set())  // holds track SID set
// roomRef.current = room  → no re-render, value persists

// useEffect — side effects (run after render, on mount/unmount)
useEffect(() => {
    const ws = new WebSocket('ws://localhost:8080/ws')
    ws.onmessage = handler
    return () => ws.close()  // cleanup on unmount
}, [])  // [] = run once on mount

// useCallback — memoized function (prevents recreation on every render)
const addLog = useCallback((msg, type) => {
    setLogs(s => [...s.slice(-200), { msg, type }])
}, [])
```

**Why `useRef` for the Room object and not `useState`?**
`useState` triggers a re-render every time the value changes. The LiveKit Room object should not cause re-renders — it's a complex object with its own event system. `useRef` stores it persistently without triggering re-renders.

---

### `livekit-client` — Browser LiveKit SDK

**What it is:** The official LiveKit JavaScript/TypeScript SDK for browsers. Handles WebRTC negotiation, track management, and room events.

```javascript
import { Room, RoomEvent, Track, createLocalAudioTrack } from 'livekit-client'

// Create a room instance
const room = new Room()

// Register event handlers BEFORE connecting
room.on(RoomEvent.TrackSubscribed, (track, publication, participant) => {
    // Called when a remote participant publishes a track
    if (track.kind === Track.Kind.Audio) {
        const audioElement = track.attach()  // creates <audio> element
        audioElement.autoplay = true
        document.body.appendChild(audioElement)
    }
})

room.on(RoomEvent.Disconnected, () => {
    setConnected(false)
})

// Connect to LiveKit Cloud
await room.connect(wsUrl, jwtToken, { autoSubscribe: true })

// Publish your microphone
const micTrack = await createLocalAudioTrack()
await room.localParticipant.publishTrack(micTrack)

// Check already-existing participants
room.remoteParticipants.forEach(participant => {
    participant.trackPublications.forEach(pub => {
        if (pub.track) {
            // handle existing published track
        }
    })
})
```

**Key RoomEvents:**

| Event | When It Fires |
|---|---|
| `RoomEvent.Connected` | Successfully joined the room |
| `RoomEvent.Disconnected` | Kicked or network lost |
| `RoomEvent.ParticipantConnected` | New participant joined |
| `RoomEvent.ParticipantDisconnected` | A participant left |
| `RoomEvent.TrackSubscribed` | A remote track is ready to consume |
| `RoomEvent.TrackUnsubscribed` | A remote track was removed |

**`autoSubscribe: true`** — automatically subscribes to all tracks that remote participants publish. Without this, you'd have to manually call `subscribe()` on each track.

**`track.attach()`** — LiveKit's SDK creates an `<audio>` or `<video>` DOM element, connects it to the WebRTC media stream, and returns it. You just append it to the document.

---

### `MediaRecorder` API — Browser Recording

**What it is:** A built-in browser API (no library needed) for recording audio/video from a MediaStream.

```javascript
// Get microphone access
const stream = await navigator.mediaDevices.getUserMedia({ audio: true })

// Find best supported format
const mimeType = ['audio/webm;codecs=opus', 'audio/webm', 'audio/ogg']
    .find(t => MediaRecorder.isTypeSupported(t)) || ''

// Start recording
const recorder = new MediaRecorder(stream, mimeType ? { mimeType } : {})
const chunks = []

recorder.ondataavailable = e => {
    if (e.data.size > 0) chunks.push(e.data)
}
recorder.onstop = () => {
    const blob = new Blob(chunks, { type: recorder.mimeType })
    // blob contains the full recording as WebM/Opus audio
}

recorder.start(100)  // fire ondataavailable every 100ms
```

**Why `audio/webm;codecs=opus` not `audio/wav`?**
Browsers cannot record WAV natively. The MediaRecorder API produces compressed formats: WebM (Opus codec on Chrome/Firefox) or OGG. The mimeType is auto-detected from what the browser supports — Deepgram's REST API accepts all these formats.

---

### `Vite` — Frontend Build Tool

**What it is:** A next-generation JavaScript bundler and dev server. Much faster than Webpack because it uses native ES modules and only transpiles what's needed.

```bash
npm run dev     # starts dev server on port 5173 with HMR
npm run build   # bundles for production into frontend/dist/
```

**HMR (Hot Module Replacement):** When you edit a `.jsx` file, Vite updates the browser instantly without a full page refresh. React state is preserved.

---

### WebSocket (Browser Built-in) — Backend Event Streaming

**What it is:** A persistent full-duplex connection between browser and server. Unlike HTTP (request-response), WebSocket keeps the connection open so the server can push data at any time.

```javascript
const ws = new WebSocket('ws://localhost:8080/ws')

ws.onopen = () => console.log('connected')
ws.onmessage = ({ data }) => {
    const event = JSON.parse(data)
    // { event_type: "llm_end", duration_ms: 1732, data: { response: "..." } }
}
ws.onclose = () => console.log('disconnected')
```

Used to receive real-time pipeline events (STT timing, LLM timing, TTS timing) from the Python agent and display them in the UI without polling.

---

## 8. Key Engineering Patterns

### Pattern 1: The Async/Executor Bridge

The fundamental tension: asyncio is single-threaded and non-blocking, but some libraries (pyttsx3, gTTS) are blocking and call into C code or make synchronous network requests.

```python
# WRONG — freezes event loop for 3-20 seconds
async def synthesize(self, text):
    engine = pyttsx3.init()
    engine.save_to_file(text, "/tmp/out.wav")
    engine.runAndWait()  # BLOCKS the event loop!

# CORRECT — runs blocking code in thread pool
async def synthesize(self, text):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self._synthesize_sync, text)
    # event loop is free during synthesis — handles other requests

def _synthesize_sync(self, text):  # this runs in a thread
    engine = pyttsx3.init()
    engine.save_to_file(text, "/tmp/out.wav")
    engine.runAndWait()  # fine to block inside a thread
```

### Pattern 2: Reconnection Loop

The agent must stay alive even when LiveKit disconnects. The pattern: wrap the core logic in a `while True` loop, catch exceptions, wait, retry.

```python
# HTTP server starts once and stays running forever
runner = web.AppRunner(app)
await runner.setup()
await web.TCPSite(runner, "localhost", 8080).start()

# Agent reconnects indefinitely without killing the HTTP server
while True:
    try:
        await agent.handle_call()     # runs until disconnect
        await asyncio.sleep(3)        # clean reconnect
    except asyncio.CancelledError:
        break
    except Exception as e:
        logging.error(f"Agent error: {e}")
        await asyncio.sleep(5)        # error reconnect
```

### Pattern 3: Event Registration Before Connection

**The critical timing bug:** If you register an event handler AFTER connecting, you miss events that fired during the connection process.

```javascript
// WRONG — might miss TrackSubscribed if agent already in room
await room.connect(url, token)
room.on(RoomEvent.TrackSubscribed, handler)  // too late!

// CORRECT — always register before connect
room.on(RoomEvent.TrackSubscribed, handler)  // registered first
await room.connect(url, token)               // now connects
// + iterate existing participants for tracks already published:
room.remoteParticipants.forEach(p => {
    p.trackPublications.forEach(pub => {
        if (pub.track) handler(pub.track, pub, p)
    })
})
```

### Pattern 4: Deduplication via Set

The agent publishes a new audio track every time it reconnects. The browser's `TrackSubscribed` fires for each new track. Without deduplication, multiple `<audio>` elements stack up.

```javascript
const agentAudioSids = useRef(new Set())  // persists across re-renders

function attachAgentAudio(track) {
    if (agentAudioSids.current.has(track.sid)) return  // already attached
    agentAudioSids.current.add(track.sid)
    const el = track.attach()
    el.autoplay = true
    document.body.appendChild(el)
}

// On disconnect, clear the set so reconnects work
agentAudioSids.current.clear()
```

### Pattern 5: Lazy Imports

Some dependencies (Gemini, ElevenLabs, Google Cloud TTS) pull in heavy packages with Pydantic v1 imports that cause warnings on Python 3.14. Load them only when they're actually needed.

```python
# WRONG — imports everything at startup, even unused providers
from agent.clients.gemini_client import GeminiClient      # Pydantic v1 warning!
from agent.clients.elevenlabs_client import ElevenLabsTTS

# CORRECT — import only what the user configured
if cfg.LLM_PROVIDER.lower() == "claude":
    from agent.clients.claude_client import ClaudeClient
    llm = ClaudeClient(cfg.ANTHROPIC_API_KEY, cfg.CLAUDE_MODEL)
elif cfg.LLM_PROVIDER.lower() == "gemini":
    from agent.clients.gemini_client import GeminiClient  # only if needed
    llm = GeminiClient(cfg.GEMINI_API_KEY, cfg.MODEL_GEMINI)
```

### Pattern 6: Global Singleton for Cross-Module Communication

The `ws_logger` needs to be shared between `voice_agent.py`, `main.py`, and the HTTP WebSocket handler. A module-level singleton avoids passing it through every constructor.

```python
# ws_logger.py
_ws_logger = None

def get_ws_logger():
    global _ws_logger
    if _ws_logger is None:
        _ws_logger = WebSocketLogger()
    return _ws_logger

# voice_agent.py
from .ws_logger import get_ws_logger
self.ws_logger = get_ws_logger()  # always returns same instance

# main.py
from agent.ws_logger import get_ws_logger
ws_logger = get_ws_logger()
ws_logger.subscribe(broadcast_to_all_frontend_clients)
```

---

## 9. AI / ML Providers Deep Dive

### Deepgram — Speech-to-Text

**What it is:** A deep learning STT service. Far more accurate than Google's free STT, supports streaming, and handles diverse accents and audio quality well.

**Two modes used in this project:**

| Mode | Client | When Used | How |
|---|---|---|---|
| REST | `deepgram_client.py` | Voice Recording upload | POST audio file → get transcript |
| WebSocket | `deepgram_ws_client.py` | LiveKit real-time | Stream PCM frames → get transcript as you speak |

**WebSocket Parameters:**
```
wss://api.deepgram.com/v1/listen
  ?encoding=linear16       # raw signed 16-bit PCM (no header)
  &sample_rate=16000       # 16kHz
  &channels=1              # mono
  &interim_results=true    # send partial transcripts as user speaks
  &utterance_end_ms=1000   # declare utterance complete after 1s silence
                           # (requires interim_results=true)
  &punctuate=true          # add periods/commas for cleaner LLM input
```

**Why `interim_results=true`?**
Without it, Deepgram only sends a transcript when it detects a long pause. With it, Deepgram sends partial results continuously so you can show them on screen and detect end-of-utterance faster. The `is_final: true` flag tells you when a final transcript is ready to process.

**Deepgram Response Format:**
```json
{
  "type": "Results",
  "is_final": true,
  "speech_final": true,
  "channel": {
    "alternatives": [{
      "transcript": "What is the capital of France?",
      "confidence": 0.99,
      "words": [...]
    }]
  },
  "duration": 2.4
}
```

---

### Anthropic Claude — Large Language Model

**What it is:** Anthropic's family of large language models. The most capable model for conversational voice because it follows precise instructions about response length and format.

**Model used:** `claude-sonnet-4-0`
- Sonnet = balanced speed vs. capability (not the slowest, not the fastest)
- Turnaround: ~1-2 seconds for a short voice response

**System Prompt Design for Voice:**
```python
_VOICE_SYSTEM_PROMPT = (
    "You are a helpful voice assistant. "
    "Keep every reply under 2 sentences — short, clear, and conversational. "
    "No lists, no markdown, no preamble."
)
```

**Why these constraints?**
- Lists and markdown look terrible when converted to speech: "asterisk asterisk item one asterisk asterisk"
- Long responses take 3-10 seconds to synthesize — the conversation feels broken
- "No preamble" prevents "Certainly! I'd be happy to help you with that." before every answer

**API Call:**
```python
message = await client.messages.create(
    model="claude-sonnet-4-0",
    max_tokens=150,          # ~2 sentences max
    system=_VOICE_SYSTEM_PROMPT,
    messages=[
        {"role": "user", "content": "What is Python?"}
    ],
)
text = message.content[0].text
```

---

### TTS Providers Comparison

| Provider | Quality | Latency | Cost | Requires Network |
|---|---|---|---|---|
| **PyTTSX3** | Robotic | 1-3s | Free | No (offline) |
| **gTTS** | Natural | 2-4s | Free | Yes |
| **Google Cloud TTS** | Very natural | 0.5-1s | ~$4/1M chars | Yes |
| **ElevenLabs** | Human-like | 0.3-0.8s | ~$0.30/1K chars | Yes |

**For development:** PyTTSX3 (no API key, instant setup)
**For production:** ElevenLabs or Google Cloud TTS (best quality + speed)

---

## 10. Audio Pipeline — How Sound Travels

### Audio Format Conversions

Sound goes through multiple format conversions in this pipeline:

```
Browser Mic
   ↓ (WebM Opus, compressed) — MediaRecorder
LiveKit Cloud
   ↓ (decoded to PCM) — LiveKit's codec layer
Python Agent receive_audio_frames()
   ↓ (16kHz mono signed 16-bit PCM) — resampled by AudioStream
VAD is_speech()
   ↓ (same 16kHz PCM)
Deepgram WebSocket send_audio()
   ↓ (sends raw PCM bytes)
Deepgram Cloud → transcript text

Claude API → response text

TTS synthesize()
   ↓ (WAV file: header + raw PCM @ 22050Hz or 24kHz)
livekit_client send_audio()
   ↓ (strips WAV header, reads PCM)
   ↓ (splits into 20ms = 480 samples per frame @ 24kHz)
AudioSource capture_frame(AudioFrame)
   ↓ (LiveKit encodes to Opus, sends via WebRTC)
LiveKit Cloud
   ↓ (routes to browser)
Browser <audio> element
   ↓ (decoded from Opus, played through speakers)
User hears response
```

### Sample Rates Explained

| Rate | Used Where | Why |
|---|---|---|
| **16000 Hz (16kHz)** | Deepgram input | Voice intelligibility range; Deepgram requires it |
| **22050 Hz** | PyTTSX3 output | Standard for TTS engines |
| **24000 Hz** | Google TTS / ElevenLabs | Higher quality TTS |
| **48000 Hz** | Browser mic raw | Web Audio API default |

LiveKit's `AudioStream` automatically resamples from the browser's native rate to whatever you specify (`sample_rate=16000`). This is why Deepgram always receives the correct format.

### What is PCM?

PCM (Pulse-Code Modulation) is the simplest audio format — just raw numbers:
- Each number = the amplitude of the sound wave at that moment
- `sample_rate=16000` = 16,000 numbers per second
- `num_channels=1` = mono (one set of numbers, not stereo)
- `sampwidth=2` = each number is 2 bytes (16-bit signed integer, range -32768 to 32767)

A 1-second audio clip at 16kHz mono 16-bit = 16000 × 2 = **32,000 bytes** = ~31 KB.

A 20ms frame = 0.02s × 16000 samples × 2 bytes = **640 bytes** — this is the unit LiveKit delivers to `on_frame()`.

---

## 11. Why Each Design Decision Was Made

### Why Python for the Agent?

Python has the best AI/ML library ecosystem. The `anthropic` SDK, `livekit` SDK, `deepgram` integrations, and all TTS libraries have first-class Python support. The async ecosystem (`aiohttp`, `asyncio`) is mature enough for this use case.

### Why a Separate Node.js Token Server?

1. `livekit-server-sdk` has a more mature and better-maintained JavaScript version
2. Separates concerns: AI logic vs. auth logic
3. The frontend can always get tokens even when the Python agent is restarting
4. In production, you'd integrate this into your main backend (Next.js, Express, etc.)

### Why WebSocket for Events (not HTTP polling)?

HTTP polling (`setInterval(() => fetch('/events'), 500)`) has a minimum delay of 500ms+ and wastes bandwidth with constant requests. WebSocket keeps one persistent connection — events arrive within milliseconds of happening, with no extra overhead.

### Why `interim_results=true` in Deepgram?

The `utterance_end_ms=1000` parameter (end-of-utterance detection after 1 second of silence) only works when `interim_results=true`. Deepgram's own documentation states these two parameters must be used together. With just `interim_results=false`, you lose the ability to set a custom silence timeout.

### Why `max_tokens=150` for Claude?

Higher max_tokens means:
- Longer responses → more TTS synthesis time (3-10s+)
- Longer audio → longer for user to wait before speaking again
- Natural conversation requires short, snappy responses

150 tokens ≈ 100-120 English words ≈ 45-60 seconds of speech at normal pace — already more than needed. 2 sentences ≈ 30-50 tokens.

### Why pyttsx3 as the Default TTS?

Local development benefit: zero setup, zero cost, zero API keys. It's robotic but functional. The architecture makes it trivial to swap — just change `TTS_PROVIDER` in `.env`.

### Why aiohttp instead of FastAPI?

Both would work. `aiohttp` was chosen because:
1. Its WebSocket server implementation is tightly integrated with the same event loop that runs LiveKit and Deepgram
2. No extra ASGI server (uvicorn) needed — simpler process model
3. The project predates the FastAPI dominance — aiohttp is battle-tested

---

## Summary: The Big Picture

```
REAL-TIME VOICE CONVERSATION = 5 technologies working together:

1. WebRTC (LiveKit)     — sends audio frames in real-time between browser and agent
2. Deepgram WebSocket   — converts streaming PCM audio to text as the user speaks
3. Claude API           — turns the transcript into a natural language response
4. PyTTSX3/gTTS/ElevenLabs — converts the response text into audio bytes
5. LiveKit (publish)    — streams the audio response back to the browser

SUPPORTING INFRASTRUCTURE:

6. aiohttp              — HTTP server + async HTTP/WebSocket client
7. asyncio              — keeps all 5 concurrent tasks running without threads
8. pydantic-settings    — loads and validates all config from .env
9. JWT / livekit-server-sdk — proves to LiveKit who is allowed in the room
10. React + livekit-client  — browser UI that connects to the room and plays audio
```

---

*Built by [Muhammad Nadeem](https://nadeem.cloud) — AI / ML Engineer*
*[LinkedIn](https://www.linkedin.com/in/muhammad-nadeem-ai-ml-engineer/) · [GitHub](https://github.com/NadeemMughal)*
