"""
Simple VAD wrapper using webrtcvad to detect speech frames.

This example assumes 16kHz mono 16-bit PCM frames. Adapt framing logic to match
your audio input pipeline (e.g., the RTP audio you receive from LiveKit).
"""
import logging

try:
    import webrtcvad

    class VAD:
        def __init__(self, aggressiveness: int = 2):
            self._vad = webrtcvad.Vad(aggressiveness)

        def is_speech(self, frame_bytes: bytes, sample_rate: int = 16000) -> bool:
            # frame_bytes must be 10/20/30ms of 16-bit mono PCM at sample_rate
            return self._vad.is_speech(frame_bytes, sample_rate)

except Exception:
    logging.getLogger(__name__).warning(
        "webrtcvad not available; using fallback VAD stub (always detects non-empty frames)"
    )

    class VAD:
        def __init__(self, aggressiveness: int = 2):
            pass

        def is_speech(self, frame_bytes: bytes, sample_rate: int = 16000) -> bool:
            return bool(frame_bytes)


__all__ = ["VAD"]
