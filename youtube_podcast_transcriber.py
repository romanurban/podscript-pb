#!/usr/bin/env python3

import sys
import os
import shutil
import time
from pathlib import Path
import subprocess

# Import our custom modules
from extract_youtube_audio import extract_youtube_audio
from chunk_audio import smart_chunk_audio
from transcribe_chunks import transcribe_chunks

def cleanup_temp_files(temp_dir="temp"):
    """Clean up temporary files"""
    if os.path.exists(temp_dir):
        try:
            shutil.rmtree(temp_dir)
            print(f"🧹 Cleaned up temporary directory: {temp_dir}")
        except Exception as e:
            print(f"⚠️  Could not clean up {temp_dir}: {str(e)}")

def sanitize_filename(filename):
    """Sanitize filename for safe filesystem usage"""
    # Remove or replace problematic characters
    invalid_chars = '<>:"/\\|?*'
    for char in invalid_chars:
        filename = filename.replace(char, '_')

    # Limit length
    if len(filename) > 100:
        filename = filename[:100]

    return filename.strip()

def find_final_output(safe_title):
    """Check if final merged transcription already exists and is valid."""
    txt = f"output/{safe_title}_transcription.txt"
    json_file = f"output/{safe_title}_transcription.json"
    srt = f"output/{safe_title}_transcription.srt"
    if os.path.exists(txt) and os.path.exists(json_file):
        try:
            with open(json_file, 'r', encoding='utf-8') as f:
                import json
                data = json.load(f)
            if isinstance(data.get('segments'), list) and len(data['segments']) > 0:
                return txt, srt, json_file
        except Exception:
            pass
    return None


def find_existing_audio(output_dir="temp"):
    """Find an existing downloaded audio file in the temp directory."""
    if not os.path.isdir(output_dir):
        return None
    wav_files = sorted(Path(output_dir).glob("*.wav"))
    # Filter out chunk files
    wav_files = [f for f in wav_files if "_chunk_" not in f.name]
    return str(wav_files[-1]) if wav_files else None


def find_existing_chunks(audio_file, output_dir="temp"):
    """Find existing chunk files for a given audio file."""
    base_name = Path(audio_file).stem
    chunk_files = sorted(Path(output_dir).glob(f"{base_name}_chunk_*.wav"))
    return [str(f) for f in chunk_files] if chunk_files else None


