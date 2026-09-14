"""
Test in-memory PCM audio alignment and zero-drift assembly.
"""

import os
import sys
import wave
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.aligner import align_and_assemble_audio, get_wav_info


class MockTTSEngine:
    """Mock TTS engine generating 1.0s of 24kHz tone for testing."""
    def synthesize(self, text: str, output_wav_path: str, target_duration=None):
        os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
        sample_rate = 24000
        num_samples = int(1.0 * sample_rate)
        dummy_pcm = b"\x10\x20" * num_samples
        with wave.open(output_wav_path, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(dummy_pcm)


def test_in_memory_assembly():
    with tempfile.TemporaryDirectory() as work_dir:
        segments = [
            {"id": 0, "start": 1.0, "end": 2.5, "duration": 1.5, "text": "Segment 1"},
            {"id": 1, "start": 4.0, "end": 5.0, "duration": 1.0, "text": "Segment 2"},
            {"id": 2, "start": 6.5, "end": 8.0, "duration": 1.5, "text": "Segment 3"},
        ]
        total_duration = 10.0
        sample_rate = 24000

        output_wav = align_and_assemble_audio(
            segments=segments,
            tts_engine=MockTTSEngine(),
            total_duration=total_duration,
            work_dir=work_dir,
            threads=2,
            sample_rate=sample_rate,
        )

        assert os.path.exists(output_wav)
        rate, width, channels, frames = get_wav_info(output_wav)
        assert rate == sample_rate
        assert channels == 1
        assert width == 2

        actual_duration = len(frames) / (rate * width)
        print(f"total target: {total_duration}s, actual WAV: {actual_duration}s")
        assert actual_duration >= total_duration
        print("  ok: in-memory assembly matches target duration")


def test_overlapping_segments_no_clobber():
    class UniquePatternTTSEngine:
        """Emits distinct byte patterns per segment."""
        def synthesize(self, text: str, output_wav_path: str, target_duration=None):
            os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
            sample_rate = 24000
            num_samples = int(1.0 * sample_rate)  # exactly 1 second
            byte_val = b"\xAA\xAA" if "first" in text else b"\xBB\xBB"
            with wave.open(output_wav_path, "wb") as wf:
                wf.setnchannels(1)
                wf.setsampwidth(2)
                wf.setframerate(sample_rate)
                wf.writeframes(byte_val * num_samples)

    with tempfile.TemporaryDirectory() as work_dir:
        # Segment 0 wants 1.0s from 1.0s. Segment 1 is cued at 1.5s.
        # Trim the first clip to the next cue instead of sliding the second clip late.
        segments = [
            {"id": 0, "start": 1.0, "end": 2.0, "duration": 1.0, "text": "first segment"},
            {"id": 1, "start": 1.5, "end": 2.5, "duration": 1.0, "text": "second segment"},
        ]
        output_wav = align_and_assemble_audio(
            segments=segments,
            tts_engine=UniquePatternTTSEngine(),
            total_duration=5.0,
            work_dir=work_dir,
            threads=1,
            sample_rate=24000,
        )
        rate, width, channels, frames = get_wav_info(output_wav)
        first_segment_bytes = frames[24000 * 2 : 36000 * 2]
        assert first_segment_bytes == b"\xAA\xAA" * 12000, "First segment was not trimmed to next cue"
        second_segment_bytes = frames[36000 * 2 : 60000 * 2]
        assert second_segment_bytes == b"\xBB\xBB" * 24000, "Second segment missed its original start"
        print("  ok: overlapping segments are trimmed to the next cue")


if __name__ == "__main__":
    test_in_memory_assembly()
    test_overlapping_segments_no_clobber()
    print("test_in_memory_aligner passed")
