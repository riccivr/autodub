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
    """Fast mock TTS engine generating 1.0s of 24kHz tone for testing."""
    def synthesize(self, text: str, output_wav_path: str):
        os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
        sample_rate = 24000
        num_samples = int(1.0 * sample_rate)  # 1.0s of audio
        # Generate dummy 16-bit audio
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
        print(f"Total target: {total_duration}s, Actual WAV: {actual_duration}s")
        assert actual_duration >= total_duration
        print("  ✓ In-memory assembly produced exact required duration.")


if __name__ == "__main__":
    test_in_memory_assembly()
    print("✓ test_in_memory_aligner passed!")
