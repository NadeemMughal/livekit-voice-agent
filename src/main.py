"""Entry point for the Voice Agent.

Loads config, wires up components, starts the HTTP test-API and the LiveKit listener.
Run: python src/main.py
"""
import asyncio
import logging
import sys
import json
from dotenv import load_dotenv
from aiohttp import web

from agent.config import AgentConfig
from agent.clients.deepgram_client import DeepgramClient
from agent.clients.deepgram_ws_client import DeepgramWebsocketClient
from agent.vad import VAD
from agent.livekit_client import LiveKitClient
from agent.voice_agent import VoiceAgent


def setup_logging():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    )


# ── globals ───────────────────────────────────────────────────────────────────
_agent: VoiceAgent | None = None
_tts_mime_type: str = "audio/wav"
_ws_clients: list = []


# ── helpers ───────────────────────────────────────────────────────────────────
def _cors(extra: dict | None = None) -> dict:
    h = {
        "Access-Control-Allow-Origin": "*",
        "Access-Control-Allow-Methods": "GET, POST, OPTIONS",
        "Access-Control-Allow-Headers": "Content-Type",
    }
    if extra:
        h.update(extra)
    return h


async def broadcast_log_event(event_data: dict):
    if not _ws_clients:
        return
    msg = json.dumps(event_data)
    for ws in list(_ws_clients):
        if not ws.closed:
            try:
                await ws.send_str(msg)
            except Exception:
                pass


# ── HTTP handlers ─────────────────────────────────────────────────────────────
async def handle_options(request):
    return web.Response(headers=_cors())


async def handle_health(request):
    return web.json_response({"status": "ok"}, headers=_cors())


async def handle_ws_logs(request):
    ws = web.WebSocketResponse()
    await ws.prepare(request)
    _ws_clients.append(ws)
    logging.info(f"Frontend WS connected (total: {len(_ws_clients)})")
    try:
        async for msg in ws:
            if msg.type == web.WSMsgType.TEXT and msg.data == "ping":
                await ws.send_str("pong")
    finally:
        _ws_clients.remove(ws)
        logging.info(f"Frontend WS disconnected (total: {len(_ws_clients)})")
    return ws


