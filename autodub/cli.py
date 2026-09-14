"""
autodub command line interface.
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
    # Resolve thread count: 0 means all cores, default is 1
    total_system_cpus = os.cpu_count() or 1
    active_threads = total_system_cpus if threads <= 0 else threads

    print("=" * 60)
    print(f"🎬 autodub - Video Dubbing Pipeline")
    print(f"Source:        {source}")
    print(f"Target Lang:   {target_lang}")
    print(f"TTS Engine:    {engine_name}")
    print(f"Whisper Model: {whisper_model}")
    print(f"CPU Threads:   {active_threads} (of {total_system_cpus} available)")
    print("=" * 60)

    work_dir = tempfile.mkdtemp(prefix="autodub_")
    output_path = Path(output_dir).resolve()
    output_path.mkdir(parents=True, exist_ok=True)

    try:
        # Step 1: Download / Extract media
        print("\n[1/6] 📥 Fetching media and extracting audio...")
        media_info = download_or_prepare_media(source, work_dir, threads=active_threads)
        video_path = media_info["video_path"]
        audio_path = media_info["audio_path"]
        title = media_info["title"]
        duration = media_info["duration"]
        safe_title = "".join(c for c in title if c.isalnum() or c in " ._-").strip()[:100]
        print(f"  ✓ Video: '{title}' ({duration:.1f}s)")

        # Save a copy of the original video in output_dir if downloaded
        original_output = output_path / f"{safe_title}_original.mp4"
        if not original_output.exists():
            shutil.copyfile(video_path, str(original_output))
            print(f"  ✓ Original video saved: {original_output.name}")

        # Step 2: Transcribe with Whisper
        print(f"\n[2/6] 🎙️ Transcribing audio with faster-whisper ({whisper_model}, {active_threads} threads)...")
        segments = transcribe_audio(
            audio_path,
            model_size=whisper_model,
            language=source_lang,
            threads=active_threads,
        )
        print(f"  ✓ Transcribed {len(segments)} speech segments.")
        if not segments:
            print("  ⚠️ No speech detected in video! Exiting.")
            return

        # Preview first few segments
        for seg in segments[:3]:
            print(f"    [{seg['start']:.1f}s -> {seg['end']:.1f}s] {seg['text']}")
        if len(segments) > 3:
            print(f"    ... and {len(segments) - 3} more segments.")

        # Step 3: Translate segments
        print(f"\n[3/6] 🌐 Translating segments to '{target_lang}' ({active_threads} threads)...")
        translated_segments = translate_segments(
            segments,
            source_lang=source_lang,
            target_lang=target_lang,
            threads=active_threads,
        )
        for seg in translated_segments[:3]:
            print(f"    [{seg['start']:.1f}s -> {seg['end']:.1f}s] {seg['text']}")
        print(f"  ✓ Translated {len(translated_segments)} segments.")

        # Step 4: Initialize TTS Engine
        print(f"\n[4/6] 🗣️ Initializing TTS Engine ({engine_name})...")
        if not voice:
            voice = DEFAULT_PIPER_VOICE if engine_name == "piper" else DEFAULT_EDGE_VOICE
        tts_engine = get_tts_engine(engine_name, voice=voice)
        print(f"  ✓ TTS Engine ready with voice: {voice}")

        # Step 5: Synthesize and Align Audio
        print("\n[5/6] ⏱️ Synthesizing speech and assembling timeline in memory...")
        dubbed_wav = align_and_assemble_audio(
            translated_segments,
            tts_engine=tts_engine,
            total_duration=duration,
            work_dir=work_dir,
            threads=active_threads,
        )
        print("  ✓ Full dubbed audio track assembled.")

        # Step 6: Remux Video
        print("\n[6/6] 🎞️ Remuxing final video...")
        dubbed_output = output_path / f"{safe_title}_dubbed_{target_lang}.mp4"
        mux_dubbed_video(
            original_video_path=video_path,
            dubbed_audio_path=dubbed_wav,
            output_video_path=str(dubbed_output),
            background_volume=background_volume,
            threads=active_threads,
        )
        print(f"  🎉 Dubbed video created: {dubbed_output}")

        if dual_audio:
            dual_output = output_path / f"{safe_title}_dual_audio.mkv"
            mux_dual_audio_video(
                original_video_path=video_path,
                dubbed_audio_path=dubbed_wav,
                output_video_path=str(dual_output),
                target_lang_code=target_lang,
                threads=active_threads,
            )
            print(f"  🎉 Dual-track video created: {dual_output}")

        print("\n" + "=" * 60)
        print("✨ Dubbing Complete!")
        print(f"1. Original: {original_output}")
        print(f"2. Dubbed:   {dubbed_output}")
        if dual_audio:
            print(f"3. Dual:     {dual_output}")
        print("=" * 60)

    finally:
        if not keep_work_dir and os.path.exists(work_dir):
            shutil.rmtree(work_dir, ignore_errors=True)
        elif keep_work_dir:
            print(f"\n[Debug] Work directory kept at: {work_dir}")


def main():
    parser = argparse.ArgumentParser(
        description="autodub - Local, CPU-friendly automatic video dubbing CLI"
    )
    parser.add_argument("source", help="Video URL (YouTube, Vimeo, etc.) or local file path")
    parser.add_argument("-l", "--target-lang", default="es", help="Target language code (default: es)")
    parser.add_argument("-s", "--source-lang", default="en", help="Source language code (default: en)")
    parser.add_argument("-t", "--threads", type=int, default=1, help="CPU threads to use (default: 1. Use 0 for all available cores)")
    parser.add_argument("--engine", choices=["piper", "edge-tts"], default="piper", help="TTS Engine: 'piper' (local CPU) or 'edge-tts' (free cloud neural)")
    parser.add_argument("--voice", default=None, help="Voice model or name")
    parser.add_argument("--whisper-model", default="base", choices=["tiny", "base", "small", "medium"], help="Whisper model size (default: base)")
    parser.add_argument("-o", "--output-dir", default="./output", help="Output directory for generated videos")
    parser.add_argument("--bg-volume", type=float, default=0.15, help="Background volume of original audio track (0.0 to 1.0, default: 0.15)")
    parser.add_argument("--dual-audio", action="store_true", help="Generate an additional dual-audio track file (MKV)")
    parser.add_argument("--keep-work-dir", action="store_true", help="Keep scratch/intermediate files for inspection")

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
