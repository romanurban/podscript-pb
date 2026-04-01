#!/bin/bash

# Master workflow for podcast text analysis
# 2-step pipeline: analyze (single LLM call) -> render (pure Python)

set -euo pipefail

usage() {
    cat <<'EOF'
Usage: ./run_podcast_full_analysis.sh <transcript_file> [options]

Arguments:
  transcript_file           Path to transcript (.txt or .json)

Options:
  --title TITLE             Episode title
  --youtube-id ID            YouTube video ID for embed and timestamp links
  --lang CODE               Output language (default: auto-detected or en)
  --top-insights N          Number of top insights to extract (default: 8)
  --max-chapters N          Maximum chapters (default: 10)
  --force                   Regenerate even if outputs already exist
  --help                    Show this message

Requires the virtual environment to be set up and the helper scripts to be executable.
EOF
}

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ---------------------------------------------------------------------------
# Language detection helper
# ---------------------------------------------------------------------------
detect_transcript_language() {
    python3 - "$1" <<'PY'
import json
import sys

path = sys.argv[1]
language = ""

try:
    if path.endswith(".json"):
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            language = data.get("language") or ""
            if not language:
                meta = data.get("info") or data.get("metadata") or {}
                if isinstance(meta, dict):
                    language = meta.get("language") or ""
            if not language:
                segments = data.get("segments")
                if isinstance(segments, list):
                    for segment in segments:
                        if isinstance(segment, dict):
                            candidate = segment.get("language")
                            if candidate:
                                language = candidate
                                break
    else:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                if line.lower().startswith("language:"):
                    language = line.split(":", 1)[1].strip()
                    break
except Exception:
    language = ""

mapping = {
    "english": "en",
    "русский": "ru",
    "russian": "ru",
    "spanish": "es",
    "español": "es",
    "french": "fr",
    "german": "de",
    "italian": "it",
    "portuguese": "pt",
    "ukrainian": "uk",
    "polish": "pl",
    "chinese": "zh",
    "japanese": "ja",
    "korean": "ko"
}

if language:
    language_norm = language.strip().lower()
    language = mapping.get(language_norm, language.split("-")[0])

print(language)
PY
}

# ---------------------------------------------------------------------------
# Derive base_name from transcript filename
# ---------------------------------------------------------------------------
derive_base_name() {
    local name="$1"
    if [[ "$name" == *_transcription.txt ]]; then
        echo "${name/_transcription.txt/}"
    elif [[ "$name" == *_transcription.json ]]; then
        echo "${name/_transcription.json/}"
    else
        echo "${name%.*}"
    fi
}

# ---------------------------------------------------------------------------
# Parse arguments
# ---------------------------------------------------------------------------
if [[ $# -lt 1 ]]; then
    usage
    exit 1
fi

TRANSCRIPT_FILE=""
TITLE=""
YOUTUBE_ID=""
LANG=""
LANG_SET=0
TOP_INSIGHTS=8
MAX_CHAPTERS=10
RESUME_MODE=1

while [[ $# -gt 0 ]]; do
    case "$1" in
        --title)
            TITLE="$2"
            shift 2
            ;;
        --youtube-id)
            YOUTUBE_ID="$2"
            shift 2
            ;;
        --lang|--lang-hint|--summary-lang)
            LANG="$2"
            LANG_SET=1
            shift 2
            ;;
        --top-insights|--top)
            TOP_INSIGHTS="$2"
            shift 2
            ;;
        --max-chapters|--chapters)
            MAX_CHAPTERS="$2"
            shift 2
            ;;
        --force)
            RESUME_MODE=0
            shift
            ;;
        --help|-h)
            usage
            exit 0
            ;;
        -*)
            echo "Unknown option: $1"
            usage
            exit 1
            ;;
        *)
            if [[ -z "$TRANSCRIPT_FILE" ]]; then
                TRANSCRIPT_FILE="$1"
            else
                echo "Unexpected argument: $1"
                usage
                exit 1
            fi
            shift
            ;;
    esac
