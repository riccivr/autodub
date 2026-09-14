"""
Test CLI argument parsing and defaults against the real parser.
"""

import os
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.cli import build_parser


def test_cli_defaults():
    args = build_parser().parse_args(["https://example.com/video"])
    assert args.threads == 1
    assert args.target_lang == "es"
    assert args.source_lang == "en"
    assert args.engine == "piper"


def test_cli_custom_threads():
    args = build_parser().parse_args(["https://example.com/video", "-t", "8"])
    assert args.threads == 8

    args_zero = build_parser().parse_args(["https://example.com/video", "-t", "0"])
    assert args_zero.threads == 0


def test_reject_default_piper_voice_on_non_es():
    import tempfile
    import subprocess
    from unittest.mock import patch
    from autodub.cli import run_pipeline

    with tempfile.TemporaryDirectory() as tmpdir:
        dummy_mp4 = os.path.join(tmpdir, "dummy.mp4")
        subprocess.check_call([
            "ffmpeg", "-y",
            "-f", "lavfi", "-i", "testsrc=size=160x120:rate=1",
            "-f", "lavfi", "-i", "sine=duration=1",
            "-t", "1",
            "-c:v", "libx264", "-c:a", "aac",
            dummy_mp4,
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

        mock_segs = [{"id": 0, "start": 0.0, "end": 1.0, "duration": 1.0, "text": "hello"}]
        with patch("autodub.cli.transcribe_audio", return_value=mock_segs), \
             patch("autodub.cli.translate_segments", return_value=mock_segs):
            failed = False
            try:
                run_pipeline(source=dummy_mp4, target_lang="fr", engine_name="piper", voice=None)
            except ValueError as err:
                failed = True
                assert "target language is 'fr'" in str(err)
            assert failed, "Expected ValueError when target_lang='fr' and voice=None"
    print("  ok: rejected default Spanish Piper voice for non-Spanish target")


def test_reject_default_edge_voice_on_non_es():
    from autodub.tts import assert_voice_matches_target, DEFAULT_EDGE_VOICE
    failed = False
    try:
        assert_voice_matches_target(DEFAULT_EDGE_VOICE, "fr", engine_name="edge-tts")
    except ValueError as err:
        failed = True
        assert "target language is 'fr'" in str(err)
    assert failed
    print("  ok: rejected default Spanish Edge voice for non-Spanish target")


def test_reject_explicit_spanish_voice_on_fr():
    from autodub.tts import assert_voice_matches_target
    failed = False
    try:
        assert_voice_matches_target("es_ES-davefx-medium", "fr", engine_name="piper")
    except ValueError:
        failed = True
    assert failed
    print("  ok: rejected explicit Spanish Piper voice for French target")


if __name__ == "__main__":
    test_cli_defaults()
    test_cli_custom_threads()
    test_reject_default_piper_voice_on_non_es()
    test_reject_default_edge_voice_on_non_es()
    test_reject_explicit_spanish_voice_on_fr()
    print("test_cli_args passed")
