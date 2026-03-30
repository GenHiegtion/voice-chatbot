"""Vietnamese ASR pipeline using ChunkFormer model."""

import asyncio
import io
import logging
import os
import tempfile
from functools import lru_cache

import torch

logger = logging.getLogger(__name__)

# Singleton model instance
_model = None
_device = None


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
        from chunkformer import ChunkFormerModel

        # Set HuggingFace cache dir if configured
        from src.config import get_settings
        settings = get_settings()
        if settings.hf_home:
            os.environ["HF_HOME"] = settings.hf_home

        _device = _get_device()
        logger.info(f"Loading ChunkFormer model on device: {_device}")

        # Try loading from local cache first (skip HuggingFace HTTP checks).
        # Only download if model is not cached yet.
        try:
            _model = ChunkFormerModel.from_pretrained(
                "khanhld/chunkformer-ctc-large-vie",
                local_files_only=True,
            )
        except Exception:
            logger.info(
                "Model not found in cache, downloading from HuggingFace...")
            _model = ChunkFormerModel.from_pretrained(
                "khanhld/chunkformer-ctc-large-vie",
            )
        _model = _model.to(_device)

        logger.info("ChunkFormer model loaded successfully.")
        return _model

    except Exception as e:
        logger.error(f"Failed to load ChunkFormer model: {e}")
        raise RuntimeError(
            f"Could not load ChunkFormer ASR model. "
            f"Make sure 'chunkformer' is installed and the model can be downloaded. "
            f"Error: {e}"
        )


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
    import soundfile as sf
    import numpy as np

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
    from src.config import get_settings
    settings = get_settings()

    if settings.vad_enabled:
        from src.speech.vad import extract_speech

        logger.info("Applying VAD to filter speech segments...")
        speech_audio = extract_speech(audio_data, sample_rate)

        if speech_audio is not None:
            audio_data = speech_audio
            logger.info(f"VAD: extracted {len(audio_data)} speech samples")
        else:
            logger.warning("VAD: no speech detected, using original audio")

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
        text = await loop.run_in_executor(
            None, _transcribe_sync, audio_bytes, sample_rate
        )
        return text

    except Exception as e:
        logger.error(f"Transcription error: {e}")
        raise RuntimeError(f"Failed to transcribe audio: {e}")
