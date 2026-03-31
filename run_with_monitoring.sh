#!/bin/bash

# Enhanced YouTube Transcriber with Resource Monitoring
# Runs transcription with background monitoring and caffeinate protection

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run: python3 -m venv venv"
    exit 1
fi

# Update yt-dlp
if [ -x "venv/bin/yt-dlp" ]; then
    echo "🔄 Updating yt-dlp..."
    if "venv/bin/yt-dlp" -U >/dev/null 2>&1; then
        echo "✅ yt-dlp is up to date"
    else
        echo "⚠️  Self-update via yt-dlp failed; trying pip upgrade..."
        "./venv/bin/python" -m pip install --quiet --upgrade yt-dlp
    fi
fi

# Start background monitor
echo "🔍 Starting resource monitor..."
"./venv/bin/python" run_monitor.py 30 &
MONITOR_PID=$!

# Cleanup function
cleanup() {
    echo "🧹 Cleaning up..."
    if kill -0 $MONITOR_PID 2>/dev/null; then
        echo "🔴 Stopping resource monitor..."
        kill $MONITOR_PID
    fi
}

# Set trap for cleanup
trap cleanup EXIT INT TERM

# Check system readiness
echo "🔍 Checking system readiness..."
if ! "./venv/bin/python" memory_check.py --force-check; then
    echo "⚠️  System may not be optimal for long transcription"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "❌ Transcription cancelled"
        exit 1
    fi
fi

echo "🔋 Running transcription with system protection..."
echo "📊 Monitor PID: $MONITOR_PID"

# Run main transcription with caffeinate
caffeinate -s "./venv/bin/python" youtube_podcast_transcriber.py "$@"
TRANSCRIPTION_EXIT=$?

# Cleanup will run automatically via trap
exit $TRANSCRIPTION_EXIT