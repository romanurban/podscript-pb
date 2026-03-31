#!/usr/bin/env python3

import sys
import os
import json
import time
import wave
import gc
import psutil
from faster_whisper import WhisperModel
from tqdm import tqdm
from utils import format_time_srt, format_time_simple

def _normalize_language(value):
    """Normalize language codes; treat 'auto' or empty values as None."""
    if not value:
        return None
    value = value.strip()
    return None if value.lower() == "auto" else value

def _select_initial_prompt(language_code):
    """Return a helpful initial prompt tuned for the target language."""
    lang = (language_code or "en").split("-")[0].lower()
    if lang == "ru":
        return "Следующий текст содержит имена, даты, числа и специальные термины."
    return "The following text may include names, dates, numbers, and technical terms."

def transcribe_audio(audio_file, language=None):
    script_start = time.time()

    if not os.path.exists(audio_file):
        print(f"Error: Audio file '{audio_file}' not found.")
        return

    # Ensure output directory exists
    os.makedirs("output", exist_ok=True)

    # Get audio duration for progress tracking
    try:
        with wave.open(audio_file, 'rb') as wav_file:
            frames = wav_file.getnframes()
            rate = wav_file.getframerate()
            audio_duration = frames / float(rate)
        print(f"Audio duration: {audio_duration:.1f} seconds ({audio_duration/60:.1f} minutes)")
    except:
        audio_duration = None
        print("Could not determine audio duration")

    requested_language = _normalize_language(language)
    default_language = _normalize_language(os.environ.get("PODSCRIPT_DEFAULT_LANGUAGE", "auto"))
    whisper_language = requested_language if requested_language is not None else default_language
    display_language = whisper_language if whisper_language is not None else "auto-detect"
    language_source = "explicit" if requested_language is not None else "default"

    print(f"Starting transcription of: {audio_file}")
    if language_source == "default":
        print(f"Target language: {display_language} (default)")
    else:
        print(f"Target language: {display_language}")
    print("Loading Whisper model (small)...")

    model_start = time.time()
    # Initial prompt to help with rare names and formulas
    initial_prompt = _select_initial_prompt(whisper_language)

    model = WhisperModel("small", compute_type="int8")  # try "base" if CPU is tight
    model_time = time.time() - model_start
    print(f"Model loaded successfully! ({model_time:.1f}s)")

    print("Starting transcription with parameters:")
    print(f"  - Language: {display_language}")
    print(f"  - Beam size: 5")
    print(f"  - Temperature: 0.0")
    print(f"  - VAD filter: enabled")
    print(f"  - Word timestamps: enabled")
    print()

    transcribe_start = time.time()
    segments, info = model.transcribe(
        audio_file,
        language=whisper_language,  # None lets the model auto-detect
        initial_prompt=initial_prompt,
        beam_size=5,
        temperature=0.0,  # cleaner, more faithful decoding
        condition_on_previous_text=True,
        vad_filter=True,
        vad_parameters={"min_silence_duration_ms": 200},
        suppress_blank=True,
        no_speech_threshold=0.6,
        log_prob_threshold=-0.7,
        compression_ratio_threshold=2.4,
        word_timestamps=True
    )

    setup_time = time.time() - transcribe_start
    print(f"Transcription setup completed! ({setup_time:.1f}s)")
    print(f"Detected language: {info.language} (confidence: {info.language_probability:.2%})")
    print()

    # Create output filename
    base_name = os.path.splitext(os.path.basename(audio_file))[0]
    output_file = f"output/{base_name}_transcription.txt"

    # Start timing the actual transcription processing
    processing_start = time.time()

    # Convert segments to list while showing progress with memory monitoring
    segments_list = []
    if audio_duration:
        with tqdm(total=audio_duration, unit="s", desc="🎧 Transcribing",
                 bar_format="{l_bar}{bar}| {n:.1f}s/{total:.1f}s [{elapsed}<{remaining}] {postfix}",
                 colour="green", ascii=False, ncols=100, position=0, leave=True,
                 mininterval=0.1, maxinterval=0.5) as pbar:
            for i, segment in enumerate(segments, 1):
                segments_list.append(segment)
                # Print segment details above the progress bar
                start_time = format_time_simple(segment.start)
                end_time = format_time_simple(segment.end)
                tqdm.write(f"  [{start_time}-{end_time}]: {segment.text.strip()}")
                
                # Memory monitoring and cleanup every 50 segments
                if i % 50 == 0:
                    memory_percent = psutil.virtual_memory().percent
                    if memory_percent > 85:
                        tqdm.write(f"⚠️  High memory usage ({memory_percent:.1f}%) - running garbage collection")
                        gc.collect()
                        memory_percent = psutil.virtual_memory().percent
                        tqdm.write(f"✓ Memory after cleanup: {memory_percent:.1f}%")
                    
                pbar.set_postfix_str(f"Segment {i}")
                pbar.update(segment.end - pbar.n)
                # Force immediate update
                pbar.refresh()
    else:
        # Fallback without progress bar if duration unknown
        for i, segment in enumerate(segments, 1):
            segments_list.append(segment)
            start_time = format_time_simple(segment.start)
            end_time = format_time_simple(segment.end)
            print(f"  Segment {i} [{start_time}-{end_time}]: {segment.text.strip()}")
            
            # Memory monitoring for fallback mode too
            if i % 50 == 0:
                memory_percent = psutil.virtual_memory().percent
                if memory_percent > 85:
                    print(f"⚠️  High memory usage ({memory_percent:.1f}%) - running garbage collection")
                    gc.collect()

    # Calculate and report actual transcription time
    processing_time = time.time() - processing_start
    print(f"\nTranscription processing completed! ({processing_time:.1f}s)")
    print(f"Found {len(segments_list)} segments total")

    # Create output filenames
    srt_file = f"output/{base_name}_transcription.srt"
    json_file = f"output/{base_name}_transcription.json"

    # Save as TXT (no console output)
    with open(output_file, "w", encoding="utf-8") as f:
        f.write(f"Language: {info.language}\n")
        f.write(f"Probability: {info.language_probability:.4f}\n\n")
        for s in segments_list:
            start_time = format_time_simple(s.start)
            end_time = format_time_simple(s.end)
            line = f"[{start_time}-{end_time}] {s.text}"
            f.write(line + "\n")

    # Save as SRT
    with open(srt_file, "w", encoding="utf-8") as f:
        for i, s in enumerate(segments_list, 1):
            start_time = format_time_srt(s.start)
            end_time = format_time_srt(s.end)
            f.write(f"{i}\n")
            f.write(f"{start_time} --> {end_time}\n")
            f.write(f"{s.text.strip()}\n\n")

    # Save as JSON
    json_data = {
        "language": info.language,
        "language_probability": info.language_probability,
        "segments": [
            {
                "id": i,
                "start": s.start,
                "end": s.end,
                "text": s.text.strip(),
                "words": [{"word": w.word, "start": w.start, "end": w.end} for w in s.words] if s.words else []
            }
            for i, s in enumerate(segments_list)
        ]
    }

    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(json_data, f, ensure_ascii=False, indent=2)

    total_time = time.time() - script_start

    print()
    print("=" * 50)
    print("TRANSCRIPTION COMPLETE!")
    print("=" * 50)
    print(f"Files saved:")
    print(f"  📄 TXT: {output_file}")
    print(f"  🎬 SRT: {srt_file}")
    print(f"  📊 JSON: {json_file}")
    print(f"Total segments: {len(segments_list)}")
    print(f"⏱️ Total time: {total_time:.1f}s")
    print("=" * 50)

if __name__ == "__main__":
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python transcribe_audio.py <audio_file> [language]")
        print("Example: python transcribe_audio.py audio.wav ru")
        sys.exit(1)

    audio_file = sys.argv[1]
    language = sys.argv[2] if len(sys.argv) == 3 else None
    transcribe_audio(audio_file, language)
