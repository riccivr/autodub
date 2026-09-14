"""
Test translation serial (threads=1) vs concurrent (threads=4).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import pytest

from autodub.translator import translate_segments

pytestmark = pytest.mark.network


def test_translation_serial_and_concurrent():
    sample_segments = [
        {"id": 0, "start": 0.0, "end": 2.0, "duration": 2.0, "text": "Good morning."},
        {"id": 1, "start": 2.0, "end": 4.5, "duration": 2.5, "text": "Welcome to our video tutorial."},
        {"id": 2, "start": 4.5, "end": 7.0, "duration": 2.5, "text": "This is a test of the translation engine."},
    ]

    print("[test] running serial translation (threads=1)...")
    res_serial = translate_segments(sample_segments, source_lang="en", target_lang="es", threads=1)
    assert len(res_serial) == 3
    assert res_serial[0]["id"] == 0
    assert len(res_serial[0]["text"]) > 0

    print("[test] running concurrent translation (threads=4)...")
    res_concurrent = translate_segments(sample_segments, source_lang="en", target_lang="es", threads=4)
    assert len(res_concurrent) == 3
    assert res_concurrent[0]["id"] == 0
    assert res_concurrent[1]["id"] == 1
    assert res_concurrent[2]["id"] == 2
    assert len(res_concurrent[1]["text"]) > 0

    print("  ok: serial and concurrent translation both preserved segment IDs")


def test_translation_failure_raises_runtime_error():
    from unittest.mock import patch
    from autodub.translator import translate_text

    with patch("deep_translator.MyMemoryTranslator.translate", side_effect=ConnectionError("Mocked network failure")), \
         patch("deep_translator.GoogleTranslator.translate", side_effect=ConnectionError("Mocked network failure")):
        failed = False
        try:
            translate_text("Test sentence", source_lang="en", target_lang="es", backend="cloud")
        except RuntimeError as err:
            failed = True
            assert "translation failed for en->es" in str(err)
        assert failed, "Expected RuntimeError on translation failure"
        print("  ok: translation failure raises RuntimeError as expected")


if __name__ == "__main__":
    test_translation_serial_and_concurrent()
    test_translation_failure_raises_runtime_error()
    print("test_translation_concurrent passed")
