autodub
=======
autodub is a command-line tool that downloads videos, transcribes speech on
CPU with faster-whisper, translates text segments, and generates a synchronized
dubbed audio track using Piper TTS or Edge-TTS.

It runs locally without requiring a dedicated GPU, adjusts playback speed per
segment to match the original speaking window, and preserves background audio
and music.

Translation uses MyMemory/Google and needs network. Only Piper TTS is offline
after the voice model is cached. Edge-TTS and yt-dlp also need network.

How it Works
------------
1. **Download and extraction**: `yt-dlp` fetches the video stream, and `ffmpeg` extracts a 16 kHz mono WAV audio track.
2. **Transcription**: `faster-whisper` runs locally on CPU with int8 quantization to generate timestamped speech segments.
3. **Translation**: Segments are translated to the target language (Spanish by default) while retaining start and end timestamps.
4. **Speech synthesis**: `piper-tts` synthesizes Spanish speech locally via ONNX (or optionally through `edge-tts`).
5. **Timeline alignment**: Audio segments are time-stretched with FFmpeg `atempo` when translation length exceeds the speaking window. Silence is generated in-memory to prevent timeline drift.
6. **Muxing**: `ffmpeg` combines the original video stream, ducks original audio into the background (0.15 volume by default) to keep background effects, and writes the dubbed video.

Features
--------
* Runs on CPU: uses int8 quantized CTranslate2 models and ONNX runtimes. No GPU required.
* Zero timeline drift: in-memory PCM timeline assembly keeps speech aligned with video timestamps across long videos.
* Background audio retention: ducks original audio rather than muting it, preserving ambient sound and music.
* Offline default: uses local Piper models. An optional Edge-TTS backend is available for cloud neural voices.
* Dual-audio output: optional `--dual-audio` flag writes an MKV container with switchable original and dubbed audio tracks.
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
autodub.sh [-l lang] [-s lang] [-t threads] [--engine engine] [--voice voice] [-o dir] [--dual-audio] <url|file>
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

Examples
--------
Dub a YouTube video using the default local Piper model on 1 core:
```sh
./autodub.sh "https://www.youtube.com/watch?v=EXAMPLE_ID"
```

Dub using all available CPU cores:
```sh
./autodub.sh -t 0 "https://www.youtube.com/watch?v=EXAMPLE_ID"
```

Dub using Edge-TTS with a Mexican Spanish voice:
```sh
./autodub.sh --engine edge-tts --voice es-MX-DaliaNeural -t 4 "https://www.youtube.com/watch?v=EXAMPLE_ID"
```

Dub a local video file and generate a dual-audio container:
```sh
./autodub.sh --dual-audio /path/to/video.mp4
```

Performance Tuning
------------------
By default, autodub uses one thread (`-t 1`) to keep CPU usage low for background execution.

For faster processing on multi-core systems:
* `-t 4`: 4 threads for Whisper transcription and parallel translation requests.
* `-t 8`: 8 threads for faster processing on medium or long videos.
* `-t 0`: Uses all detected CPU cores (`os.cpu_count()`).

Supported Voices
----------------

### Piper (Local / Offline)
* `es_ES-davefx-medium` (default European Spanish male)
* `es_ES-sharvard-medium` (European Spanish female)
* `es_MX-ald-medium` (Mexican Spanish male)

### Edge-TTS (Cloud Neural)
* `es-ES-AlvaroNeural` (default European Spanish male)
* `es-ES-ElviraNeural` (European Spanish female)
* `es-MX-DaliaNeural` (Mexican Spanish female)
* `es-MX-JorgeNeural` (Mexican Spanish male)

Running Tests
-------------
```sh
.venv/bin/python tests/test_cli_args.py
.venv/bin/python tests/test_translation_concurrent.py
.venv/bin/python tests/test_in_memory_aligner.py
.venv/bin/python tests/test_e2e.py
```
