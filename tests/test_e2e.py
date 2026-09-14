"""
End-to-end integration test for autodub on a synthetic video.
"""

import os
import sys
import subprocess
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def create_synthetic_test_video(output_video_path: str):
    """Generate a 7-second test video with synthesized English speech."""
    os.makedirs(os.path.dirname(os.path.abspath(output_video_path)), exist_ok=True)
    temp_en_wav = "/tmp/synthetic_en.wav"

    import edge_tts
    import asyncio
    async def _gen():
        comm = edge_tts.Communicate("Hello everyone! This is a test video to verify our automatic dubbing tool.", "en-US-GuyNeural")
        await comm.save(temp_en_wav)
    asyncio.run(_gen())

    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", "testsrc=size=640x360:rate=24",
        "-i", temp_en_wav,
        "-c:v", "libx264", "-tune", "stillimage", "-pix_fmt", "yuv420p",
        "-c:a", "aac",
        "-shortest",
        output_video_path,
    ]
    subprocess.check_call(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    print(f"created synthetic video: {output_video_path}")


def main():
    test_video = "/tmp/autodub_test_source.mp4"
    output_dir = str(PROJECT_ROOT / "tests" / "output")

    print("[e2e] step 1: creating synthetic video...")
    create_synthetic_test_video(test_video)

    print("\n[e2e] step 2: running autodub pipeline...")
    from autodub.cli import run_pipeline
    run_pipeline(
        source=test_video,
        target_lang="es",
        source_lang="en",
        engine_name="piper",
        whisper_model="tiny",
        output_dir=output_dir,
        dual_audio=True,
    )

    out_path = Path(output_dir)
    dubbed_files = list(out_path.glob("*dubbed_es.mp4"))
    dual_files = list(out_path.glob("*dual_audio.mkv"))

    print("\n[e2e] step 3: verifying generated files...")
    assert len(dubbed_files) > 0, "dubbed video missing"
    assert len(dual_files) > 0, "dual-audio mkv missing"

    dubbed = dubbed_files[0]
    dual = dual_files[0]
    print(f"  dubbed video: {dubbed.name} ({dubbed.stat().st_size} bytes)")
    print(f"  dual-audio video: {dual.name} ({dual.stat().st_size} bytes)")
    assert dubbed.stat().st_size > 1000
    assert dual.stat().st_size > 1000

    print("\ne2e test passed")


if __name__ == "__main__":
    main()
