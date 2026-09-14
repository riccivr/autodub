"""
Text-to-Speech (TTS) module supporting Piper TTS (offline local ONNX) and Edge-TTS (free cloud neural).
"""

import os
import asyncio
import subprocess
import urllib.request
from pathlib import Path
from typing import Optional

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


def voice_lang_prefix(voice_name: str) -> Optional[str]:
    """Return ISO-639-1 prefix from a Piper or Edge voice name, if present."""
    if not voice_name:
        return None
    name = Path(voice_name).name.lower()
    if len(name) >= 3 and name[2] in "-_":
        prefix = name[:2]
        if prefix.isalpha():
            return prefix
    return None


def assert_voice_matches_target(voice_name: str, target_lang: str, engine_name: str = "piper"):
    """Reject a resolved voice whose language prefix disagrees with -l."""
    prefix = voice_lang_prefix(voice_name)
    lang = (target_lang or "").lower().replace("_", "-")
    lang_prefix = lang.split("-")[0]
    if prefix and lang_prefix and prefix != lang_prefix:
        raise ValueError(
            f"{engine_name} voice {voice_name!r} is '{prefix}' but target language is '{target_lang}'; "
            f"pass --voice for {target_lang}"
        )


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
        except Exception as exc:
            raise RuntimeError(f"Failed to load Piper voice {self.model_path}") from exc

    def synthesize(self, text: str, output_wav_path: str, target_duration=None):
        """Synthesize text to output_wav_path using Piper."""
        os.makedirs(os.path.dirname(output_wav_path) or ".", exist_ok=True)
        import wave
        syn_kwargs = {}
        if target_duration and target_duration > 0:
            try:
                from piper.config import SynthesisConfig
            except Exception:
                try:
                    from piper import SynthesisConfig
                except Exception:
                    SynthesisConfig = None
            if SynthesisConfig is not None:
                # First pass at default rate, then rescale if we can estimate.
                # length_scale > 1 is slower. Rough char-rate estimate: 12 chars/sec.
                estimated = max(0.4, len(text) / 12.0)
                length_scale = max(0.6, min(estimated / float(target_duration), 1.8))
                syn_kwargs["syn_config"] = SynthesisConfig(length_scale=length_scale)
        with wave.open(output_wav_path, "wb") as wav_file:
            self.voice.synthesize_wav(text, wav_file, **syn_kwargs)


class EdgeTTSEngine:
    def __init__(self, voice_name: str = DEFAULT_EDGE_VOICE):
        self.voice_name = voice_name

    def synthesize(self, text: str, output_wav_path: str, target_duration=None):
        """Synthesize text and convert Edge-TTS MP3 output to 24 kHz mono s16 WAV."""
        import edge_tts
        os.makedirs(os.path.dirname(output_wav_path) or ".", exist_ok=True)
        raw_path = output_wav_path + ".edge.bin"

        async def _run():
            communicate = edge_tts.Communicate(text, self.voice_name)
            await communicate.save(raw_path)

        try:
            asyncio.run(_run())
            cmd = [
                "ffmpeg", "-y",
                "-i", raw_path,
                "-ar", "24000",
                "-ac", "1",
                "-acodec", "pcm_s16le",
                output_wav_path,
            ]
            proc = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.PIPE, text=True)
            if proc.returncode != 0:
                raise RuntimeError(f"ffmpeg failed converting Edge-TTS audio: {proc.stderr[-500:]}")
        finally:
            if os.path.exists(raw_path):
                os.remove(raw_path)


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
