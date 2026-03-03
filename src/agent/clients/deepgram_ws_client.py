"""
Deepgram realtime WebSocket streaming client (prototype).

This client opens a WebSocket to Deepgram's /listen realtime endpoint and
allows sending audio frames via `send_audio`. Incoming transcript messages are
passed to a user-provided callback.

Note: adjust URL params (encoding, sample_rate, channels) to match your audio.
"""
import aiohttp
import asyncio
from typing import Callable, Optional


class DeepgramWebsocketClient:
    def __init__(self, api_key: str, encoding: str = "linear16", sample_rate: int = 16000, channels: int = 1):
        self.api_key = api_key
        self.encoding = encoding
        self.sample_rate = sample_rate
        self.channels = channels
        self._ws = None
        self._session = None
        self._listener_task: Optional[asyncio.Task] = None

    def _url(self) -> str:
        return (
            f"wss://api.deepgram.com/v1/listen"
            f"?encoding={self.encoding}"
            f"&sample_rate={self.sample_rate}"
            f"&channels={self.channels}"
            f"&interim_results=true"    # required for utterance_end_ms to work
            f"&utterance_end_ms=1000"   # end-of-utterance after 1 s of silence
            f"&punctuate=true"          # cleaner text input for LLM
        )

    async def connect(self, on_transcript: Callable[[dict], None]):
        headers = {"Authorization": f"Token {self.api_key}"}
        # Close any leftover session from a previous failed connect
        if self._session is not None:
            await self._session.close()
            self._session = None
        self._session = aiohttp.ClientSession()
        try:
            self._ws = await self._session.ws_connect(self._url(), headers=headers)
        except Exception:
            await self._session.close()
            self._session = None
            raise

        async def _reader():
            async for msg in self._ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = msg.json()
                    except Exception:
                        data = {"raw": msg.data}
                    # callback with raw dict
                    await on_transcript(data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    break

        self._listener_task = asyncio.create_task(_reader())

    async def send_audio(self, frame: bytes):
        """Send binary audio frame to Deepgram WS.

        Deepgram expects raw PCM frames; ensure frames match the `encoding` and
        `sample_rate` parameters.
        """
        if self._ws is None:
            raise RuntimeError("WebSocket not connected")
        await self._ws.send_bytes(frame)

    async def close(self):
        if self._ws is not None:
            await self._ws.close()
            self._ws = None
        if self._listener_task is not None:
            self._listener_task.cancel()
            self._listener_task = None
        if self._session is not None:
            await self._session.close()
            self._session = None

    async def __aenter__(self):
        # no-op; user should call connect(on_transcript)
        return self

    async def __aexit__(self, exc_type, exc, tb):
        await self.close()


__all__ = ["DeepgramWebsocketClient"]
