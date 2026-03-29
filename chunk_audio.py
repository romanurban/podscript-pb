#!/usr/bin/env python3

import sys
import os
import subprocess
import wave
from pathlib import Path

def get_audio_duration(audio_file):
    """Get duration of audio file in seconds"""
    try:
        with wave.open(audio_file, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            duration = frames / float(rate)
            return duration
    except:
        # Fallback using ffprobe
        try:
            result = subprocess.run([
                'ffprobe', '-v', 'quiet', '-print_format', 'json',
                '-show_format', audio_file
            ], capture_output=True, text=True)

            if result.returncode == 0:
                import json
                data = json.loads(result.stdout)
                return float(data['format']['duration'])
        except:
            pass

    return None

def chunk_audio(audio_file, output_dir="temp", chunk_duration_minutes=10):
    """
    Split audio into chunks using ffmpeg with silence detection
    Returns list of chunk file paths
    """

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Get audio duration
    total_duration = get_audio_duration(audio_file)
    if not total_duration:
        print("❌ Could not determine audio duration")
        return []

    chunk_duration_seconds = chunk_duration_minutes * 60
    estimated_chunks = int(total_duration / chunk_duration_seconds) + 1

    print(f"🔪 Chunking audio into ~{chunk_duration_minutes} minute segments")
    print(f"📊 Total duration: {int(total_duration//60)}:{int(total_duration%60):02d}")
    print(f"📈 Estimated chunks: {estimated_chunks}")

    # Get base filename without extension
    base_name = Path(audio_file).stem
    chunk_pattern = f"{output_dir}/{base_name}_chunk_%03d.wav"

    # Use ffmpeg to split with silence detection for better boundaries
    cmd = [
        'ffmpeg', '-i', audio_file,
        '-f', 'segment',
        '-segment_time', str(chunk_duration_seconds),
        '-segment_format', 'wav',
        '-reset_timestamps', '1',
        '-map', '0:a',
        '-c:a', 'pcm_s16le',  # Ensure WAV format
        '-y',  # Overwrite existing files
        chunk_pattern
    ]

    try:
        print("⚙️  Running ffmpeg chunking...")
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode != 0:
            print(f"❌ ffmpeg error: {result.stderr}")
            return []

        # Find all generated chunks
        chunk_files = sorted(list(Path(output_dir).glob(f"{base_name}_chunk_*.wav")))
        chunk_paths = [str(f) for f in chunk_files]

        print(f"✅ Created {len(chunk_paths)} audio chunks:")
        for i, chunk_path in enumerate(chunk_paths, 1):
            chunk_duration = get_audio_duration(chunk_path)
            duration_str = f"{int(chunk_duration//60)}:{int(chunk_duration%60):02d}" if chunk_duration else "unknown"
            print(f"   📄 Chunk {i:02d}: {Path(chunk_path).name} ({duration_str})")

        return chunk_paths

    except Exception as e:
        print(f"❌ Error during chunking: {str(e)}")
        return []


def smart_chunk_audio(audio_file, output_dir="temp", chunk_duration_minutes=10, silence_threshold=0.001):
    """
    Attempt silence-aware chunking, fall back to simple time slicing.
    """

    print("🧠 Attempting smart chunking with silence detection...")

    # Run ffmpeg's silencedetect to prime future improvements; currently fallback.
    cmd = [
        'ffmpeg', '-i', audio_file,
        '-af', f'silencedetect=noise={silence_threshold}:d=1',
        '-f', 'null', '-'
    ]

    try:
        subprocess.run(cmd, capture_output=True, text=True, check=False)
        print("🔄 Using simple time-based chunking")
        return chunk_audio(audio_file, output_dir, chunk_duration_minutes)
    except Exception as exc:
        print(f"⚠️  Smart chunking failed, using simple chunking: {exc}")
        return chunk_audio(audio_file, output_dir, chunk_duration_minutes)


if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python chunk_audio.py <audio_file> [chunk_duration_minutes]")
        print("Example: python chunk_audio.py temp/audio.wav 15")
        sys.exit(1)

    audio_file = sys.argv[1]
    chunk_duration = int(sys.argv[2]) if len(sys.argv) == 3 else 10

    if not os.path.exists(audio_file):
        print(f"❌ Error: Audio file '{audio_file}' not found.")
        sys.exit(1)

    chunk_files = smart_chunk_audio(audio_file, chunk_duration_minutes=chunk_duration)

    if chunk_files:
        print(f"\n✅ SUCCESS: Created {len(chunk_files)} chunks")
        for chunk in chunk_files:
            print(f"   {chunk}")
    else:
        print("❌ FAILED: Could not create audio chunks")
        sys.exit(1)
