"""
Translation module for timestamped speech segments.

Backends:
  auto   - MyMemory then Google (default, needs network)
  cloud  - same as auto
  argos  - local Argos Translate packages
  ollama - local Ollama HTTP API
"""

import json
import os
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any


def _lang(code: str) -> str:
    return (code or "").lower().replace("_", "-").split("-")[0]


def translate_text_cloud(text: str, source_lang: str = "en", target_lang: str = "es") -> str:
    """Translate with MyMemory then Google. Raises if both fail."""
    from deep_translator import MyMemoryTranslator, GoogleTranslator

    src_map = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}
    tgt_map = {"es": "es-ES", "en": "en-US", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}
    src_mm = src_map.get(source_lang.lower(), source_lang)
    tgt_mm = tgt_map.get(target_lang.lower(), target_lang)

    try:
        translated = MyMemoryTranslator(source=src_mm, target=tgt_mm).translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception as exc:
        print(f"  warn: MyMemory failed: {exc}")

    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception as exc:
        print(f"  warn: GoogleTranslator failed: {exc}")

    raise RuntimeError(
        f"translation failed for {source_lang}->{target_lang}: {text[:80]!r}"
    )


def _ensure_argos_pair(source_lang: str, target_lang: str):
    import argostranslate.package
    import argostranslate.translate

    src = _lang(source_lang)
    tgt = _lang(target_lang)
    try:
        sample = argostranslate.translate.translate("ok", src, tgt)
        if sample is not None:
            return
    except Exception:
        pass

    print(f"  installing Argos package {src}->{tgt} (one-time download)...")
    argostranslate.package.update_package_index()
    available = argostranslate.package.get_available_packages()
    package = next((p for p in available if p.from_code == src and p.to_code == tgt), None)
    if package is None:
        raise RuntimeError(
            f"no Argos package for {src}->{tgt}; install argostranslate and a matching language pair"
        )
    download_path = package.download()
    argostranslate.package.install_from_path(download_path)


def translate_text_argos(text: str, source_lang: str = "en", target_lang: str = "es") -> str:
    try:
        import argostranslate.translate
    except ImportError as exc:
        raise RuntimeError(
            "Argos Translate is not installed. pip install argostranslate"
        ) from exc
    _ensure_argos_pair(source_lang, target_lang)
    translated = argostranslate.translate.translate(text, _lang(source_lang), _lang(target_lang))
    if not translated or not translated.strip():
        raise RuntimeError(f"Argos returned empty translation for {text[:80]!r}")
    return translated.strip()


def translate_text_ollama(text: str, source_lang: str = "en", target_lang: str = "es") -> str:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    model = os.environ.get("AUTODUB_OLLAMA_MODEL", "llama3.2")
    payload = {
        "model": model,
        "stream": False,
        "prompt": (
            f"Translate the following text from {source_lang} to {target_lang}. "
            "Reply with the translation only, no quotes or commentary.\n\n"
            f"{text}"
        ),
    }
    req = urllib.request.Request(
        f"{host}/api/generate",
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=120) as resp:
            body = json.loads(resp.read().decode("utf-8"))
    except Exception as exc:
        raise RuntimeError(
            f"Ollama request failed at {host} (model={model}): {exc}"
        ) from exc
    translated = (body.get("response") or "").strip()
    if not translated:
        raise RuntimeError("Ollama returned an empty translation")
    return translated


def translate_text(
    text: str,
    source_lang: str = "en",
    target_lang: str = "es",
    backend: str = "auto",
) -> str:
    if not text or not text.strip():
        return text
    name = (backend or "auto").lower()
    if name in ("auto", "cloud"):
        return translate_text_cloud(text, source_lang, target_lang)
    if name == "argos":
        return translate_text_argos(text, source_lang, target_lang)
    if name == "ollama":
        return translate_text_ollama(text, source_lang, target_lang)
    raise ValueError(f"unknown translator backend: {backend}")


def translate_segments(
    segments: List[Dict[str, Any]],
    source_lang: str = "en",
    target_lang: str = "es",
    threads: int = 1,
    backend: str = "auto",
) -> List[Dict[str, Any]]:
    if not segments:
        return []

    workers = threads if threads > 0 else (os.cpu_count() or 1)
    # Local models are not helped by a wide thread pool.
    if backend in ("argos", "ollama"):
        workers = 1

    def _item(seg):
        translated = translate_text(
            seg["text"],
            source_lang=source_lang,
            target_lang=target_lang,
            backend=backend,
        )
        return {
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "duration": seg["duration"],
            "orig_text": seg["text"],
            "text": translated,
        }

    if workers <= 1 or len(segments) <= 1:
        return [_item(seg) for seg in segments]

    max_workers = min(4, workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_item, segments))
    results.sort(key=lambda x: x["id"])
    return results
