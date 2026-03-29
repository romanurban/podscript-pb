#!/bin/bash

# YouTube Podcast Transcriber Wrapper
# This script automatically activates the virtual environment and runs the transcriber

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv"
    exit 1
fi

# Update yt-dlp to avoid API changes causing failures
if [ -x "venv/bin/yt-dlp" ]; then
    echo "🔄 Updating yt-dlp..."
    if "venv/bin/yt-dlp" -U >/dev/null 2>&1; then
        echo "✅ yt-dlp is up to date"
    else
        echo "⚠️  Self-update via yt-dlp failed; trying pip upgrade..."
        if "./venv/bin/python" -m pip install --quiet --upgrade yt-dlp; then
            echo "✅ yt-dlp upgraded via pip"
        else
            echo "⚠️  Unable to update yt-dlp automatically; continuing with current version"
        fi
    fi
else
    echo "⚠️  yt-dlp executable not found in the virtual environment; skipping auto-update"
fi

# Use the venv directly
exec "./venv/bin/python" youtube_podcast_transcriber.py "$@"
