"""
WebSocket logging handler for streaming agent logs to frontend.

Allows the agent to emit structured log events (STT, LLM, TTS, latency, etc.)
that can be subscribed to by the frontend.
"""
import asyncio
import json
import time
import logging
from typing import Dict, Any, Optional, Callable, List
from dataclasses import dataclass, asdict
from datetime import datetime

@dataclass
class LogEvent:
    """Structured log event."""
    timestamp: float
    level: str
    event_type: str  # 'stt', 'llm', 'tts', 'vad', 'error', etc.
    message: str
    data: Optional[Dict[str, Any]] = None
    duration_ms: Optional[float] = None

    def to_dict(self):
        return asdict(self)

    def to_json(self):
        return json.dumps(self.to_dict())


class WebSocketLogger:
    """Manages WebSocket connections and broadcasts log events."""
    
    def __init__(self):
        self._subscribers: List[Callable[[LogEvent], None]] = []
        self._logger = logging.getLogger(__name__)

    def subscribe(self, callback: Callable[[LogEvent], None]):
        """Subscribe to log events."""
        self._subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[LogEvent], None]):
        """Unsubscribe from log events."""
        if callback in self._subscribers:
            self._subscribers.remove(callback)

    def emit(self, event: LogEvent):
        """Emit a log event to all subscribers."""
        for callback in self._subscribers:
            try:
                asyncio.create_task(self._async_callback(callback, event))
            except Exception as e:
                self._logger.error(f"Error emitting log: {e}")

    async def _async_callback(self, callback, event):
        """Handle async callback safely."""
        try:
            if asyncio.iscoroutinefunction(callback):
                await callback(event)
            else:
                callback(event)
        except Exception as e:
            self._logger.error(f"Error in log callback: {e}")

    def log_stt_start(self, message: str = "STT started"):
        """Log STT start event."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="stt_start",
            message=message,
        ))

    def log_stt_end(self, transcript: str, duration_ms: float):
        """Log STT completion with transcript and latency."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="stt_end",
            message=f"STT complete: '{transcript}'",
            data={"transcript": transcript},
            duration_ms=duration_ms,
        ))

    def log_llm_start(self, prompt: str):
        """Log LLM processing start."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="llm_start",
            message=f"LLM processing: {prompt[:100]}...",
            data={"prompt": prompt},
        ))

    def log_llm_end(self, response: str, duration_ms: float):
        """Log LLM completion with response and latency."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="llm_end",
            message=f"LLM response: '{response}'",
            data={"response": response},
            duration_ms=duration_ms,
        ))

    def log_tts_start(self, text: str):
        """Log TTS processing start."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="tts_start",
            message=f"TTS synthesis: {text[:100]}...",
            data={"text": text},
        ))

    def log_tts_end(self, duration_ms: float, audio_bytes: int = 0):
        """Log TTS completion with latency."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="tts_end",
            message=f"TTS complete ({audio_bytes} bytes)",
            data={"audio_bytes": audio_bytes},
            duration_ms=duration_ms,
        ))

    def log_vad(self, is_speech: bool):
        """Log VAD detection."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="DEBUG",
            event_type="vad",
            message=f"VAD: {'speech' if is_speech else 'silence'}",
            data={"is_speech": is_speech},
        ))

    def log_error(self, message: str, exception: Optional[Exception] = None):
        """Log error."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="ERROR",
            event_type="error",
            message=message,
            data={"exception": str(exception)} if exception else None,
        ))

    def log_interrupt(self, message: str = "User interrupted"):
        """Log interrupt event."""
        self.emit(LogEvent(
            timestamp=time.time(),
            level="INFO",
            event_type="interrupt",
            message=message,
        ))


# Global logger instance
_ws_logger: Optional[WebSocketLogger] = None


def get_ws_logger() -> WebSocketLogger:
    """Get or create the global WebSocket logger."""
    global _ws_logger
    if _ws_logger is None:
        _ws_logger = WebSocketLogger()
    return _ws_logger


__all__ = ["WebSocketLogger", "LogEvent", "get_ws_logger"]
