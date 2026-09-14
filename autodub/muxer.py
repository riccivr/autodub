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

    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_video_path


def mux_dual_audio_video(
    original_video_path: str,
    dubbed_audio_path: str,
    output_video_path: str,
    target_lang_code: str = "spa",
    threads: int = 1,
) -> str:
    """
    Create a container with both English and dubbed Spanish audio tracks.
    Track 0: Original Audio (English)
    Track 1: Dubbed Audio (Spanish)
    """
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    th_val = str(threads if threads > 0 else 0)

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
        "-metadata:s:a:0", "language=eng",
        "-metadata:s:a:0", "title=Original (English)",
        "-metadata:s:a:1", f"language={target_lang_code}",
        "-metadata:s:a:1", "title=Dubbed (Spanish)",
        output_video_path,
    ]

    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return output_video_path
