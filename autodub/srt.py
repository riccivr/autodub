"""Write SRT subtitle files from timestamped segments."""

from pathlib import Path
from typing import List, Dict, Any


def format_timestamp(seconds: float) -> str:
    if seconds < 0:
        seconds = 0.0
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    millis = int(round((seconds - int(seconds)) * 1000))
    if millis == 1000:
        secs += 1
        millis = 0
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{millis:03d}"


def write_srt(segments: List[Dict[str, Any]], output_path: str, text_key: str = "text") -> str:
    """Write an SRT file. Uses text_key, falling back to 'text' then 'orig_text'."""
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    blocks = []
    index = 1
    for seg in segments:
        text = (seg.get(text_key) or seg.get("text") or seg.get("orig_text") or "").strip()
        if not text:
            continue
        start = format_timestamp(float(seg.get("start") or 0.0))
        end = format_timestamp(float(seg.get("end") or seg.get("start") or 0.0))
        blocks.append(f"{index}\n{start} --> {end}\n{text}\n")
        index += 1
    path.write_text("\n".join(blocks) + ("\n" if blocks else ""), encoding="utf-8")
    return str(path)