done

if [[ -z "$TRANSCRIPT_FILE" ]]; then
    echo "Transcript file is required."
    usage
    exit 1
fi

if [[ ! -f "$TRANSCRIPT_FILE" ]]; then
    echo "Transcript file not found: $TRANSCRIPT_FILE"
    exit 1
fi

# Ensure helpers exist
if [[ ! -x "./run.sh" ]]; then
    echo "Required helper script not executable: ./run.sh  (run: chmod +x run.sh)"
    exit 1
fi
if [[ ! -x "./venv/bin/python" ]]; then
    echo "Python virtual environment not found or not executable"
    exit 1
fi

transcript_dir="$(dirname "$TRANSCRIPT_FILE")"
transcript_name="$(basename "$TRANSCRIPT_FILE")"
base_name="$(derive_base_name "$transcript_name")"

# Auto-detect language from transcript if not explicitly set
AUTO_LANG="$(detect_transcript_language "$TRANSCRIPT_FILE")"
if [[ $LANG_SET -eq 0 ]]; then
    if [[ -n "$AUTO_LANG" ]]; then
        LANG="$AUTO_LANG"
    else
        LANG="en"
    fi
fi

ANALYSIS_FILE="${transcript_dir}/${base_name}_analysis.json"
PREVIEW_FILE="${transcript_dir}/${base_name}_preview.md"

echo "Transcript: $TRANSCRIPT_FILE"
echo "Title:      ${TITLE:-<none>}"
echo "YouTube:    ${YOUTUBE_ID:-<none>}"
echo "Language:   $LANG"
echo "Insights:   $TOP_INSIGHTS"
echo "Chapters:   $MAX_CHAPTERS"
if [[ $RESUME_MODE -eq 1 ]]; then
    echo "Resume:     enabled (use --force to regenerate)"
fi
echo

# --- Step 1: Unified analysis ---
echo "===== STEP 1: Analyze ====="
if [[ $RESUME_MODE -eq 1 && -f "$ANALYSIS_FILE" ]]; then
    echo "Exists: $ANALYSIS_FILE — skipping (use --force to regenerate)."
else
    analyze_cmd=( "./run.sh" "analyze" "$TRANSCRIPT_FILE"
                  "--lang" "$LANG"
                  "--top" "$TOP_INSIGHTS"
                  "--chapters" "$MAX_CHAPTERS"
                  "--output" "$ANALYSIS_FILE" )
    if [[ -n "$TITLE" ]]; then
        analyze_cmd+=( "--title" "$TITLE" )
    fi
    if [[ -n "$YOUTUBE_ID" ]]; then
        analyze_cmd+=( "--youtube-id" "$YOUTUBE_ID" )
    fi
    "${analyze_cmd[@]}"
fi
if [[ ! -f "$ANALYSIS_FILE" ]]; then
    echo "Analysis file not found: $ANALYSIS_FILE"
    exit 1
fi

# --- Step 2: Render preview ---
echo
echo "===== STEP 2: Render Preview ====="
if [[ $RESUME_MODE -eq 1 && -f "$PREVIEW_FILE" ]]; then
    echo "Exists: $PREVIEW_FILE — skipping (use --force to regenerate)."
else
    render_cmd=("./run.sh" render "$ANALYSIS_FILE" --output "$PREVIEW_FILE")
    if [[ -n "$YOUTUBE_ID" ]]; then
        render_cmd+=("--youtube-id" "$YOUTUBE_ID")
    fi
    "${render_cmd[@]}"
fi
if [[ ! -f "$PREVIEW_FILE" ]]; then
    echo "Preview file not found: $PREVIEW_FILE"
    exit 1
fi

echo
echo "Done! Outputs:"
echo "  Analysis: $ANALYSIS_FILE"
echo "  Preview:  $PREVIEW_FILE"
