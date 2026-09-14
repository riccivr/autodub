"""Tests for optional Demucs vocal separation."""

import sys
from pathlib import Path
from unittest.mock import patch

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from autodub.separator import separate_accompaniment


def test_missing_demucs_raises():
    with patch("autodub.separator.demucs_available", return_value=False):
        try:
            separate_accompaniment("in.wav", "/tmp")
            assert False, "expected RuntimeError"
        except RuntimeError as err:
            assert "pip install demucs" in str(err)


if __name__ == "__main__":
    test_missing_demucs_raises()
    print("test_separator passed")
