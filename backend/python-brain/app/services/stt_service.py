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


def _build_initial_prompt(context: str | None) -> str:
    """Build a Whisper initial_prompt that primes the decoder for
    Chinese-English code-switching with technical terminology.

    The initial_prompt conditions Whisper's decoder to output these exact
    tokens when it encounters similar sounds, dramatically improving
    recognition of English terms embedded in Chinese speech.
    """
    # Base vocabulary: common CS terms that Whisper often misrecognizes
    base_terms = (
        "Goroutine, Channel, Mutex, WaitGroup, Context, Defer, Panic, Recover, "
        "GMP, G, M, P, GOMAXPROCS, Netpoller, Syscall, Runtime, Scheduler, "
        "Transformer, Attention, Embedding, Token, Prompt, RAG, Agent, LangChain, "
        "API, HTTP, gRPC, WebSocket, Docker, Kubernetes, Redis, PostgreSQL, MySQL, "
        "CPU, GPU, IO, "
        "协程, 调度器, 队列, 线程, 进程, 堆栈, 垃圾回收, 内存分配"
    )
    if context:
        return f"{context}\n{base_terms}"
    return base_terms


def _llm_cleanup(raw_text: str, context: str) -> str:
    """Use LLM to fix obvious STT errors given the interview context."""
    from app.services.llm_client import RelayLLMClient

    client = RelayLLMClient()
    if not client.is_enabled():
        return raw_text

    system_prompt = (
        "你是语音转写纠错器。用户正在进行技术面试，语音识别把部分内容转错了。"
        "请根据面试上下文修正明显的错误，保留原意，不要添加内容。"
        "规则：\n"
        "1. 修正英文技术术语（如「机」在讨论 GMP 时应为「G」，「Simon协成」应为「syscall」）\n"
        "2. 修正中文同音字（如「协成」→「协程」，「对列」→「队列」，「组设」→「阻塞」）\n"
        "3. 保持原文语序和口语风格，不要重写整段\n"
        "4. 严格输出 JSON: {\"text\": \"修正后的文本\"}\n"
    )
    user_prompt = (
        f"面试问题: {context}\n\n"
        f"语音识别原文:\n{raw_text}"
    )
    try:
        data, _reasoning = client.chat_json_sync(
            model=settings.llm_model_default,
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            force_json_object=True,
            timeout_s=10.0,
        )
        cleaned = str(data.get("text", "")).strip()
        if not cleaned:
            return raw_text
        log_event("stt.llm_cleanup.done", original_len=len(raw_text), cleaned_len=len(cleaned))
        return cleaned
    except Exception as exc:
        log_event("stt.llm_cleanup.failed", error=str(exc))
        return raw_text


def transcribe_audio(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    context: str | None = None,
) -> str:
    """Transcribe audio bytes to text using Whisper.

    Args:
        audio_bytes: Raw audio data.
        filename: Original filename (for format detection).
        context: Interview context (e.g. current question) used to build
                 initial_prompt for better Chinese-English recognition.

    WAV files are decoded in pure Python (no ffmpeg).
    Other formats require ffmpeg on PATH.
    """
    model = _get_model()
    suffix = Path(filename).suffix.lower()

    vad_params = dict(min_silence_duration_ms=500)
    initial_prompt = _build_initial_prompt(context)

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
            initial_prompt=initial_prompt,
            beam_size=5,
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
        has_context=bool(context),
    )

    # Optional: LLM-based post-processing to fix domain-specific errors
    if settings.stt_llm_cleanup and context and full_text:
        full_text = _llm_cleanup(full_text, context)

    return full_text
