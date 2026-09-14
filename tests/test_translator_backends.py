"""Offline tests for translator backend selection."""

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.translator import translate_text, translate_segments


def test_unknown_backend():
    try:
        translate_text("hello", backend="nope")
        assert False, "expected ValueError"
    except ValueError as err:
        assert "unknown translator backend" in str(err)


def test_empty_text_short_circuit():
    assert translate_text("  ", backend="argos") == "  "


def test_argos_backend_is_used():
    segs = [{"id": 0, "start": 0.0, "end": 1.0, "duration": 1.0, "text": "Hello"}]
    with patch("autodub.translator.translate_text_argos", return_value="Hola") as mock:
        out = translate_segments(segs, backend="argos")
    mock.assert_called_once()
    assert out[0]["text"] == "Hola"
    assert out[0]["orig_text"] == "Hello"


def test_ollama_backend_is_used():
    segs = [{"id": 0, "start": 0.0, "end": 1.0, "duration": 1.0, "text": "Hello"}]
    with patch("autodub.translator.translate_text_ollama", return_value="Hola") as mock:
        out = translate_segments(segs, backend="ollama", threads=8)
    mock.assert_called_once()
    assert out[0]["text"] == "Hola"


if __name__ == "__main__":
    test_unknown_backend()
    test_empty_text_short_circuit()
    test_argos_backend_is_used()
    test_ollama_backend_is_used()
    print("test_translator_backends passed")
