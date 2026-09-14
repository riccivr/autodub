"""Optional vocal/accompaniment separation via Demucs."""

import os
import sys
import shutil
import subprocess
from pathlib import Path
from typing import Optional


def demucs_available() -> bool:
    return shutil.which("demucs") is not None or _module_available("demucs")


def _module_available(name: str) -> bool:
    try:
        __import__(name)
        return True
    except Exception:
        return False


def separate_accompaniment(audio_or_video_path: str, work_dir: str, threads: int = 1) -> Optional[str]:
    """
    Return path to an accompaniment WAV (no vocals), or raise if Demucs is missing.

    Uses `python -m demucs --two-stems=vocals` so only vocals + no_vocals are produced.
    """
    if not demucs_available():
        raise RuntimeError(
            "vocal separation requires Demucs. Install with: pip install demucs"
        )

    out_root = Path(work_dir) / "demucs"
    out_root.mkdir(parents=True, exist_ok=True)
    cmd = [
        sys.executable, "-m", "demucs",
        "--two-stems", "vocals",
        "-n", "htdemucs",
        "-o", str(out_root),
        audio_or_video_path,
    ]
    if threads and threads > 0:
        os.environ.setdefault("OMP_NUM_THREADS", str(threads))

    proc = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    if proc.returncode != 0:
        raise RuntimeError(f"demucs failed: {proc.stderr[-800:]}")

    matches = list(out_root.rglob("no_vocals.wav"))
    if not matches:
        raise RuntimeError("demucs finished but no_vocals.wav was not found")
    return str(matches[0])
