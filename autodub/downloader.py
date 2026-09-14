"""
Video and audio downloader module using yt-dlp and ffmpeg.
Supports configurable multi-threaded downloads and extraction.
"""

import os
import subprocess
import json
from pathlib import Path
from typing import Dict, Any


def is_url(path_or_url: str) -> bool:
    """Check if the input looks like an HTTP/HTTPS URL."""
    return path_or_url.startswith("http://") or path_or_url.startswith("https://")


def get_video_duration(video_path: str) -> float:
    """Get video duration in seconds using ffprobe."""
    cmd = [
        "ffprobe",
        "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        video_path,
    ]
    try:
        output = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, text=True).strip()
        return float(output)
    except Exception:
        return 0.0


def extract_audio_for_whisper(video_path: str, audio_output_path: str, threads: int = 1) -> str:
    """Extract 16kHz mono WAV audio from a video for optimal Whisper transcription."""
    os.makedirs(os.path.dirname(audio_output_path), exist_ok=True)
    th_val = str(threads if threads > 0 else 0)
    cmd = [
        "ffmpeg",
        "-y",
        "-threads", th_val,
        "-i", video_path,
        "-vn",
        "-acodec", "pcm_s16le",
        "-ar", "16000",
        "-ac", "1",
        audio_output_path,
    ]
    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg extract failed for {video_path}: {proc.stderr[-500:]}")
    return audio_output_path


def download_or_prepare_media(source: str, work_dir: str, threads: int = 1) -> Dict[str, Any]:
    """
    Given a URL or local file path, prepare the video and extract the Whisper audio.
    """
    os.makedirs(work_dir, exist_ok=True)

    if not is_url(source):
        # Local video file
        local_path = os.path.abspath(source)
        if not os.path.exists(local_path):
            raise FileNotFoundError(f"Input file does not exist: {local_path}")
        title = Path(local_path).stem
        video_path = local_path
    else:
        # Download with yt-dlp
        output_template = os.path.join(work_dir, "%(title).150B.%(ext)s")
        # Use concurrent fragments when threads > 1
        frag_count = str(min(8, threads) if threads > 1 else 1)
        cmd = [
            "yt-dlp",
            "--no-playlist",
            "--concurrent-fragments", frag_count,
            "-f", "bv*[ext=mp4]+ba[ext=m4a]/b[ext=mp4]/bv*+ba/b",
            "--merge-output-format", "mp4",
            "-o", output_template,
            "--print-json",
            source,
        ]
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
        if result.returncode != 0:
            raise RuntimeError(f"yt-dlp download failed:\n{result.stderr}")

        try:
            info = json.loads(result.stdout.strip().split("\n")[0])
            title = info.get("title", "downloaded_video")
            filename = info.get("_filename")
            if filename and os.path.exists(filename):
                video_path = filename
            else:
                mp4_files = list(Path(work_dir).glob("*.mp4"))
                if not mp4_files:
                    raise FileNotFoundError("Could not locate downloaded video file.")
                video_path = str(max(mp4_files, key=os.path.getmtime))
        except Exception:
            title = "downloaded_video"
            mp4_files = list(Path(work_dir).glob("*.mp4"))
            if not mp4_files:
                raise FileNotFoundError("Could not locate downloaded video file.")
            video_path = str(max(mp4_files, key=os.path.getmtime))

    # Extract 16kHz mono audio for Whisper
    audio_path = os.path.join(work_dir, "original_16k.wav")
    extract_audio_for_whisper(video_path, audio_path, threads=threads)
    duration = get_video_duration(video_path)

    return {
        "video_path": video_path,
        "audio_path": audio_path,
        "title": title,
        "duration": duration,
    }
