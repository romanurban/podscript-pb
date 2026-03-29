#!/usr/bin/env python3

import sys
import os
import json
import time
from pathlib import Path
from tqdm import tqdm

# Import the existing transcription function
from transcribe_audio import transcribe_audio
from utils import format_time_srt, format_time_simple

def chunk_json_path(chunk_file):
    """Return the expected JSON transcription path for a chunk audio file."""
    return f"output/{Path(chunk_file).stem}_transcription.json"


def is_chunk_transcribed(chunk_file):
    """Check if a chunk already has a valid transcription JSON."""
    json_file = chunk_json_path(chunk_file)
    if not os.path.exists(json_file):
        return False
    try:
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        return isinstance(data.get('segments'), list) and len(data['segments']) > 0
    except (json.JSONDecodeError, OSError):
        return False


def load_chunk_transcription(chunk_file):
    """Load an existing chunk transcription JSON."""
    with open(chunk_json_path(chunk_file), 'r', encoding='utf-8') as f:
        return json.load(f)


def transcribe_single_chunk(chunk_file, language=None):
    """
    Transcribe a single audio chunk using the existing transcribe_audio function.
    Skips transcription if a valid output already exists (resume support).
    Returns the transcription data or None on error.
    """

    # Resume: reuse existing transcription if valid
    if is_chunk_transcribed(chunk_file):
        print(f"Reusing existing transcription: {Path(chunk_file).name}")
        return load_chunk_transcription(chunk_file)

    try:
        print(f"Transcribing: {Path(chunk_file).name}")
        transcribe_audio(chunk_file, language)

        json_file = chunk_json_path(chunk_file)
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        else:
            print(f"JSON output not found for {chunk_file}")
            return None

    except Exception as e:
        print(f"Error transcribing {chunk_file}: {e}")
        return None

def merge_transcriptions(transcription_data_list, video_title="merged"):
    """
    Merge multiple transcription results with proper timing offsets
    """

    print("🔗 Merging transcription results...")

    merged_segments = []
    current_time_offset = 0.0
    total_segments = 0

    # Calculate timing offsets and merge segments
    for i, data in enumerate(transcription_data_list):
        if not data or 'segments' not in data:
            continue

        print(f"   📝 Processing chunk {i+1}: {len(data['segments'])} segments")

        for segment in data['segments']:
            # Adjust timing with offset
            adjusted_segment = {
                'id': total_segments,
                'start': segment['start'] + current_time_offset,
                'end': segment['end'] + current_time_offset,
                'text': segment['text'],
                'words': []
            }

            # Adjust word timestamps if available
            if 'words' in segment and segment['words']:
                adjusted_segment['words'] = [
                    {
                        'word': word['word'],
                        'start': word['start'] + current_time_offset,
                        'end': word['end'] + current_time_offset
                    }
                    for word in segment['words']
                ]

            merged_segments.append(adjusted_segment)
            total_segments += 1

        # Update time offset for next chunk
        if data['segments']:
            last_segment = data['segments'][-1]
            current_time_offset = last_segment['end'] + current_time_offset

    # Create merged result
    merged_data = {
        'language': transcription_data_list[0]['language'] if transcription_data_list else 'unknown',
        'language_probability': sum(d.get('language_probability', 0) for d in transcription_data_list) / len(transcription_data_list),
        'segments': merged_segments
    }

    print(f"✅ Merged {len(merged_segments)} total segments from {len(transcription_data_list)} chunks")

    return merged_data

