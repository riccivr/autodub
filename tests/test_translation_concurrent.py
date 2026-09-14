"""
Test translation serial (threads=1) vs concurrent (threads=4).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.translator import translate_segments

def test_translation_serial_and_concurrent():
    sample_segments = [
        {"id": 0, "start": 0.0, "end": 2.0, "duration": 2.0, "text": "Good morning."},
        {"id": 1, "start": 2.0, "end": 4.5, "duration": 2.5, "text": "Welcome to our video tutorial."},
        {"id": 2, "start": 4.5, "end": 7.0, "duration": 2.5, "text": "This is a test of the translation engine."},
    ]

    print("[TEST] Running serial translation (threads=1)...")
    res_serial = translate_segments(sample_segments, source_lang="en", target_lang="es", threads=1)
    assert len(res_serial) == 3
    assert res_serial[0]["id"] == 0
    assert len(res_serial[0]["text"]) > 0

    print("[TEST] Running concurrent translation (threads=4)...")
    res_concurrent = translate_segments(sample_segments, source_lang="en", target_lang="es", threads=4)
    assert len(res_concurrent) == 3
    assert res_concurrent[0]["id"] == 0
    assert res_concurrent[1]["id"] == 1
    assert res_concurrent[2]["id"] == 2
    assert len(res_concurrent[1]["text"]) > 0

    print("  ✓ Serial & concurrent translation both completed and preserved IDs.")


if __name__ == "__main__":
    test_translation_serial_and_concurrent()
    print("✓ test_translation_concurrent passed!")
