"""
Translation module to translate transcribed segments to target language (e.g. Spanish).
Supports configurable concurrent thread pool execution.
"""

import os
from concurrent.futures import ThreadPoolExecutor
from typing import List, Dict, Any
from deep_translator import MyMemoryTranslator, GoogleTranslator


def translate_text(text: str, source_lang: str = "en", target_lang: str = "es") -> str:
    """Translate single text with provider fallback."""
    if not text or not text.strip():
        return text

    # Standardize language codes for MyMemory (e.g. en -> en-US, es -> es-ES)
    src_map = {"en": "en-US", "es": "es-ES", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}
    tgt_map = {"es": "es-ES", "en": "en-US", "fr": "fr-FR", "de": "de-DE", "it": "it-IT"}

    src_mm = src_map.get(source_lang.lower(), source_lang)
    tgt_mm = tgt_map.get(target_lang.lower(), target_lang)

    # 1. Try MyMemory
    try:
        translated = MyMemoryTranslator(source=src_mm, target=tgt_mm).translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass

    # 2. Try GoogleTranslator
    try:
        translated = GoogleTranslator(source=source_lang, target=target_lang).translate(text)
        if translated and translated.strip():
            return translated.strip()
    except Exception:
        pass

    # Fallback to original text if both fail
    return text


def translate_segments(
    segments: List[Dict[str, Any]],
    source_lang: str = "en",
    target_lang: str = "es",
    threads: int = 1,
) -> List[Dict[str, Any]]:
    """
    Translate segment text from source_lang to target_lang.
    Preserves start, end, and duration timing data.
    Uses ThreadPoolExecutor when threads > 1 for fast concurrent network I/O.
    """
    if not segments:
        return []

    workers = threads if threads > 0 else (os.cpu_count() or 1)

    if workers <= 1 or len(segments) <= 1:
        # Serial execution (default when threads=1)
        translated_segments = []
        for seg in segments:
            translated_text = translate_text(seg["text"], source_lang=source_lang, target_lang=target_lang)
            translated_segments.append({
                "id": seg["id"],
                "start": seg["start"],
                "end": seg["end"],
                "duration": seg["duration"],
                "orig_text": seg["text"],
                "text": translated_text,
            })
        return translated_segments

    # Concurrent execution when threads > 1
    max_workers = min(32, workers * 2)

    def _translate_item(seg):
        translated = translate_text(seg["text"], source_lang=source_lang, target_lang=target_lang)
        return {
            "id": seg["id"],
            "start": seg["start"],
            "end": seg["end"],
            "duration": seg["duration"],
            "orig_text": seg["text"],
            "text": translated,
        }

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(_translate_item, segments))

    # Ensure results maintain original order by ID
    results.sort(key=lambda x: x["id"])
    return results
