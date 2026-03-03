"""
LiveKit client — real-time audio using the livekit.rtc Python SDK.

The agent joins the configured room as "voice-agent", subscribes to every
other participant's audio (the user's mic), and publishes TTS audio back
so the browser hears the response.
"""
import asyncio
import io
import logging
import wave
from typing import Callable, Optional

logger = logging.getLogger(__name__)

_AGENT_IDENTITY = "voice-agent"
_FRAME_SAMPLES  = 480   # 20 ms @ 24 kHz


class LiveKitClient:
    def __init__(
        self,
        url: str,
        api_key: Optional[str] = None,
        api_secret: Optional[str] = None,
        room: str = "test-room",
    ):
        self.url        = url
        self.api_key    = api_key
        self.api_secret = api_secret
        self.room       = room

        self._room        = None
        self._src         = None   # rtc.AudioSource — outbound TTS audio
        self._local_track = None
        self._connected   = False

    # ── token ──────────────────────────────────────────────────────────────────
    def _make_token(self) -> str:
        from livekit.api import AccessToken, VideoGrants
        return (
            AccessToken(api_key=self.api_key, api_secret=self.api_secret)
            .with_identity(_AGENT_IDENTITY)
            .with_name("Voice Agent")
            .with_grants(VideoGrants(
                room_join=True,
                room=self.room,
                can_publish=True,
                can_subscribe=True,
            ))
            .to_jwt()
        )

    # ── connect ────────────────────────────────────────────────────────────────
    async def connect(self):
        from livekit import rtc
        self._room = rtc.Room()
        token = self._make_token()
        logger.info(f"Connecting agent to LiveKit room '{self.room}'...")
        await self._room.connect(self.url, token)
        self._connected = True
        logger.info(f"Agent connected: {self._room.name}")

        # Publish a mono audio source so the browser hears TTS replies
        self._src = rtc.AudioSource(sample_rate=22050, num_channels=1)
        self._local_track = rtc.LocalAudioTrack.create_audio_track(
            "agent-voice", self._src
        )
        await self._room.local_participant.publish_track(self._local_track)
        logger.info("Agent audio track published — browser can now subscribe to it")

    # ── send TTS audio to browser ──────────────────────────────────────────────
    async def send_audio(self, audio_bytes: bytes):
        """Stream WAV bytes as LiveKit audio frames so the user hears the response."""
        if not self._src or not audio_bytes:
            return
        try:
            from livekit import rtc
            pcm, rate, ch = self._wav_to_pcm(audio_bytes)
            bytes_per_frame = _FRAME_SAMPLES * 2 * ch   # int16 LE

            for off in range(0, len(pcm), bytes_per_frame):
                chunk = pcm[off: off + bytes_per_frame]
                if not chunk:
                    break
                frame = rtc.AudioFrame(
                    data=chunk,
                    sample_rate=rate,
                    num_channels=ch,
                    samples_per_channel=len(chunk) // (2 * ch),
                )
                await self._src.capture_frame(frame)
                await asyncio.sleep(0)   # yield — keeps event loop responsive
        except Exception as e:
            logger.error(f"send_audio error: {e}")

    @staticmethod
    def _wav_to_pcm(data: bytes):
        """Return (pcm_bytes, sample_rate, channels) from a WAV blob."""
        try:
            with wave.open(io.BytesIO(data), "rb") as wf:
                return wf.readframes(wf.getnframes()), wf.getframerate(), wf.getnchannels()
        except Exception:
            return data, 22050, 1   # fallback: treat as raw PCM mono 22050

    # ── receive participant audio ──────────────────────────────────────────────
    async def receive_audio_frames(self, on_frame: Callable[[bytes], None]):
        """
        Subscribe to every non-agent participant's audio track.
        Calls on_frame(pcm_bytes) for each 20 ms frame resampled to 16 kHz mono
        (matching the Deepgram WebSocket encoding).
        """
        from livekit import rtc

        async def _drain(stream: rtc.AudioStream, identity: str):
            logger.info(f"Streaming audio from: {identity}")
            try:
                async for event in stream:
                    if isinstance(event, rtc.AudioFrameEvent):
                        await on_frame(bytes(event.frame.data))
            except Exception as e:
                logger.debug(f"Audio stream ended ({identity}): {e}")

        @self._room.on("track_subscribed")
        def _on_track(track, pub, participant):
            if (
                track.kind == rtc.TrackKind.KIND_AUDIO
                and participant.identity != _AGENT_IDENTITY
            ):
                # Resample to 16 kHz mono so Deepgram WS gets the right format
                stream = rtc.AudioStream(track, sample_rate=16000, num_channels=1)
                asyncio.create_task(_drain(stream, participant.identity))
                logger.info(f"Subscribed to audio from: {participant.identity}")

        @self._room.on("disconnected")
        def _on_disc(reason=None):
            self._connected = False
            logger.info(f"LiveKit disconnected: {reason}")

        # ── Handle participants who were already in the room before this call ──
        # If the browser user joined before receive_audio_frames() was called,
        # the track_subscribed event already fired and was missed.  Catch up now.
        for participant in self._room.remote_participants.values():
            if participant.identity == _AGENT_IDENTITY:
                continue
            for pub in participant.track_publications.values():
                if pub.subscribed and pub.track and pub.track.kind == rtc.TrackKind.KIND_AUDIO:
                    stream = rtc.AudioStream(pub.track, sample_rate=16000, num_channels=1)
                    asyncio.create_task(_drain(stream, participant.identity))
                    logger.info(f"Subscribed to existing audio from: {participant.identity}")

        logger.info(f"Listening for participants in room '{self.room}'...")
        while self._connected:
            await asyncio.sleep(0.5)

    # ── disconnect ────────────────────────────────────────────────────────────
    async def disconnect(self):
        self._connected = False
        if self._room:
            await self._room.disconnect()
        logger.info("LiveKit disconnected")


__all__ = ["LiveKitClient"]
