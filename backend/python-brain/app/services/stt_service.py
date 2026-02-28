"""Speech-to-Text service using faster-whisper (local Whisper inference)."""

from __future__ import annotations

import io
import tempfile
import wave
from pathlib import Path

import numpy as np

from app.core.config import settings
from app.core.logging import log_event

_model = None


def _get_model():
    global _model
    if _model is not None:
        return _model
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError(
            "faster-whisper 未安装。请运行: uv sync --extra stt"
        )
    log_event("stt.model.loading", model=settings.stt_model, device=settings.stt_device)
    _model = WhisperModel(
        settings.stt_model,
        device=settings.stt_device,
        compute_type=settings.stt_compute_type,
    )
    log_event("stt.model.loaded", model=settings.stt_model)
    return _model


def _wav_to_float32(audio_bytes: bytes) -> np.ndarray:
    """Read WAV bytes into a float32 numpy array (no ffmpeg needed)."""
    with wave.open(io.BytesIO(audio_bytes)) as wf:
        frames = wf.readframes(wf.getnframes())
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


def transcribe_audio(audio_bytes: bytes, filename: str = "audio.wav") -> str:
    """Transcribe audio bytes to text using Whisper.

    WAV files are decoded in pure Python (no ffmpeg).
    Other formats require ffmpeg on PATH.
    """
    model = _get_model()
    suffix = Path(filename).suffix.lower()

    vad_params = dict(min_silence_duration_ms=500)

    if suffix == ".wav":
        audio_input = _wav_to_float32(audio_bytes)
    else:
        # Non-WAV: write to temp file, faster-whisper will use ffmpeg
        tmp = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            tmp.write(audio_bytes)
            tmp.flush()
            tmp.close()
            audio_input = tmp.name
        except Exception:
            Path(tmp.name).unlink(missing_ok=True)
            raise

    try:
        segments, info = model.transcribe(
            audio_input,
            language="zh",
            vad_filter=True,
            vad_parameters=vad_params,
        )
        text_parts = [seg.text for seg in segments]
    finally:
        # Clean up temp file for non-WAV
        if isinstance(audio_input, str):
            Path(audio_input).unlink(missing_ok=True)

    full_text = "".join(text_parts).strip()
    log_event(
        "stt.transcribed",
        language=info.language,
        duration=round(info.duration, 1),
        text_length=len(full_text),
    )
    return full_text
