# 🎬 autodub

A lightweight, CPU-friendly command-line tool to automatically download, transcribe, translate, and dub videos from English to Spanish (and other languages) using free and local tools.

---

## ✨ Features

- 📥 **Universal Downloader**: Uses `yt-dlp` to download videos from YouTube, Vimeo, X/Twitter, Reddit, or accepts local video files (`.mp4`, `.mkv`, etc.).
- 🎙️ **Local CPU Transcription**: Uses `faster-whisper` (`base` model with `int8` quantization) for fast, highly accurate speech-to-text with zero GPU requirements.
- 🌐 **Automatic Translation**: Translates speech segments from English to Spanish while retaining precise sentence boundaries. Supports concurrent translation across worker threads.
- 🗣️ **Local & Free TTS**:
  - **Piper TTS (Default)**: 100% offline, local neural speech synthesis via ONNX. Runs in milliseconds on CPU with zero internet needed once downloaded.
  - **Edge-TTS (Optional)**: Free Microsoft neural voices (e.g. `es-ES-AlvaroNeural`, `es-MX-DaliaNeural`) with near-studio quality and zero setup.
- ⚡ **Zero-Subprocess In-Memory Alignment**: Synthesizes and stitches PCM audio directly in memory, eliminating hundreds of temporary FFmpeg subprocesses and guaranteeing **zero drift** throughout long videos.
- 🧵 **Configurable CPU Core Scaling**: Defaults to a single core (`-t 1`) for lightweight background execution, with the ability to unlock all cores (`-t 0` or `-t 16`) for maximum speed.
- 🎞️ **Dual Output**:
  - `video_original.mp4`: The untouched original video.
  - `video_dubbed_es.mp4`: The dubbed Spanish video with soft background audio ducking so sound effects and music are preserved.
  - `video_dual_audio.mkv` *(optional with `--dual-audio`)*: A single video with switchable English and Spanish audio tracks.

---

## 🚀 Quick Start (WSL / Linux)

### 1. Requirements
Ensure `ffmpeg` and `yt-dlp` are installed:
```bash
sudo apt update && sudo apt install -y ffmpeg yt-dlp
```

### 2. Setup Virtual Environment
```bash
cd autodub
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 3. Run autodub
You can run it directly using the provided launcher:
```bash
# Default single-core execution (low resource usage)
./autodub.sh "https://www.youtube.com/watch?v=EXAMPLE_ID"

# Turbo multi-core mode (use all available CPU cores)
./autodub.sh "https://www.youtube.com/watch?v=EXAMPLE_ID" -t 0

# Specify exact core count (e.g., 4 or 8 cores)
./autodub.sh "https://www.youtube.com/watch?v=EXAMPLE_ID" -t 8

# Dub with Edge-TTS for ultra-natural neural voices
./autodub.sh "https://www.youtube.com/watch?v=EXAMPLE_ID" --engine edge-tts -t 0

# Generate an additional dual-audio track file (switch between EN and ES in VLC)
./autodub.sh "https://www.youtube.com/watch?v=EXAMPLE_ID" --dual-audio
```

---

## ⚡ Multi-Core Performance & Scaling

By default, `autodub` runs on **1 CPU core** (`-t 1`), making it quiet and gentle on system resources so you can keep working while it dubs in the background.

When you want videos dubbed as fast as possible, you can scale across your machine's CPU cores:

| Command | CPU Cores | Behavior |
| :--- | :--- | :--- |
| `./autodub.sh <URL>` | **1 (Default)** | Single core, minimal background footprint. |
| `./autodub.sh <URL> -t 4` | **4 cores** | 4x faster Whisper CTranslate2 + concurrent translation. |
| `./autodub.sh <URL> -t 8` | **8 cores** | High-speed processing for medium to long videos. |
| `./autodub.sh <URL> -t 0` | **Auto (All Cores)** | Detects `nproc` (e.g. 16 cores) and unleashes full CPU capability. |

### How Multi-Threading is Applied:
1. **CTranslate2 / Whisper**: Uses OpenMP across the specified number of threads.
2. **Translation**: Dispatches segment translation requests concurrently using a thread pool.
3. **Audio Time-Stretching (`atempo`)**: Runs audio speed alignment in parallel across threads.
4. **FFmpeg & yt-dlp**: Passes thread counts to FFmpeg encoding and chunk downloading.

---

## 🛠️ Options & Flags

| Flag | Default | Description |
| :--- | :--- | :--- |
| `source` | *(required)* | Video URL (YouTube, Vimeo, etc.) or local video path |
| `-t`, `--threads` | `1` | CPU threads to use (`1` = single core, `0` = all cores, or specific number) |
| `-l`, `--target-lang` | `es` | Target language code (`es`, `fr`, `de`, `it`, etc.) |
| `-s`, `--source-lang` | `en` | Source language code |
| `--engine` | `piper` | TTS engine: `piper` (offline CPU) or `edge-tts` (free cloud neural) |
| `--voice` | `None` (auto) | Specific voice name |
| `--whisper-model` | `base` | Model size: `tiny`, `base`, `small`, `medium` |
| `-o`, `--output-dir` | `./output` | Output folder for generated videos |
| `--bg-volume` | `0.15` | Background volume for original audio/music (0.0 to 1.0) |
| `--dual-audio` | `false` | Also generate a single MKV file with both audio tracks |
| `--keep-work-dir` | `false` | Retain temporary segment audio files for debugging |

---

## 🎙️ Supported Voices

### Piper Voices (100% Local / Offline)
- `es_ES-davefx-medium` (Default European Spanish)
- `es_ES-sharvard-medium` (European Spanish)
- `es_MX-ald-medium` (Mexican Spanish)

### Edge-TTS Voices (Cloud Neural)
- `es-ES-AlvaroNeural` (Default European Spanish Male)
- `es-ES-ElviraNeural` (European Spanish Female)
- `es-MX-DaliaNeural` (Mexican Spanish Female)
- `es-MX-JorgeNeural` (Mexican Spanish Male)

---

## 🧪 Running Tests

A full test suite is included in `tests/`:

```bash
# Run all unit tests
.venv/bin/python tests/test_cli_args.py
.venv/bin/python tests/test_translation_concurrent.py
.venv/bin/python tests/test_in_memory_aligner.py

# Run end-to-end pipeline test
.venv/bin/python tests/test_e2e.py
```
