autodub
=======
autodub is a command-line tool that downloads videos, transcribes speech on
CPU with faster-whisper, translates text segments, and generates a synchronized
dubbed audio track using Piper TTS or Edge-TTS.

It runs locally without requiring a dedicated GPU, adjusts playback speed per
segment to match the original speaking window, and preserves background audio
and music.

Translation defaults to batched Google endpoints (`--translator auto`). Pass
`--translator argos` or `--translator ollama` for a local backend. Piper TTS
is offline after the voice is cached. Edge-TTS, yt-dlp, and first-run Argos
package installs need network.

How it works
------------
1. **Download and extraction**: `yt-dlp` fetches the video stream, and `ffmpeg` extracts a 16 kHz mono WAV audio track.
2. **Transcription**: `faster-whisper` runs locally on CPU with int8 quantization to generate timestamped speech segments.
3. **Translation**: Segments are batched and translated into the target language (Spanish by default) while retaining start and end timestamps.
4. **Speech synthesis**: `piper-tts` synthesizes Spanish speech locally via ONNX (or optionally through `edge-tts`).
5. **Timeline alignment**: Audio segments are time-stretched with FFmpeg `atempo` when translation length exceeds the speaking window. Silence is generated in-memory to prevent timeline drift.
6. **Muxing**: `ffmpeg` combines the original video stream, ducks original audio into the background (0.15 volume by default) to keep background effects, and writes the dubbed video.

Features
--------
* Runs on CPU: uses int8 quantized CTranslate2 models and ONNX runtimes. No GPU required.
* Whisper defaults to `base` with `beam_size=1` (greedy) for CPU speed, not max accuracy. Use `--whisper-model small` or `medium` when quality matters.
* Batched translation: batches speech segments into grouped requests to avoid rate limits, scrapers, and CAPTCHA blocks.
* Zero timeline drift: in-memory PCM timeline assembly keeps speech aligned with video timestamps across long videos.
* Background audio retention: ducks original audio rather than muting it, preserving ambient sound and music.
* Local Piper TTS after the voice is cached.
* Dual-audio output: optional `--dual-audio` flag writes an MKV container with switchable original and dubbed audio tracks.
* Subtitles: writes original and translated `.srt` files next to the dubbed video.
* Local translation: `--translator argos` or `--translator ollama`.
* Optional vocal split: `--separate-vocals` (Demucs) so music stays full-level.
* Configurable CPU threading: defaults to 1 core for light background execution, scales to all available cores via `-t`.

Requirements
------------
* Python 3.9+
* `ffmpeg` and `ffprobe`
* `yt-dlp`

On Debian, Ubuntu, or WSL:
```sh
sudo apt update && sudo apt install -y ffmpeg yt-dlp python3-venv
```

Installation
------------
```sh
git clone https://github.com/riccivr/autodub.git
cd autodub
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/pip install -e .
```

Usage
-----
```sh
autodub [-l lang] [-s lang] [-t threads] [--engine engine] [--voice voice]
        [--translator auto|cloud|argos|ollama] [--separate-vocals] [--no-srt]
        [-o dir] [--dual-audio] <url|file>
```

Or using the repository script:
```sh
./autodub.sh [options] <url|file>
```

### Options
* `-l, --target-lang`: Target language code (default: `es`).
* `-s, --source-lang`: Source language code (default: `en`).
* `-t, --threads`: CPU threads to use (default: `1`, use `0` for all cores).
* `--engine`: TTS engine: `piper` or `edge-tts` (default: `piper`).
* `--voice`: Specific voice model name.
* `--whisper-model`: Whisper model size: `tiny`, `base`, `small`, `medium` (default: `base`).
* `-o, --output-dir`: Output directory for generated files (default: `./output`).
* `--bg-volume`: Background volume ratio for original audio ducking (default: `0.15`, use `0.0` for full replacement).
* `--dual-audio`: Output an additional MKV file containing both original and dubbed audio tracks.
* `--keep-work-dir`: Preserve intermediate segment audio files.
* `--translator`: `auto`/`cloud` (batched Google with fallbacks), `argos` (local Argos Translate), or `ollama` (local LLM). Default: `auto`.
* `--no-srt`: Do not write original and translated `.srt` files.
* `--separate-vocals`: Run Demucs, keep accompaniment at full level, replace only speech. Requires `pip install demucs`.

Examples
--------
Dub a YouTube video using the default local Piper model on 1 core:
```sh
autodub "https://www.youtube.com/watch?v=EXAMPLE_ID"
```

Dub using all available CPU cores:
```sh
autodub -t 0 "https://www.youtube.com/watch?v=EXAMPLE_ID"
```

Dub using Edge-TTS with a Mexican Spanish voice:
```sh
autodub --engine edge-tts --voice es-MX-DaliaNeural -t 4 "https://www.youtube.com/watch?v=EXAMPLE_ID"
```

Dub a local video file and generate a dual-audio container:
```sh
autodub --dual-audio /path/to/video.mp4
```

Local translation plus vocal separation:
```sh
autodub --translator argos --separate-vocals /path/to/video.mp4
```

Ollama translation uses `OLLAMA_HOST` (default `http://127.0.0.1:11434`) and
`AUTODUB_OLLAMA_MODEL` (default `llama3.2`).

Optional extras:
```sh
.venv/bin/pip install -e ".[local,separate,dev]"
```

Performance tuning
------------------
By default, autodub uses one thread (`-t 1`) to keep CPU usage low for background execution.

For faster processing on multi-core systems:
* `-t 4`: 4 threads for Whisper transcription and parallel operations.
* `-t 8`: 8 threads for faster processing on medium or long videos.
* `-t 0`: Uses all detected CPU cores (`os.cpu_count()`).

Supported voices
----------------

### Piper (local / offline)
* `es_ES-davefx-medium` (default European Spanish male)
* `es_ES-sharvard-medium` (European Spanish female)
* `es_MX-ald-medium` (Mexican Spanish male)

### Edge-TTS (cloud neural)
* `es-ES-AlvaroNeural` (default European Spanish male)
* `es-ES-ElviraNeural` (European Spanish female)
* `es-MX-DaliaNeural` (Mexican Spanish female)
* `es-MX-JorgeNeural` (Mexican Spanish male)

Running tests
-------------
```sh
.venv/bin/pip install -e ".[dev]"
.venv/bin/pytest -m "not network"
.venv/bin/python tests/test_e2e.py
```

License
-------
MIT
