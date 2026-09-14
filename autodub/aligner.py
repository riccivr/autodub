"""
Audio alignment and time-stretching module.
Aligns translated TTS audio segments to their original video timestamps without drifting.
Uses direct in-memory PCM timeline assembly to eliminate hundreds of slow FFmpeg subprocesses.
"""

import os
import wave
import subprocess
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Tuple


def get_wav_info(wav_path: str) -> Tuple[int, int, int, bytes]:
    """
    Read WAV file properties and PCM frames.
    Returns: (sample_rate, sample_width, channels, raw_frames)
    """
    with wave.open(wav_path, "rb") as wf:
        rate = wf.getframerate()
        width = wf.getsampwidth()
        channels = wf.getnchannels()
        frames = wf.readframes(wf.getnframes())
        return rate, width, channels, frames


def stretch_or_resample_audio(
    input_wav: str,
    output_wav: str,
    speed_ratio: float = 1.0,
    target_sample_rate: int = 24000,
) -> str:
    """
    Adjust playback speed using ffmpeg atempo and normalize to mono 16-bit PCM target_sample_rate.
    """
    speed_ratio = max(0.6, min(speed_ratio, 1.75))
    filter_parts = []
    if abs(speed_ratio - 1.0) > 0.04:
        filter_parts.append(f"atempo={speed_ratio:.4f}")

    filter_arg = ["-filter:a", ",".join(filter_parts)] if filter_parts else []

    cmd = [
        "ffmpeg", "-y",
        "-i", input_wav,
        *filter_arg,
        "-ar", str(target_sample_rate),
        "-ac", "1",
        "-acodec", "pcm_s16le",
        output_wav,
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_wav


def align_and_assemble_audio(
    segments: List[Dict[str, Any]],
    tts_engine,
    total_duration: float,
    work_dir: str,
    threads: int = 1,
    sample_rate: int = 24000,
) -> str:
    """
    Synthesize all segments, apply parallel time-stretching if necessary,
    and assemble the master audio track in-memory for maximum speed and zero drift.
    """
    seg_dir = Path(work_dir) / "segments"
    seg_dir.mkdir(parents=True, exist_ok=True)
    final_dubbed_wav = str(Path(work_dir) / "dubbed_full.wav")

    # Step 1: Synthesize all segments to raw files
    synth_tasks = []
    for idx, seg in enumerate(segments):
        raw_path = str(seg_dir / f"seg_{idx}_raw.wav")
        synth_tasks.append((idx, seg, raw_path))

    # Synthesize sequentially (TTS models are optimized internally)
    for idx, seg, raw_path in synth_tasks:
        tts_engine.synthesize(seg["text"], raw_path)

    # Step 2: Determine which segments need time stretching or sample rate adjustment
    process_tasks = []
    for idx, seg, raw_path in synth_tasks:
        target_duration = max(0.2, seg["duration"])
        try:
            with wave.open(raw_path, "rb") as wf:
                actual_duration = wf.getnframes() / float(wf.getframerate())
                needs_resample = (wf.getframerate() != sample_rate or wf.getnchannels() != 1 or wf.getsampwidth() != 2)
        except Exception:
            actual_duration = target_duration
            needs_resample = True

        needs_stretch = actual_duration > target_duration * 1.05
        speed_ratio = (actual_duration / target_duration) if needs_stretch else 1.0

        proc_path = str(seg_dir / f"seg_{idx}_proc.wav")
        process_tasks.append((idx, seg, raw_path, proc_path, speed_ratio, needs_stretch or needs_resample))

    # Step 3: Run processing (atempo / resample) in parallel if threads > 1
    def _process_one(task):
        idx, seg, raw_path, proc_path, speed_ratio, needed = task
        if needed:
            stretch_or_resample_audio(raw_path, proc_path, speed_ratio, target_sample_rate=sample_rate)
            return idx, proc_path
        else:
            return idx, raw_path

    workers = threads if threads > 0 else (os.cpu_count() or 1)
    if workers > 1 and len(process_tasks) > 1:
        with ThreadPoolExecutor(max_workers=workers) as executor:
            processed_results = dict(executor.map(_process_one, process_tasks))
    else:
        processed_results = dict([_process_one(t) for t in process_tasks])

    # Step 4: Assemble Master Audio Timeline in Memory (Zero Subprocesses, Zero Drift)
    total_samples = int(max(total_duration, max((s["end"] for s in segments), default=0.0) + 1.0) * sample_rate)
    bytes_per_sample = 2  # 16-bit PCM mono
    master_buffer = bytearray(total_samples * bytes_per_sample)

    for idx, seg in enumerate(segments):
        audio_file = processed_results[idx]
        try:
            r, w, ch, pcm_bytes = get_wav_info(audio_file)
        except Exception:
            continue

        start_sample = int(seg["start"] * sample_rate)
        num_samples = len(pcm_bytes) // bytes_per_sample

        if start_sample >= total_samples:
            continue

        insert_samples = min(num_samples, total_samples - start_sample)
        start_byte = start_sample * bytes_per_sample
        end_byte = start_byte + (insert_samples * bytes_per_sample)

        master_buffer[start_byte:end_byte] = pcm_bytes[: insert_samples * bytes_per_sample]

    # Step 5: Write the single master WAV file
    with wave.open(final_dubbed_wav, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(bytes_per_sample)
        wf.setframerate(sample_rate)
        wf.writeframes(master_buffer)

    return final_dubbed_wav
