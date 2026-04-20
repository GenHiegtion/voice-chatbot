"""Vietnamese ASR pipeline using ChunkFormer model."""

import asyncio
from contextlib import redirect_stderr, redirect_stdout
from concurrent.futures import ThreadPoolExecutor
import io
import logging
import os
import tempfile
from functools import lru_cache

import soundfile as sf
import torch

from src.config import configure_model_cache_environment, get_settings
from src.speech.vad import extract_speech

logger = logging.getLogger(__name__)

# Singleton model instance
_model = None
_device = None
_executor = None
_MIN_ASR_SAMPLES = 400


def is_asr_model_loaded() -> bool:
    """Return whether the ASR model is already loaded in memory."""
    return _model is not None


def _get_device() -> str:
    """Get the best available device (CUDA > MPS > CPU)."""
    if torch.cuda.is_available():
        return "cuda"
    if torch.backends.mps.is_available():
        return "mps"
    return "cpu"


def get_asr_model():
    """Load or get the ChunkFormer ASR model (singleton).

    Uses khanhld/chunkformer-ctc-large-vie for Vietnamese ASR.
    The model will be downloaded automatically on first use.
    """
    global _model, _device

    if _model is not None:
        return _model

    try:
        # chunkformer may print optional dependency notices to stdout/stderr.
        # Silence those to keep API logs focused.
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            from chunkformer import ChunkFormerModel

        configure_model_cache_environment()

        _device = _get_device()
        logger.info("Loading ChunkFormer model", extra={"device": _device})

        # Try loading from local cache first (skip HuggingFace HTTP checks).
        # Only download if model is not cached yet.
        try:
            _model = ChunkFormerModel.from_pretrained(
                "khanhld/chunkformer-ctc-large-vie",
                local_files_only=True,
            )
        except Exception:
            logger.info("ChunkFormer model not found in local cache, downloading")
            _model = ChunkFormerModel.from_pretrained(
                "khanhld/chunkformer-ctc-large-vie",
            )
        _model = _model.to(_device)

        logger.info("ChunkFormer model loaded")
        return _model

    except Exception as e:
        logger.error("Failed to load ChunkFormer model", exc_info=True)
        raise RuntimeError(
            f"Could not load ChunkFormer ASR model. "
            f"Make sure 'chunkformer' is installed and the model can be downloaded. "
            f"Error: {e}"
        )


def _get_asr_executor() -> ThreadPoolExecutor:
    """Create or get the bounded executor used by ASR tasks."""
    global _executor
    if _executor is None:
        max_workers = max(1, get_settings().asr_max_workers)
        _executor = ThreadPoolExecutor(
            max_workers=max_workers,
            thread_name_prefix="asr-worker",
        )
    return _executor


@lru_cache(maxsize=16)
def _get_resampler(orig_freq: int, new_freq: int):
    """Get a cached torchaudio Resampler for the given frequency pair."""
    import torchaudio
    return torchaudio.transforms.Resample(orig_freq=orig_freq, new_freq=new_freq)


def _transcribe_sync(audio_bytes: bytes, sample_rate: int) -> str:
    """Synchronous transcription logic (runs in thread pool).

    All CPU-intensive work (audio decoding, resampling, VAD, model inference)
    is done here to avoid blocking the async event loop.
    """
    # Read audio from bytes
    audio_buffer = io.BytesIO(audio_bytes)
    audio_data, sr = sf.read(audio_buffer)

    # Convert to mono if stereo
    if len(audio_data.shape) > 1:
        audio_data = audio_data.mean(axis=1)

    # Resample if needed (using cached resampler)
    if sr != sample_rate:
        waveform = torch.tensor(
            audio_data, dtype=torch.float32).unsqueeze(0)
        resampler = _get_resampler(sr, sample_rate)
        waveform = resampler(waveform)
        audio_data = waveform.squeeze(0).numpy()

    # Apply VAD to filter speech segments (if enabled)
    settings = get_settings()

    if settings.vad_enabled:
        speech_audio = extract_speech(audio_data, sample_rate)

        if speech_audio is not None:
            audio_data = speech_audio
        else:
            logger.debug("VAD found no speech segments; using original audio")

    # Guard against ultra-short waveforms that can crash feature extraction.
    if len(audio_data) < _MIN_ASR_SAMPLES:
        logger.info(
            "Audio too short for ASR inference; returning empty transcription",
            extra={"samples": int(len(audio_data))},
        )
        return ""

    # Get model
    model = get_asr_model()

    # ChunkFormerModel.endless_decode requires a file path, not a numpy array.
    # Write audio data to a temporary WAV file for decoding.
    tmp_file = None
    try:
        tmp_file = tempfile.NamedTemporaryFile(
            suffix=".wav", delete=False
        )
        sf.write(tmp_file.name, audio_data, sample_rate)
        tmp_file.close()

        # Use endless_decode for long-form transcription
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            result = model.endless_decode(
                tmp_file.name,
                return_timestamps=False,
            )
    finally:
        if tmp_file and os.path.exists(tmp_file.name):
            os.unlink(tmp_file.name)

    # Handle result format
    # When return_timestamps=False, result is a joined string.
    # When return_timestamps=True, result is a list of dicts with 'decode' key.
    if isinstance(result, list):
        text = " ".join(
            item["decode"] if isinstance(item, dict) else str(item)
            for item in result
        )
    elif isinstance(result, dict):
        text = result.get("decode", result.get("text", str(result)))
    else:
        text = str(result)

    return text.strip()


async def transcribe_audio(audio_bytes: bytes, sample_rate: int = 16000) -> str:
    """Transcribe audio bytes to Vietnamese text using ChunkFormer.

    Pipeline: Audio → VAD (filter speech) → ASR (transcribe)

    Runs CPU-intensive work in a thread pool to avoid blocking the event loop.

    Args:
        audio_bytes: Raw audio data (WAV format expected)
        sample_rate: Audio sample rate (default 16000 Hz)

    Returns:
        Transcribed text string
    """
    try:
        loop = asyncio.get_running_loop()
        executor = _get_asr_executor()
        text = await loop.run_in_executor(
            executor,
            _transcribe_sync,
            audio_bytes,
            sample_rate,
        )
        return text

    except Exception as e:
        logger.error("Transcription failed", exc_info=True)
        raise RuntimeError(f"Failed to transcribe audio: {e}")
