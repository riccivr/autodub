"""
Test CLI argument parsing and defaults against the real parser.
"""

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


if __name__ == "__main__":
    test_cli_defaults()
    test_cli_custom_threads()
    print("test_cli_args passed")
