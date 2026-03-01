"""Speech-to-Text service using faster-whisper (local Whisper inference)."""

from __future__ import annotations

import asyncio
import io
import re
import tempfile
import wave
from functools import partial
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


def preload_model() -> None:
    """Eagerly load the Whisper model (call during app startup)."""
    if not settings.stt_enabled:
        return
    try:
        _get_model()
    except Exception as exc:
        log_event("stt.preload.failed", error=str(exc))


def _wav_to_float32(audio_bytes: bytes) -> np.ndarray:
    """Read WAV bytes into a float32 numpy array (no ffmpeg needed)."""
    with wave.open(io.BytesIO(audio_bytes)) as wf:
        frames = wf.readframes(wf.getnframes())
        samples = np.frombuffer(frames, dtype=np.int16).astype(np.float32) / 32768.0
    return samples


# ── Punctuation Restoration ──────────────────────────────────────────────
# Connective words that typically start a new clause in spoken Chinese.
# Sorted longest-first to avoid partial matches.
_CONNECTIVES = sorted([
    "但是", "不过", "然后", "所以", "因为", "因此", "如果", "那么",
    "比如", "比如说", "就是说", "或者", "而且", "另外", "同时",
    "接下来", "还有", "其实", "总的来说", "总之", "最后",
    "首先", "其次", "当然", "实际上", "一般来说", "关于",
    "对于", "至于", "除此之外", "与此同时", "换句话说",
    "具体来说", "简单来说", "也就是说", "换言之", "反过来",
    "还有就是", "再一个", "第一", "第二", "第三",
], key=len, reverse=True)

_CONNECTIVES_PATTERN = re.compile(
    r'(?<=[^\s，。？！、；：,.!?;:])((?:' +
    '|'.join(re.escape(c) for c in _CONNECTIVES) +
    r'))'
)

_PUNC_CHARS = set('，。？！、；：,.!?;:')


def _restore_punctuation(text: str) -> str:
    """Add basic Chinese punctuation to unpunctuated ASR output.

    Uses connective-word detection to insert commas at natural clause
    boundaries.  Designed for spoken Chinese with technical terms.
    """
    if not text or len(text) < 10:
        return text
    # Skip if already has adequate punctuation (>1.5 marks per 100 chars)
    punc_count = sum(1 for c in text if c in _PUNC_CHARS)
    if punc_count >= max(1, len(text) * 0.015):
        return text

    result = _CONNECTIVES_PATTERN.sub(r'，\1', text)
    # Clean leading comma, double commas
    if result.startswith('，'):
        result = result[1:]
    result = re.sub(r'[，,]{2,}', '，', result)
    # Ensure period at end
    if result and result[-1] not in '。？！…':
        if result[-1] == '，':
            result = result[:-1] + '。'
        else:
            result += '。'
    return result


def _build_initial_prompt(context: str | None) -> str:
    """Build a Whisper initial_prompt that primes the decoder for
    Chinese-English code-switching with technical terminology.

    The prompt is written as a properly punctuated Chinese paragraph so
    that Whisper's decoder is conditioned to output punctuation in the
    same style.
    """
    # A punctuated Chinese paragraph that primes the decoder to produce
    # proper punctuation and recognise common CS terms correctly.
    primer = (
        "嗯，我来说一下我的理解。首先，Transformer 的核心是 Self-Attention 机制，"
        "它通过 Query、Key、Value 三个矩阵来计算注意力权重。"
        "在实际项目中，我用过 LangChain 来搭建 RAG 系统，包括 Embedding 检索和 Prompt 工程。"
        "Agent 编排方面，我主要用 LangGraph 实现了多步骤的 Planner-Executor 架构。"
        "另外，在工程实践上，我部署过 Docker 和 Kubernetes 集群，"
        "数据库用的是 PostgreSQL 和 Redis，API 层用 gRPC 和 WebSocket。"
        "关于 Go 语言，我了解 Goroutine、Channel、Mutex 这些并发原语，"
        "以及 GMP 调度模型中 G、M、P 的职责和协作方式。"
    )
    if context:
        return f"{context}\n{primer}"
    return primer


def _llm_cleanup(raw_text: str, context: str) -> str:
    """Use LLM to fix obvious STT errors given the interview context."""
    from app.services.llm_client import RelayLLMClient

    client = RelayLLMClient()
    if not client.is_enabled():
        return raw_text

    system_prompt = (
        "你是语音转写纠错器。用户正在进行技术面试，语音识别把部分内容转错了。"
        "请根据面试上下文修正明显的错误，并补齐标点符号，保留原意，不要添加内容。"
        "规则：\n"
        "1. 修正英文技术术语（如「机」在讨论 GMP 时应为「G」，「Simon协成」应为「syscall」）\n"
        "2. 修正中文同音字（如「协成」→「协程」，「对列」→「队列」，「组设」→「阻塞」）\n"
        "3. 在自然断句处添加逗号（，），在语句结束处添加句号（。），疑问句用问号（？）\n"
        "4. 保持原文语序和口语风格，不要重写整段\n"
        "5. 严格输出 JSON: {\"text\": \"修正后的文本\"}\n"
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

    # Step 1: Rule-based punctuation restoration (fast, no network)
    full_text = _restore_punctuation(full_text)

    # Step 2: LLM-based post-processing to fix errors + refine punctuation
    if settings.stt_llm_cleanup and context and full_text:
        full_text = _llm_cleanup(full_text, context)

    return full_text


async def transcribe_audio_async(
    audio_bytes: bytes,
    filename: str = "audio.wav",
    context: str | None = None,
) -> str:
    """Async wrapper — runs transcribe_audio in a thread pool executor."""
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(
        None,
        partial(transcribe_audio, audio_bytes, filename=filename, context=context),
    )
