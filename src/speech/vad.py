"""Silero VAD (Voice Activity Detection) for filtering speech segments.

Detects speech regions in audio before sending to ASR,
improving transcription quality by removing silence/noise.
"""

import logging
from contextlib import redirect_stderr, redirect_stdout
import io
from typing import Optional

import torch
import numpy as np

from src.config import configure_model_cache_environment

logger = logging.getLogger(__name__)

# Singleton VAD model
_vad_model = None
_vad_utils = None


def is_vad_model_loaded() -> bool:
    """Return whether the VAD model is already loaded in memory."""
    return _vad_model is not None


def get_vad_model():
    """Load or get the Silero VAD model (singleton).

    Model is loaded from torch.hub (snakers4/silero-vad).
    Downloaded automatically on first use (~2MB).
    """
    global _vad_model, _vad_utils

    if _vad_model is not None:
        return _vad_model, _vad_utils

    try:
        configure_model_cache_environment()
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            model, utils = torch.hub.load(
                repo_or_dir="snakers4/silero-vad",
                model="silero_vad",
                trust_repo=True,
                force_reload=False,
                skip_validation=True,
            )
        _vad_model = model
        _vad_utils = utils
        logger.info("Silero VAD model loaded")
        return _vad_model, _vad_utils

    except Exception as e:
        logger.error("Failed to load Silero VAD model", exc_info=True)
        raise RuntimeError(f"Could not load Silero VAD model: {e}")


def detect_speech_segments(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    threshold: float = 0.5,
    min_speech_duration_ms: int = 250,
    min_silence_duration_ms: int = 100,
) -> list[dict]:
    """Detect speech segments in audio using Silero VAD.

    Args:
        audio_data: Audio waveform as numpy array (mono, float32)
        sample_rate: Audio sample rate (must be 8000 or 16000)
        threshold: Speech probability threshold (0.0-1.0)
        min_speech_duration_ms: Minimum speech segment duration in ms
        min_silence_duration_ms: Minimum silence between segments in ms

    Returns:
        List of dicts with 'start' and 'end' sample indices
    """
    model, utils = get_vad_model()
    get_speech_timestamps = utils[0]

    # Convert to torch tensor
    wav_tensor = torch.tensor(audio_data, dtype=torch.float32)

    # Get speech timestamps
    speech_timestamps = get_speech_timestamps(
        wav_tensor,
        model,
        sampling_rate=sample_rate,
        threshold=threshold,
        min_speech_duration_ms=min_speech_duration_ms,
        min_silence_duration_ms=min_silence_duration_ms,
    )

    return speech_timestamps


def extract_speech(
    audio_data: np.ndarray,
    sample_rate: int = 16000,
    padding_ms: int = 30,
) -> Optional[np.ndarray]:
    """Extract only speech portions from audio, removing silence/noise.

    Args:
        audio_data: Audio waveform as numpy array (mono, float32)
        sample_rate: Audio sample rate
        padding_ms: Padding around speech segments in ms

    Returns:
        Audio array containing only speech, or None if no speech detected
    """
    try:
        segments = detect_speech_segments(audio_data, sample_rate)

        if not segments:
            logger.debug("No speech segments detected in audio")
            return None

        padding_samples = int(sample_rate * padding_ms / 1000)
        speech_chunks = []

        for seg in segments:
            start = max(0, seg["start"] - padding_samples)
            end = min(len(audio_data), seg["end"] + padding_samples)
            speech_chunks.append(audio_data[start:end])

        # Concatenate all speech segments
        if speech_chunks:
            return np.concatenate(speech_chunks)

        return None

    except Exception:
        logger.warning("VAD processing failed, using original audio", exc_info=True)
        return audio_data
