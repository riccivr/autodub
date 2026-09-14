"""
Command-line interface for autodub.
"""

import os
import sys
import shutil
import argparse
import tempfile
from pathlib import Path

from autodub.downloader import download_or_prepare_media
from autodub.transcriber import transcribe_audio
from autodub.translator import translate_segments
from autodub.tts import get_tts_engine, DEFAULT_PIPER_VOICE, DEFAULT_EDGE_VOICE
from autodub.aligner import align_and_assemble_audio
from autodub.muxer import mux_dubbed_video, mux_dual_audio_video


def run_pipeline(
    source: str,
    target_lang: str = "es",
    source_lang: str = "en",
    engine_name: str = "piper",
    voice: str = None,
    whisper_model: str = "base",
    threads: int = 1,
    output_dir: str = "./output",
    background_volume: float = 0.15,
    dual_audio: bool = False,
    keep_work_dir: bool = False,
):
    total_system_cpus = os.cpu_count() or 1
    active_threads = total_system_cpus if threads <= 0 else threads

    print("-" * 60)
    print("autodub")
    print(f"source:        {source}")
    print(f"target lang:   {target_lang}")
    print(f"tts engine:    {engine_name}")
    print(f"whisper model: {whisper_model}")
    print(f"threads:       {active_threads}/{total_system_cpus}")
    print("-" * 60)

    work_dir = tempfile.mkdtemp(prefix="autodub_")
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Download or prepare media
        print("\n[1/6] Preparing media and extracting audio...")
        media_info = download_or_prepare_media(source, work_dir, threads=active_threads)
        video_path = media_info["video_path"]
        audio_path = media_info["audio_path"]
        title = media_info["title"]
        duration = media_info["duration"]
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()[:100]
        print(f"  video: {title} ({duration:.1f}s)")
        original_output = Path(video_path)

        # Step 2: Transcribe with Whisper
        print(f"\n[2/6] Transcribing with faster-whisper ({whisper_model}, {active_threads} threads)...")
        segments = transcribe_audio(
            audio_path,
            model_size=whisper_model,
            language=source_lang,
            threads=active_threads,
        )
        print(f"  transcribed {len(segments)} segments")
        if not segments:
            print("  no speech detected in audio file")
            return

        for seg in segments[:3]:
            print(f"    [{seg['start']:.1f}s -> {seg['end']:.1f}s] {seg['text']}")
        if len(segments) > 3:
            print(f"    ... and {len(segments) - 3} more segments")

        # Step 3: Translate segments
        print(f"\n[3/6] Translating segments to '{target_lang}' ({active_threads} threads)...")
        translated_segments = translate_segments(
            segments,
            source_lang=source_lang,
            target_lang=target_lang,
            threads=active_threads,
        )
        for seg in translated_segments[:3]:
            print(f"    [{seg['start']:.1f}s -> {seg['end']:.1f}s] {seg['text']}")
        print(f"  translated {len(translated_segments)} segments")

        # Step 4: Initialize TTS Engine
        print(f"\n[4/6] Initializing TTS engine ({engine_name})...")
        if not voice:
            voice = DEFAULT_PIPER_VOICE if engine_name == "piper" else DEFAULT_EDGE_VOICE
        tts_engine = get_tts_engine(engine_name, voice=voice)
        print(f"  voice: {voice}")

        # Step 5: Synthesize and Align Audio
        print("\n[5/6] Synthesizing speech and assembling audio track...")
        dubbed_wav = align_and_assemble_audio(
            translated_segments,
            tts_engine=tts_engine,
            total_duration=duration,
            work_dir=work_dir,
            threads=active_threads,
        )
        print("  assembled dubbed audio track")

        # Step 6: Remux Video
        print("\n[6/6] Remuxing final video...")
        dubbed_output = output_path / f"{safe_title}_dubbed_{target_lang}.mp4"
        mux_dubbed_video(
            original_video_path=video_path,
            dubbed_audio_path=dubbed_wav,
            output_video_path=str(dubbed_output),
            background_volume=background_volume,
            threads=active_threads,
        )
        print(f"  output: {dubbed_output}")

        if dual_audio:
            dual_output = output_path / f"{safe_title}_dual_audio.mkv"
            mux_dual_audio_video(
                original_video_path=video_path,
                dubbed_audio_path=dubbed_wav,
                output_video_path=str(dual_output),
                target_lang_code=target_lang,
                source_lang_code=source_lang,
                threads=active_threads,
            )
            print(f"  dual audio: {dual_output}")

        print("\n" + "-" * 60)
        print("Completed:")
        print(f"  Source: {original_output}")
        print(f"  Dubbed: {dubbed_output}")
        if dual_audio:
            print(f"  Dual:   {dual_output}")
        print("-" * 60)

    finally:
        if not keep_work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
        elif keep_work_dir:
            print(f"\nTemporary files preserved at: {work_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="autodub - non-interactive video dubbing tool"
    )
    parser.add_argument("source", help="video URL or local file path")
    parser.add_argument("-l", "--target-lang", default="es", help="target language code (default: es)")
    parser.add_argument("-s", "--source-lang", default="en", help="source language code (default: en)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="CPU threads to use (default: 1, use 0 for all cores)")
    parser.add_argument("--engine", choices=["piper", "edge-tts"], default="piper", help="TTS engine: piper or edge-tts (default: piper)")
    parser.add_argument("--voice", default=None, help="voice model or name")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium"], help="Whisper model size (default: base)")
    parser.add_argument("-o", "--output-dir", default="./output", help="output directory (default: ./output)")
    parser.add_argument("--bg-volume", type=float, default=0.15, help="background audio volume ducking ratio (default: 0.15)")
    parser.add_argument("--dual-audio", action="store_true", help="output an additional dual-audio MKV file")
    parser.add_argument("--keep-work-dir", action="store_true", help="retain temporary segment files")

    args = parser.parse_args()

    run_pipeline(
        source=args.source,
        target_lang=args.target_lang,
        source_lang=args.source_lang,
        engine_name=args.engine,
        voice=args.voice,
        whisper_model=args.whisper_model,
        threads=args.threads,
        output_dir=args.output_dir,
        background_volume=args.bg_volume,
        dual_audio=args.dual_audio,
        keep_work_dir=args.keep_work_dir,
    )


if __name__ == "__main__":
    main()
