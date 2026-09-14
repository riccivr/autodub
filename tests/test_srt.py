"""Tests for SRT export."""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.srt import format_timestamp, write_srt


def test_format_timestamp():
    assert format_timestamp(0) == "00:00:00,000"
    assert format_timestamp(1.5) == "00:00:01,500"
    assert format_timestamp(3661.25) == "01:01:01,250"


def test_write_srt(tmp_path=None):
    import tempfile
    segments = [
        {"id": 0, "start": 0.0, "end": 1.5, "text": "Hello", "orig_text": "Hi"},
        {"id": 1, "start": 2.0, "end": 3.0, "text": "World"},
    ]
    with tempfile.TemporaryDirectory() as d:
        out = Path(d) / "out.srt"
        write_srt(segments, str(out), text_key="text")
        body = out.read_text(encoding="utf-8")
        assert "00:00:00,000 --> 00:00:01,500" in body
        assert "Hello" in body
        assert "World" in body
        write_srt(segments, str(out), text_key="orig_text")
        body = out.read_text(encoding="utf-8")
        assert "Hi" in body


if __name__ == "__main__":
    test_format_timestamp()
    test_write_srt()
    print("test_srt passed")
