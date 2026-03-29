#!/usr/bin/env python3

import sys
import os
import yt_dlp
from pathlib import Path

def extract_youtube_audio(youtube_url, output_dir="temp"):
    """
    Extract audio from YouTube URL using yt-dlp
    Returns: (audio_file_path, video_info) or (None, None) on error
    """

    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)

    # Configure yt-dlp options
    ydl_opts = {
        'format': 'bestaudio/best',
        'outtmpl': f'{output_dir}/%(title)s.%(ext)s',
        'postprocessors': [{
            'key': 'FFmpegExtractAudio',
            'preferredcodec': 'wav',
            'preferredquality': '192',
        }],
        'ffmpeg_location': '/usr/local/bin/ffmpeg',  # Use system ffmpeg
    }

    try:
        print(f"🎥 Extracting audio from: {youtube_url}")

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # Get video info first
            info = ydl.extract_info(youtube_url, download=False)
            video_title = info.get('title', 'Unknown')
            duration = info.get('duration', 0)

            print(f"📺 Title: {video_title}")
            print(f"⏱️  Duration: {duration//60}:{duration%60:02d}")

            # Download and extract audio
            info = ydl.extract_info(youtube_url, download=True)

            # Find the extracted audio file
            expected_filename = f"{output_dir}/{video_title}.wav"
            if os.path.exists(expected_filename):
                audio_file = expected_filename
            else:
                # Fallback: find any .wav file in output directory
                wav_files = list(Path(output_dir).glob("*.wav"))
                if wav_files:
                    audio_file = str(wav_files[-1])  # Use the most recent
                else:
                    print("❌ Error: No audio file found after extraction")
                    return None, None

            print(f"✅ Audio extracted: {audio_file}")
            return audio_file, info

    except Exception as e:
        print(f"❌ Error extracting audio: {str(e)}")
        return None, None

if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python extract_youtube_audio.py <youtube_url>")
        print("Example: python extract_youtube_audio.py 'https://www.youtube.com/watch?v=...'")
        sys.exit(1)

    youtube_url = sys.argv[1]
    audio_file, info = extract_youtube_audio(youtube_url)

    if audio_file:
        print(f"SUCCESS: Audio saved to {audio_file}")
    else:
        print("FAILED: Could not extract audio")
        sys.exit(1)