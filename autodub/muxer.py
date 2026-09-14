"""
FFmpeg video and audio remuxing module.
Merges dubbed speech with original video, with support for background audio ducking, multi-threading, and dual-audio tracks.
"""

import os
import subprocess


def mux_dubbed_video(
    original_video_path: str,
    dubbed_audio_path: str,
    output_video_path: str,
    background_volume: float = 0.15,
    threads: int = 1,
) -> str:
    """
    Combine original video stream with the dubbed audio track.
    If background_volume > 0, ducks original audio into the background to keep
    music and sound effects intact.
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    th_val = str(threads if threads > 0 else 0)

    if background_volume > 0.0:
        filter_str = f"[0:a]volume={background_volume:.2f}[bg];[1:a]volume=1.0[voice];[bg][voice]amix=inputs=2:duration=first[aout]"
        cmd = [
            "ffmpeg", "-y",
            "-threads", th_val,
            "-i", original_video_path,
            "-i", dubbed_audio_path,
            "-filter_complex", filter_str,
            "-map", "0:v:0",
            "-map", "[aout]",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video_path,
        ]
    else:
        cmd = [
            "ffmpeg", "-y",
            "-threads", th_val,
            "-i", original_video_path,
            "-i", dubbed_audio_path,
            "-map", "0:v:0",
            "-map", "1:a:0",
            "-c:v", "copy",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            output_video_path,
        ]

    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg mux failed for {output_video_path}: {proc.stderr[-500:]}")
    return output_video_path


def mux_dual_audio_video(
    original_video_path: str,
    dubbed_audio_path: str,
    output_video_path: str,
    target_lang_code: str = "es",
    source_lang_code: str = "en",
    threads: int = 1,
) -> str:
    """
    Create a container with original and dubbed audio tracks.
    Track 0: Original audio
    Track 1: Dubbed audio
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    th_val = str(threads if threads > 0 else 0)

    probe = subprocess.run(
        [
            "ffprobe", "-v", "error",
            "-select_streams", "a:0",
            "-show_entries", "stream=index",
            "-of", "csv=p=0",
            original_video_path,
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if probe.returncode != 0 or not probe.stdout.strip():
        raise RuntimeError(
            f"dual-audio mux needs an original audio stream on {original_video_path}"
        )

    cmd = [
        "ffmpeg", "-y",
        "-threads", th_val,
        "-i", original_video_path,
        "-i", dubbed_audio_path,
        "-map", "0:v:0",
        "-map", "0:a:0",
        "-map", "1:a:0",
        "-c:v", "copy",
        "-c:a", "aac",
        "-b:a", "192k",
        "-metadata:s:a:0", f"language={source_lang_code}",
        "-metadata:s:a:0", f"title=Original ({source_lang_code})",
        "-metadata:s:a:1", f"language={target_lang_code}",
        "-metadata:s:a:1", f"title=Dubbed ({target_lang_code})",
        output_video_path,
    ]

    proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg dual-audio mux failed for {output_video_path}: {proc.stderr[-500:]}")
    return output_video_path
