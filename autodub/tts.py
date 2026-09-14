"""
Text-to-Speech (TTS) module supporting Piper TTS (offline local ONNX) and Edge-TTS (free cloud neural).
"""

import os
import sys
import asyncio
import subprocess
import urllib.request
from pathlib import Path
from typing import List, Dict, Any, Optional

# Pre-defined voice models for Piper TTS on Hugging Face
PIPER_VOICE_MAP = {
    "es_ES-davefx-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/davefx/medium/es_ES-davefx-medium.onnx.json",
    },
    "es_ES-sharvard-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_ES/sharvard/medium/es_ES-sharvard-medium.onnx.json",
    },
    "es_MX-ald-medium": {
        "onnx": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx",
        "json": "https://huggingface.co/rhasspy/piper-voices/resolve/main/es/es_MX/ald/medium/es_MX-ald-medium.onnx.json",
    },
}

DEFAULT_PIPER_VOICE = "es_ES-davefx-medium"
DEFAULT_EDGE_VOICE = "es-ES-AlvaroNeural"


def get_cache_dir() -> Path:
    """Return local cache directory for models."""
    cache = Path(os.environ.get("AUTODUB_CACHE", Path.home() / ".cache" / "autodub"))
    cache.mkdir(parents=True, exist_ok=True)
    return cache


def download_file(url: str, dest_path: Path):
    """Download a file with progress display."""
    if dest_path.exists() and dest_path.stat().st_size > 0:
        return
    print(f"Downloading {dest_path.name} from Hugging Face...")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, str(dest_path))


def ensure_piper_model(voice_name: str = DEFAULT_PIPER_VOICE) -> Path:
    """Ensure Piper voice ONNX and JSON files are present locally."""
    if voice_name not in PIPER_VOICE_MAP:
        # If user passed a direct path to an onnx file
        onnx_file = Path(voice_name)
        if onnx_file.exists():
            return onnx_file
        raise ValueError(f"Unknown Piper voice '{voice_name}'. Available defaults: {list(PIPER_VOICE_MAP.keys())}")

    voice_dir = get_cache_dir() / "piper" / voice_name
    onnx_path = voice_dir / f"{voice_name}.onnx"
    json_path = voice_dir / f"{voice_name}.onnx.json"

    download_file(PIPER_VOICE_MAP[voice_name]["onnx"], onnx_path)
    download_file(PIPER_VOICE_MAP[voice_name]["json"], json_path)

    return onnx_path


class PiperTTSEngine:
    def __init__(self, voice_name: str = DEFAULT_PIPER_VOICE):
        self.voice_name = voice_name
        self.model_path = ensure_piper_model(voice_name)
        self.voice = None
        self._init_piper()

    def _init_piper(self):
        try:
            from piper import PiperVoice
            self.voice = PiperVoice.load(str(self.model_path))
        except Exception:
            # Fallback to piper CLI if python binding fails
            self.voice = None

    def synthesize(self, text: str, output_wav_path: str):
        """Synthesize text to output_wav_path using Piper."""
        os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)
        if self.voice is not None:
            import wave
            with wave.open(output_wav_path, "wb") as wav_file:
                self.voice.synthesize_wav(text, wav_file)
        else:
            # CLI fallback
            cmd = [
                sys.executable, "-m", "piper",
                "--model", str(self.model_path),
                "--output_file", output_wav_path,
            ]
            process = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            stdout, stderr = process.communicate(input=text)
            if process.returncode != 0:
                raise RuntimeError(f"Piper synthesis error: {stderr}")


class EdgeTTSEngine:
    def __init__(self, voice_name: str = DEFAULT_EDGE_VOICE):
        self.voice_name = voice_name

    def synthesize(self, text: str, output_wav_path: str):
        """Synthesize text to output_wav_path using Edge-TTS."""
        import edge_tts
        os.makedirs(os.path.dirname(output_wav_path), exist_ok=True)

        async def _run():
            communicate = edge_tts.Communicate(text, self.voice_name)
            await communicate.save(output_wav_path)

        asyncio.run(_run())


def get_tts_engine(engine_name: str = "piper", voice: Optional[str] = None):
    """Factory to get the desired TTS engine."""
    if engine_name.lower() == "piper":
        voice = voice or DEFAULT_PIPER_VOICE
        return PiperTTSEngine(voice)
    elif engine_name.lower() in ("edge", "edge-tts"):
        voice = voice or DEFAULT_EDGE_VOICE
        return EdgeTTSEngine(voice)
    else:
        raise ValueError(f"Unsupported TTS engine: {engine_name}. Choose 'piper' or 'edge-tts'.")
