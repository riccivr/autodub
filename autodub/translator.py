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
import urllib.parse
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any, Optional

CHROME_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/128.0.0.0 Safari/537.36"
)


def _lang(code: str) -> str:
    return (code or "").lower().replace("_", "-").split("-")[0]


def _translate_google_client(text: str, source_lang: str = "en", target_lang: str = "es") -> Optional[str]:
    """Direct Google Translate client endpoint used by Chrome extensions.

    Fast, reliable, does not hit scraping CAPTCHAs or anonymous daily quotas.
    """
    src = _lang(source_lang)
    tgt = _lang(target_lang)
    params = urllib.parse.urlencode({
        "client": "dict-chrome-ex",
        "sl": src,
        "tl": tgt,
        "q": text,
    })
    url = f"https://clients5.google.com/translate_a/t?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": CHROME_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], str):
                return data[0]
            if isinstance(data, str):
                return data
    except Exception:
        pass
    return None


def _translate_google_api(text: str, source_lang: str = "en", target_lang: str = "es") -> Optional[str]:
    """Secondary Google Translate API endpoint."""
    src = _lang(source_lang)
    tgt = _lang(target_lang)
    params = urllib.parse.urlencode({
        "client": "dict-chrome-ex",
        "sl": src,
        "tl": tgt,
        "dt": "t",
        "q": text,
    })
    url = f"https://translate.googleapis.com/translate_a/single?{params}"
    req = urllib.request.Request(url, headers={"User-Agent": CHROME_USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            if isinstance(data, list) and len(data) > 0 and isinstance(data[0], list):
                parts = [part[0] for part in data[0] if part and len(part) > 0 and part[0]]
                if parts:
                    return "".join(parts)
    except Exception:
        pass
    return None


def translate_text_cloud(text: str, source_lang: str = "en", target_lang: str = "es") -> str:
    """Translate with Google client endpoints, falling back to deep_translator."""
    res = _translate_google_client(text, source_lang, target_lang)
    if res and res.strip():
        return res.strip()

    res = _translate_google_api(text, source_lang, target_lang)
    if res and res.strip():
        return res.strip()

    try:
        from deep_translator import GoogleTranslator
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass

    try:
        from deep_translator import MyMemoryTranslator
        src_map = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}
        tgt_map = {"es": "es-ES", "en": "en-US", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}
        src_mm = src_map.get(source_lang.lower(), source_lang)
        tgt_mm = tgt_map.get(target_lang.lower(), target_lang)
        translated = MyMemoryTranslator(source=src_mm, target=tgt_mm).translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass

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
    if backend in ("argos", "ollama"):
        workers = 1

    def _item(seg: Dict[str, Any]) -> Dict[str, Any]:
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

    # Batch translation for cloud endpoints (dramatically reduces HTTP requests)
    if backend in ("auto", "cloud") and len(segments) > 1:
        batch_size = 20
        results = []
        for i in range(0, len(segments), batch_size):
            batch = segments[i : i + batch_size]
            texts = [s["text"].strip().replace("\n", " ") for s in batch]
            combined = "\n".join(texts)
            translated_combined = _translate_google_client(combined, source_lang, target_lang)
            if translated_combined:
                lines = [ln.strip() for ln in translated_combined.split("\n")]
                if len(lines) == len(batch):
                    for s, ln in zip(batch, lines):
                        results.append({
                            "id": s["id"],
                            "start": s["start"],
                            "end": s["end"],
                            "duration": s["duration"],
                            "orig_text": s["text"],
                            "text": ln or s["text"],
                        })
                    continue

            # Fallback for this batch if line count mismatched or request failed
            for s in batch:
                results.append(_item(s))

        results.sort(key=lambda x: x["id"])
        return results

    if workers <= 1 or len(segments) <= 1:
        return [_item(seg) for seg in segments]

    max_workers = min(4, workers)
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_item, segments))
    results.sort(key=lambda x: x["id"])
    return results
