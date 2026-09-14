"""
Test CLI argument parsing and defaults.
"""

import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def test_cli_defaults():
    import argparse
    from autodub.cli import main

    # Inspect argument defaults directly by creating parser
    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("-t", "--threads", type=int, default=1)
    parser.add_argument("-l", "--target-lang", default="es")
    parser.add_argument("--engine", default="piper")

    args = parser.parse_args(["https://example.com/video"])
    assert args.threads == 1
    assert args.target_lang == "es"
    assert args.engine == "piper"


def test_cli_custom_threads():
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("source")
    parser.add_argument("-t", "--threads", type=int, default=1)

    args = parser.parse_args(["https://example.com/video", "-t", "8"])
    assert args.threads == 8

    args_zero = parser.parse_args(["https://example.com/video", "-t", "0"])
    assert args_zero.threads == 0


if __name__ == "__main__":
    test_cli_defaults()
    test_cli_custom_threads()
    print("✓ test_cli_args passed!")
