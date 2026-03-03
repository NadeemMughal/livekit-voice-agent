"""
VoiceAgent: orchestrates VAD, STT, LLM, and TTS to handle a single call.

This is a high-level orchestrator demonstrating dependency injection and OOP
so you can replace individual client implementations for production usage.
"""
import asyncio
import time
import logging
from typing import Optional

from typing import Any

from .clients.deepgram_client import DeepgramClient
from .clients.deepgram_ws_client import DeepgramWebsocketClient
from .livekit_client import LiveKitClient
from .vad import VAD
from .ws_logger import get_ws_logger

logger = logging.getLogger(__name__)


class VoiceAgent:
    def __init__(
        self,
        stt: DeepgramClient,
        llm: Any,
        tts: Any,
        vad: VAD,
        livekit: LiveKitClient,
        stt_stream: DeepgramWebsocketClient | None = None,
    ):
        self.stt = stt
        self.llm = llm
        self.tts = tts
        self.vad = vad
        self.livekit = livekit
        self.stt_stream = stt_stream
        self.ws_logger = get_ws_logger()
        self._interrupt_flag = False
        self._processing_task: Optional[asyncio.Task] = None

    def request_interrupt(self):
        """Request interrupt of current processing."""
        self._interrupt_flag = True
        self.ws_logger.log_interrupt("Interrupt requested")

    async def handle_call(self):
        """High-level call loop with streaming and interrupt support."""
        await self.livekit.connect()
        try:
            if self.stt_stream is not None:
                async def on_transcript(msg: dict):
                    if self._interrupt_flag:
                        return

                    # Skip interim/partial results — only act on final transcripts
                    if not msg.get("is_final", True):
                        return

                    text = ""
                    try:
                        text = (
                            msg.get("channel", {})
                            .get("alternatives", [{}])[0]
                            .get("transcript", "")
                            .strip()
                        )
                    except Exception:
                        pass

                    if text:
                        await self._process_transcript(text)

                await self.stt_stream.connect(on_transcript)

                async def on_frame(frame: bytes):
                    if self.vad.is_speech(frame):
                        self.ws_logger.log_vad(True)
                        await self.stt_stream.send_audio(frame)
                    else:
                        self.ws_logger.log_vad(False)

                await self.livekit.receive_audio_frames(on_frame)
                await self.stt_stream.close()
                return

            # Non-streaming fallback: receive audio frames and buffer/handle elsewhere
            async def on_frame(frame: bytes):
                if self.vad.is_speech(frame):
                    self.ws_logger.log_vad(True)

            await self.livekit.receive_audio_frames(on_frame)
        finally:
            # Always disconnect LiveKit so the identity is freed before any reconnect.
            # Without this, the reconnection loop gets DuplicateIdentity errors.
            await self.livekit.disconnect()

    async def _process_transcript(self, text: str) -> bytes:
        """Process a transcript: LLM -> TTS. Returns TTS audio bytes (or b'' on error/interrupt)."""
        if self._interrupt_flag:
            return b""

        audio_out = b""
        try:
            # LLM
            self.ws_logger.log_llm_start(text)
            llm_start = time.time()
            response_text = await self.llm.generate(prompt=text)
            self.ws_logger.log_llm_end(response_text, (time.time() - llm_start) * 1000)

            if self._interrupt_flag:
                return b""

            # TTS
            self.ws_logger.log_tts_start(response_text)
            tts_start = time.time()
            audio_out = await self.tts.synthesize(response_text)
            self.ws_logger.log_tts_end((time.time() - tts_start) * 1000, len(audio_out))

            if self._interrupt_flag:
                return b""

            await self.livekit.send_audio(audio_out)
        except Exception as e:
            self.ws_logger.log_error(f"Error processing transcript: {e}", e)
            logger.error(f"Error in _process_transcript: {e}", exc_info=True)

        return audio_out

    async def process_utterance(self, audio_bytes: bytes) -> bytes:
        """Process a finished utterance: STT -> LLM -> TTS. Returns audio bytes."""
        self.ws_logger.log_stt_start()
        stt_start = time.time()
        transcript = await self.stt.transcribe_file(audio_bytes)
        stt_duration = (time.time() - stt_start) * 1000
        self.ws_logger.log_stt_end(transcript, stt_duration)

        await self._process_transcript(transcript)
        return audio_bytes


__all__ = ["VoiceAgent"]
