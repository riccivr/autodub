"""
Speech-to-text transcription module using faster-whisper.
Runs on CPU with int8 quantization and configurable thread count.
"""

import os
from typing import List, Dict, Any


def transcribe_audio(
    audio_path: str,
    model_size: str = "base",
    language: str = "en",
    threads: int = 1,
    beam_size: int = 1,
) -> List[Dict[str, Any]]:
    """
    Transcribe audio file into timecoded speech segments.
    
    Args:
        audio_path: Path to 16kHz mono WAV file.
        model_size: Whisper model size ('tiny', 'base', 'small', 'medium').
        language: Source audio language code ('en').
        threads: Number of CPU threads for CTranslate2 (default: 1).
        beam_size: Beam search width (default: 1 for fast greedy search).
    
    Returns:
        List of segment dictionaries with timestamps.
    """
    from faster_whisper import WhisperModel

    # Determine thread allocation
    cpu_threads = threads if threads > 0 else (os.cpu_count() or 1)
    num_workers = min(2, cpu_threads) if cpu_threads > 1 else 1

    model = WhisperModel(
        model_size,
        device="cpu",
        compute_type="int8",
        cpu_threads=cpu_threads,
        num_workers=num_workers,
    )

    segments, info = model.transcribe(
        audio_path,
        language=language,
        beam_size=beam_size,
        word_timestamps=False,  # segment-level timestamps are sufficient and faster
        condition_on_previous_text=False,  # avoids hallucination loops and speeds up CPU inference
        vad_filter=True,  # filters out long silences and background noise
        vad_parameters=dict(min_silence_duration_ms=500),
    )

    parsed_segments = []
    for i, segment in enumerate(segments):
        clean_text = segment.text.strip()
        if not clean_text:
            continue
        parsed_segments.append({
            "id": i,
            "start": round(segment.start, 3),
            "end": round(segment.end, 3),
            "duration": round(segment.end - segment.start, 3),
            "text": clean_text,
        })

    return parsed_segments
