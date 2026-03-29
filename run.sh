#!/bin/bash

# Unified Podscript Runner
# Automatically activates the virtual environment and runs the specified script

set -eo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Virtual environment not found. Please run: python3 -m venv venv"
    exit 1
fi

# Show usage if no arguments
if [ $# -eq 0 ]; then
    echo "Podscript Runner"
    echo "================"
    echo "Usage: $0 <command> [arguments...]"
    echo ""
    echo "Commands:"
    echo "  analyze   - Analyze podcast (type + summary + chapters + insights)"
    echo "  render    - Render markdown preview from analysis JSON"
    echo ""
    echo "Examples:"
    echo "  $0 analyze transcript.txt --lang en --top 8"
    echo "  $0 render analysis.json --output preview.md"
    exit 1
fi

# Get the command and map to script file
COMMAND="$1"
shift

case "$COMMAND" in
    analyze)
        SCRIPT_FILE="analyze_podcast.py"
        ;;
    render)
        SCRIPT_FILE="render_preview.py"
        ;;
    *)
        echo "Unknown command: $COMMAND"
        echo "Available commands: analyze, render"
        exit 1
        ;;
esac

# Check if script exists
if [ ! -f "$SCRIPT_FILE" ]; then
    echo "Script not found: $SCRIPT_FILE"
    exit 1
fi

# Run the script with all remaining arguments
exec "./venv/bin/python" "$SCRIPT_FILE" "$@"
