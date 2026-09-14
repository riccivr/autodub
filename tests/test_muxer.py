"""
Test muxer functions and metadata tagging.
"""

import os
import sys
import subprocess
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.muxer import mux_dual_audio_video


def test_mux_dual_audio_metadata():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a dummy video and dummy audio
        video_path = os.path.join(tmpdir, "input.mp4")
        audio_path = os.path.join(tmpdir, "dubbed.wav")
        output_path = os.path.join(tmpdir, "dual.mkv")

        subprocess.check_call([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10",
            "-f", "lavfi", "-i", "sine=frequency=1000:duration=1",
            "-t", "1",
            "-c:v", "libx264", "-c:a", "aac",
            video_path,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.check_call([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=500:duration=1",
            "-t", "1",
            audio_path,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mux_dual_audio_video(
            original_video_path=video_path,
            dubbed_audio_path=audio_path,
            output_video_path=output_path,
            target_lang_code="de",
            source_lang_code="fr",
        )

        assert os.path.exists(output_path)

        # Inspect metadata with ffprobe
        probe_cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "stream_tags=title,language",
            "-select_streams", "a",
            "-of", "default=noprint_wrappers=1",
            output_path,
        ]
        output = subprocess.check_output(probe_cmd, text=True)
        assert "language=fr" in output or "tag:language=fr" in output
        assert "language=de" in output or "tag:language=de" in output
        assert "Original (fr)" in output
        assert "Dubbed (de)" in output
        print("  ok: dual-audio metadata correctly tagged with dynamic language codes")


def test_mux_dual_audio_fails_without_source_audio():
    with tempfile.TemporaryDirectory() as tmpdir:
        # Create a video with NO audio stream
        video_no_audio = os.path.join(tmpdir, "silent.mp4")
        audio_path = os.path.join(tmpdir, "dubbed.wav")
        output_path = os.path.join(tmpdir, "dual.mkv")

        subprocess.check_call([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=320x240:rate=10",
            "-t", "1",
            "-an",  # no audio
            "-c:v", "libx264",
            video_no_audio,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        subprocess.check_call([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "sine=frequency=500:duration=1",
            "-t", "1",
            audio_path,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        failed = False
        try:
            mux_dual_audio_video(
                original_video_path=video_no_audio,
                dubbed_audio_path=audio_path,
                output_video_path=output_path,
            )
        except RuntimeError as err:
            failed = True
            assert "dual-audio mux needs an original audio stream" in str(err)
        assert failed, "Expected RuntimeError when source video has no audio stream"
        print("  ok: dual-audio mux fails early when source lacks audio stream")


if __name__ == "__main__":
    test_mux_dual_audio_metadata()
    test_mux_dual_audio_fails_without_source_audio()
    print("test_muxer passed")
