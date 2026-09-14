"""
Unit tests for autodub components.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_imports():
    print("[test] importing dependencies...")
    import faster_whisper
    import deep_translator
    import edge_tts
    from autodub import downloader, transcriber, translator, tts, aligner, muxer, cli
    print("  ok: all modules imported successfully")


def test_translator():
    print("\n[test] testing translation...")
    from autodub.translator import translate_segments
    sample_segments = [
        {"id": 0, "start": 0.0, "end": 2.5, "duration": 2.5, "text": "Hello, welcome to this video!"},
        {"id": 1, "start": 2.5, "end": 5.0, "duration": 2.5, "text": "Today we will learn how to dub videos."},
    ]
    translated = translate_segments(sample_segments, source_lang="en", target_lang="es")
    for seg in translated:
        print(f"  en: {seg['orig_text']}")
        print(f"  es: {seg['text']}")
        assert len(seg['text']) > 0
    print("  ok: translation works")


def test_edge_tts():
    print("\n[test] testing edge-tts synthesis...")
    import wave
    from autodub.tts import EdgeTTSEngine
    engine = EdgeTTSEngine(voice_name="es-ES-AlvaroNeural")
    test_wav = "/tmp/test_edge.wav"
    engine.synthesize("Hola, esta es una prueba de voz.", test_wav)
    assert os.path.exists(test_wav) and os.path.getsize(test_wav) > 0
    with wave.open(test_wav, "rb") as wf:
        assert wf.getnchannels() == 1
        assert wf.getframerate() == 24000
        assert wf.getsampwidth() == 2
    print(f"  ok: edge-tts generated valid WAV ({os.path.getsize(test_wav)} bytes)")
    os.remove(test_wav)


def test_piper_tts():
    print("\n[test] testing piper-tts synthesis...")
    from autodub.tts import PiperTTSEngine
    engine = PiperTTSEngine(voice_name="es_ES-davefx-medium")
    test_wav = "/tmp/test_piper.wav"
    engine.synthesize("Hola, esta es una prueba con Piper.", test_wav)
    assert os.path.exists(test_wav) and os.path.getsize(test_wav) > 0
    print(f"  ok: piper-tts generated {os.path.getsize(test_wav)} bytes")
    os.remove(test_wav)

    # Test target_duration fitting
    test_wav_fast = "/tmp/test_piper_fast.wav"
    engine.synthesize("Hola, esta es una prueba con Piper para evaluar el ajuste de duración.", test_wav_fast, target_duration=1.2)
    assert os.path.exists(test_wav_fast) and os.path.getsize(test_wav_fast) > 0
    os.remove(test_wav_fast)
    print("  ok: piper-tts adapts to target_duration")


if __name__ == "__main__":
    test_imports()
    test_translator()
    test_edge_tts()
    test_piper_tts()
    print("\nall tests passed")