def transcribe_youtube_podcast(youtube_url, language=None, chunk_duration=10, cleanup=True):
    """
    Complete pipeline to transcribe a YouTube podcast.
    Resumable: skips steps whose outputs already exist.
    """

    script_start = time.time()
    print("Starting YouTube Podcast Transcription Pipeline")
    print("="*60)
    
    # Log initial system state
    import psutil
    memory = psutil.virtual_memory()
    print(f"🖥️  System state: {memory.percent:.1f}% memory, {memory.available/1024/1024/1024:.1f}GB available")

    try:
        # Step 1: Extract audio from YouTube (skip if audio exists)
        print("\nSTEP 1: Extracting audio from YouTube")
        print("-" * 40)

        audio_file = find_existing_audio("temp")
        if audio_file:
            print(f"Reusing existing audio: {audio_file}")
            # Still need video info for the title — get without downloading
            import yt_dlp
            with yt_dlp.YoutubeDL({'quiet': True}) as ydl:
                video_info = ydl.extract_info(youtube_url, download=False)
        else:
            audio_file, video_info = extract_youtube_audio(youtube_url, "temp")
            if not audio_file:
                print("Failed to extract audio")
                return False, None

        video_title = video_info.get('title', 'youtube_podcast')
        safe_title = sanitize_filename(video_title)
        print(f"Output prefix: {safe_title}")

        # Check if final output already exists
        existing = find_final_output(safe_title)
        if existing:
            print(f"\nFinal transcription already exists: {existing[0]}")
            print("Use --no-cleanup on a fresh run to force retranscription.")
            if cleanup:
                cleanup_temp_files()
            return True, existing

        # Step 2: Chunk the audio (skip if chunks exist)
        print(f"\nSTEP 2: Chunking audio into {chunk_duration}-minute segments")
        print("-" * 40)

        chunk_files = find_existing_chunks(audio_file, "temp")
        if chunk_files:
            print(f"Reusing {len(chunk_files)} existing audio chunks")
        else:
            chunk_files = smart_chunk_audio(
                audio_file,
                output_dir="temp",
                chunk_duration_minutes=chunk_duration
            )
            if not chunk_files:
                print("Failed to create audio chunks")
                return False, None

        # Step 3: Transcribe all chunks (individually resumable)
        print("\nSTEP 3: Transcribing audio chunks")
        print("-" * 40)

        output_files = transcribe_chunks(chunk_files, safe_title, language)

        if not output_files:
            print("Failed to transcribe chunks")
            return False, None

        # Step 4: Report results
        total_time = time.time() - script_start

        print("\n" + "="*60)
        print("YOUTUBE PODCAST TRANSCRIPTION COMPLETE!")
        print("="*60)
        print(f"Video: {video_title}")
        print(f"URL: {youtube_url}")
        print(f"Language: {language or 'auto-detected'}")
        print(f"Chunks processed: {len(chunk_files)}")
        print(f"Total time: {total_time:.1f}s ({total_time/60:.1f} minutes)")
        print("-" * 60)
        txt_file, srt_file, json_file = output_files
        print(f"Output files:")
        print(f"  TXT: {txt_file}")
        print(f"  SRT: {srt_file}")
        print(f"  JSON: {json_file}")
        print("="*60)

        # Step 5: Cleanup (optional)
        if cleanup:
            cleanup_temp_files()

        return True, output_files

    except KeyboardInterrupt:
        print("\nProcess interrupted by user — rerun to resume")
        return False, None

    except Exception as e:
        print(f"\nUnexpected error: {e}")
        print("Temp files preserved for resume — rerun to continue")
        return False, None

def main():
    """Main function with argument parsing"""

    if len(sys.argv) < 2:
        print("YouTube Podcast Transcriber")
        print("="*40)
        print("Usage: python youtube_podcast_transcriber.py <youtube_url> [options]")
        print()
        print("Arguments:")
        print("  youtube_url     YouTube video URL")
        print()
        print("Options:")
        print("  --language LANG Language code (ru, en, es, fr, de, etc.)")
        print("  --chunk-size N  Chunk duration in minutes (default: 10)")
        print("  --no-cleanup    Keep temporary files")
        print()
        print("Examples:")
        print("  python youtube_podcast_transcriber.py 'https://www.youtube.com/watch?v=...'")
        print("  python youtube_podcast_transcriber.py 'https://youtu.be/...' --language ru")
        print("  python youtube_podcast_transcriber.py 'https://youtu.be/...' --chunk-size 15")
        sys.exit(1)

    # Parse arguments
    youtube_url = sys.argv[1]
    language = None
    chunk_duration = 10
    cleanup = True

    i = 2
    while i < len(sys.argv):
        arg = sys.argv[i]
        if arg == '--language' and i + 1 < len(sys.argv):
            language = sys.argv[i + 1]
            i += 2
        elif arg == '--chunk-size' and i + 1 < len(sys.argv):
            try:
                chunk_duration = int(sys.argv[i + 1])
            except ValueError:
                print(f"❌ Invalid chunk size: {sys.argv[i + 1]}")
                sys.exit(1)
            i += 2
        elif arg == '--no-cleanup':
            cleanup = False
            i += 1
        else:
            print(f"❌ Unknown argument: {arg}")
            sys.exit(1)

    # Validate URL
    if not ('youtube.com' in youtube_url or 'youtu.be' in youtube_url):
        print("❌ Please provide a valid YouTube URL")
        sys.exit(1)

    # Run the transcription pipeline
    success, output_files = transcribe_youtube_podcast(
        youtube_url,
        language=language,
        chunk_duration=chunk_duration,
        cleanup=cleanup
    )

    if success:
        print("\n✅ Transcription completed successfully!")
        sys.exit(0)
    else:
        print("\n❌ Transcription failed!")
        sys.exit(1)

if __name__ == "__main__":
    main()