LiveKit Voice Agent — Frontend (React + Vite)

This small frontend connects to a LiveKit room and publishes your microphone.

Setup

1. Install dependencies

```bash
cd "d:/LiveKit Voice Agent/frontend"
npm install
```

2. Run dev server

```bash
npm run dev
```

Usage

- Get a valid LiveKit access token for the room you want to join. For testing,
  you can create a token on a trusted server using your `LIVEKIT_API_KEY` and
  `LIVEKIT_API_SECRET` (do not embed secrets in the frontend).
- Paste `LiveKit URL` (e.g. `wss://livekit.example`) and the token into the UI,
  then click `Connect & Publish Mic`.

Notes

- This is a simple test UI — it expects a working LiveKit token. The agent
  backend should join the same room and handle the audio (STT/LLM/TTS).
- For production use, create a backend endpoint that mints short-lived tokens
  and returns them to the frontend; never expose your LiveKit secret in the
  browser.