async def handle_test_pipeline(request):
    """POST /test  →  text input, returns TTS audio bytes."""
    global _agent
    if not _agent:
        return web.json_response({"error": "Agent not initialised"}, status=500, headers=_cors())
    try:
        data = await request.json()
        text = data.get("text", "Hello, how are you?")
        logging.info(f"TEST /test: '{text}'")

        audio = await _agent._process_transcript(text)
        if not audio:
            return web.json_response({"error": "No audio produced"}, status=500, headers=_cors())

        return web.Response(
            body=audio,
            content_type=_tts_mime_type,
            headers=_cors({"Access-Control-Expose-Headers": "X-Input-Text"}),
        )
    except Exception as e:
        logging.error(f"/test error: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500, headers=_cors())


async def handle_process_audio(request):
    """POST /process-audio  →  audio upload, STT→LLM→TTS, returns TTS audio bytes."""
    global _agent
    if not _agent:
        return web.json_response({"error": "Agent not initialised"}, status=500, headers=_cors())
    try:
        reader = await request.multipart()
        field = await reader.next()
        if field is None or field.name != "audio":
            return web.json_response({"error": 'Expected "audio" field'}, status=400, headers=_cors())

        audio_bytes = await field.read()
        if not audio_bytes:
            return web.json_response({"error": "Empty audio"}, status=400, headers=_cors())

        logging.info(f"Received audio: {len(audio_bytes)} bytes — transcribing...")
        transcript = await _agent.stt.transcribe_file(audio_bytes)

        if not transcript or not transcript.strip():
            return web.json_response({"error": "Could not transcribe audio"}, status=422, headers=_cors())

        logging.info(f"Transcript: '{transcript}'")
        audio_out = await _agent._process_transcript(transcript)
        if not audio_out:
            return web.json_response({"error": "Pipeline produced no audio"}, status=500, headers=_cors())

        return web.Response(
            body=audio_out,
            content_type=_tts_mime_type,
            headers=_cors({
                "Access-Control-Expose-Headers": "X-Transcript",
                "X-Transcript": transcript[:500],
            }),
        )
    except Exception as e:
        logging.error(f"/process-audio error: {e}", exc_info=True)
        return web.json_response({"error": str(e)}, status=500, headers=_cors())


# ── main ──────────────────────────────────────────────────────────────────────
async def run():
    global _agent, _tts_mime_type
    load_dotenv()
    cfg = AgentConfig()

    # LLM — lazy import so unused providers don't trigger Pydantic-v1 warnings
    if cfg.LLM_PROVIDER.lower() == "claude":
        if not cfg.ANTHROPIC_API_KEY:
            raise KeyError("ANTHROPIC_API_KEY required for Claude")
        from agent.clients.claude_client import ClaudeClient
        llm = ClaudeClient(cfg.ANTHROPIC_API_KEY, model=cfg.CLAUDE_MODEL)
        llm_name = f"Claude ({cfg.CLAUDE_MODEL})"
    else:
        if not cfg.GEMINI_API_KEY:
            raise KeyError("GEMINI_API_KEY required for Gemini")
        from agent.clients.gemini_client import GeminiClient
        llm = GeminiClient(cfg.GEMINI_API_KEY, model=cfg.MODEL_GEMINI)
        llm_name = f"Gemini ({cfg.MODEL_GEMINI})"

    # TTS — lazy import
    tts_provider = cfg.TTS_PROVIDER.lower()
    if tts_provider == "pyttsx3":
        from agent.clients.pyttsx3_client import PyTTSX3Client
        tts = PyTTSX3Client()
        tts_name, _tts_mime_type = "PyTTSX3 (offline)", "audio/wav"
    elif tts_provider == "gtts":
        from agent.clients.gtts_client import GTTSClient
        tts = GTTSClient(language=cfg.TTS_LANGUAGE)
        tts_name, _tts_mime_type = "gTTS (free)", "audio/mpeg"
    elif tts_provider == "googlecloud":
        from agent.clients.google_tts_client import GoogleCloudTTS
        tts = GoogleCloudTTS(
            credentials_path=cfg.GOOGLE_CLOUD_TTS_CREDENTIALS_PATH,
            voice_name=cfg.GOOGLE_CLOUD_TTS_VOICE,
        )
        tts_name, _tts_mime_type = "Google Cloud TTS", "audio/mpeg"
    elif tts_provider == "elevenlabs":
        if not cfg.ELEVENLABS_API_KEY:
            raise KeyError("ELEVENLABS_API_KEY required for ElevenLabs")
        from agent.clients.elevenlabs_client import ElevenLabsTTS
        tts = ElevenLabsTTS(cfg.ELEVENLABS_API_KEY, voice_id=cfg.ELEVEN_VOICE_ID)
        tts_name, _tts_mime_type = "ElevenLabs", "audio/mpeg"
    else:
        raise ValueError(f"Unknown TTS_PROVIDER: {cfg.TTS_PROVIDER!r}")

    stt     = DeepgramClient(cfg.DEEPGRAM_API_KEY)
    stt_ws  = DeepgramWebsocketClient(cfg.DEEPGRAM_API_KEY)
    vad     = VAD()
    livekit = LiveKitClient(
        cfg.LIVEKIT_URL,
        api_key=cfg.LIVEKIT_API_KEY,
        api_secret=cfg.LIVEKIT_API_SECRET,
        room=cfg.LIVEKIT_ROOM,
    )
    agent   = VoiceAgent(stt=stt, llm=llm, tts=tts, vad=vad, livekit=livekit, stt_stream=stt_ws)
    _agent  = agent

    logging.info("=" * 60)
    logging.info("LiveKit Voice Agent started")
    logging.info(f"  LiveKit : {cfg.LIVEKIT_URL}")
    logging.info(f"  LLM     : {llm_name}")
    logging.info(f"  TTS     : {tts_name}  [{_tts_mime_type}]")
    logging.info("=" * 60)

    async def log_callback(event):
        await broadcast_log_event(event.to_dict())

    agent.ws_logger.subscribe(log_callback)

    app = web.Application()
    app.router.add_get("/health",         handle_health)
    app.router.add_get("/ws",             handle_ws_logs)
    app.router.add_post("/test",          handle_test_pipeline)
    app.router.add_options("/test",       handle_options)
    app.router.add_post("/process-audio", handle_process_audio)
    app.router.add_options("/process-audio", handle_options)

    runner = web.AppRunner(app)
    await runner.setup()
    await web.TCPSite(runner, "localhost", 8080).start()

    logging.info("HTTP API  http://localhost:8080")
    logging.info("  POST /test           text → LLM → TTS  (returns audio)")
    logging.info("  POST /process-audio  audio → STT → LLM → TTS  (returns audio)")
    logging.info("  GET  /health")
    logging.info("  WS   /ws             real-time pipeline events")
    logging.info("=" * 60)

    # ── Agent reconnection loop ────────────────────────────────────────────
    # HTTP server stays alive regardless of LiveKit connect/disconnect cycles.
    # When the remote participant disconnects, handle_call() returns and we
    # reconnect after a short pause.
    try:
        while True:
            try:
                logging.info("Agent starting call loop...")
                await agent.handle_call()
                logging.info("Call ended — reconnecting in 3 s...")
            except asyncio.CancelledError:
                break
            except Exception as e:
                logging.error(f"Agent error: {e}", exc_info=True)
                logging.info("Reconnecting in 5 s...")
                await asyncio.sleep(5)
                continue
            await asyncio.sleep(3)
    except asyncio.CancelledError:
        pass
    finally:
        await runner.cleanup()


if __name__ == "__main__":
    setup_logging()
    try:
        asyncio.run(run())
    except KeyError as e:
        logging.error(f"Missing env var: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"Fatal: {e}", exc_info=True)
        sys.exit(1)
