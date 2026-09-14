"""
Unit tests for autodub components.
"""

import os
import sys
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

def test_imports():
    print("[TEST] Importing dependencies...")
    import faster_whisper
    import deep_translator
    import edge_tts
    from autodub import downloader, transcriber, translator, tts, aligner, muxer, cli
    print("  ✓ All modules imported successfully.")


def test_translator():
    print("\n[TEST] Testing translation...")
    from autodub.translator import translate_segments
    sample_segments = [
        {"id": 0, "start": 0.0, "end": 2.5, "duration": 2.5, "text": "Hello, welcome to this video!"},
        {"id": 1, "start": 2.5, "end": 5.0, "duration": 2.5, "text": "Today we will learn how to dub videos."},
    ]
    translated = translate_segments(sample_segments, source_lang="en", target_lang="es")
    for seg in translated:
        print(f"  EN: {seg['orig_text']}")
        print(f"  ES: {seg['text']}")
        assert len(seg['text']) > 0
    print("  ✓ Translation works!")


def test_edge_tts():
    print("\n[TEST] Testing Edge-TTS synthesis...")
    from autodub.tts import EdgeTTSEngine
    engine = EdgeTTSEngine(voice_name="es-ES-AlvaroNeural")
    test_wav = "/tmp/test_edge.mp3"
    engine.synthesize("Hola, esta es una prueba de voz.", test_wav)
    assert os.path.exists(test_wav) and os.path.getsize(test_wav) > 0
    print(f"  ✓ Edge-TTS generated audio: {os.path.getsize(test_wav)} bytes.")
    os.remove(test_wav)


def test_piper_tts():
    print("\n[TEST] Testing Piper-TTS downloading and synthesis...")
    from autodub.tts import PiperTTSEngine
    engine = PiperTTSEngine(voice_name="es_ES-davefx-medium")
    test_wav = "/tmp/test_piper.wav"
    engine.synthesize("Hola, esta es una prueba con Piper.", test_wav)
    assert os.path.exists(test_wav) and os.path.getsize(test_wav) > 0
    print(f"  ✓ Piper-TTS generated audio: {os.path.getsize(test_wav)} bytes.")
    os.remove(test_wav)


if __name__ == "__main__":
    test_imports()
    test_translator()
    test_edge_tts()
    test_piper_tts()
    print("\n🎉 ALL TESTS PASSED!")