def save_merged_results(merged_data, output_prefix, cleanup_chunks=True):
    """
    Save merged transcription in all formats (TXT, SRT, JSON)
    """

    print(f"💾 Saving merged results as '{output_prefix}'...")

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Save TXT
    txt_file = f"output/{output_prefix}_transcription.txt"
    with open(txt_file, 'w', encoding='utf-8') as f:
        f.write(f"Language: {merged_data['language']}\n")
        f.write(f"Probability: {merged_data['language_probability']:.4f}\n\n")
        for segment in merged_data['segments']:
            start_time = format_time_simple(segment['start'])
            end_time = format_time_simple(segment['end'])
            f.write(f"[{start_time}-{end_time}] {segment['text']}\n")

    # Save SRT
    srt_file = f"output/{output_prefix}_transcription.srt"
    with open(srt_file, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(merged_data['segments'], 1):
            start_time = format_time_srt(segment['start'])
            end_time = format_time_srt(segment['end'])
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{segment['text'].strip()}\n\n")

    # Save JSON
    json_file = f"output/{output_prefix}_transcription.json"
    with open(json_file, 'w', encoding='utf-8') as f:
        json.dump(merged_data, f, ensure_ascii=False, indent=2)

    print(f"✅ Files saved:")
    print(f"   📄 TXT: {txt_file}")
    print(f"   🎬 SRT: {srt_file}")
    print(f"   📊 JSON: {json_file}")

    # Cleanup individual chunk transcription files
    if cleanup_chunks:
        print("🧹 Cleaning up chunk transcription files...")
        chunk_files = list(Path("output").glob("*chunk*_transcription.*"))
        for chunk_file in chunk_files:
            try:
                chunk_file.unlink()
            except:
                pass
        if chunk_files:
            print(f"   🗑️  Removed {len(chunk_files)} chunk files")

    return txt_file, srt_file, json_file

def transcribe_chunks(chunk_files, output_prefix, language=None):
    """
    Transcribe all chunks and merge the results
    """

    if not chunk_files:
        print("No chunk files provided")
        return None

    # Count how many are already done
    already_done = sum(1 for f in chunk_files if is_chunk_transcribed(f))
    remaining = len(chunk_files) - already_done

    print(f"Starting transcription of {len(chunk_files)} audio chunks")
    if already_done > 0:
        print(f"  Resuming: {already_done} already transcribed, {remaining} remaining")
    print(f"Output prefix: {output_prefix}")

    # Transcribe each chunk
    transcription_data_list = []

    with tqdm(total=len(chunk_files), desc="Transcribing chunks",
              bar_format="{l_bar}{bar}| {n}/{total} [{elapsed}<{remaining}]",
              colour="blue", initial=0) as pbar:

        for i, chunk_file in enumerate(chunk_files, 1):
            pbar.set_postfix_str(f"Chunk {i}")

            transcription_data = transcribe_single_chunk(chunk_file, language)

            if transcription_data:
                transcription_data_list.append(transcription_data)
            else:
                pbar.write(f"Failed chunk {i}/{len(chunk_files)}")

            pbar.update(1)

    if not transcription_data_list:
        print("No chunks were successfully transcribed")
        return None

    print(f"Successfully transcribed {len(transcription_data_list)}/{len(chunk_files)} chunks")

    # Merge results
    merged_data = merge_transcriptions(transcription_data_list, output_prefix)

    # Save merged results
    return save_merged_results(merged_data, output_prefix)

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python transcribe_chunks.py <output_prefix> <chunk_file1> [chunk_file2] ... [language]")
        print("Example: python transcribe_chunks.py podcast_episode temp/chunk_001.wav temp/chunk_002.wav ru")
        sys.exit(1)

    output_prefix = sys.argv[1]
    chunk_files = []
    language = None

    # Parse arguments
    for arg in sys.argv[2:]:
        if arg in ['ru', 'en', 'es', 'fr', 'de']:  # Common language codes
            language = arg
        elif os.path.exists(arg):
            chunk_files.append(arg)
        else:
            print(f"⚠️  Warning: File not found: {arg}")

    if not chunk_files:
        print("❌ No valid chunk files found")
        sys.exit(1)

    results = transcribe_chunks(chunk_files, output_prefix, language)

    if results:
        print("\n" + "="*60)
        print("🎉 CHUNK TRANSCRIPTION COMPLETE!")
        print("="*60)
        txt_file, srt_file, json_file = results
        print(f"📄 TXT: {txt_file}")
        print(f"🎬 SRT: {srt_file}")
        print(f"📊 JSON: {json_file}")
        print("="*60)
    else:
        print("❌ Chunk transcription failed")
        sys.exit(1)