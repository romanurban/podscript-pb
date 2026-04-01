# Podscript

Podcast transcription and analysis pipeline powered by OpenAI's Whisper and GPT models. Focused on extracting the most interesting ideas from podcasts.

## Setup

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

Create a `.env` file (see `.env.example`):
```bash
OPENAI_API_KEY=your_api_key_here
OPENAI_ORG_ID=your_org_id  # Optional
```

## Quick Start

### 1. Transcribe from YouTube
```bash
./run_youtube_transcriber.sh <youtube-url>
```
- Auto-updates `yt-dlp`, auto-detects language
- Outputs: `output/<video>_transcription.txt`

### 2. Run Full Analysis
```bash
./run_podcast_full_analysis.sh output/<video>_transcription.txt --title "Episode Title"
```

Two-step pipeline:
1. **Analyze** — single LLM call producing type classification, summary, chapters, and top insights
2. **Render** — pure Python, formats the analysis JSON into a readable markdown preview

Options:
- `--lang <code>` — output language (default: auto-detected or `en`)
- `--top-insights N` — number of top insights to extract (default: 8)
- `--max-chapters N` — maximum chapters (default: 10)
- `--force` — regenerate all outputs (default: resume mode skips existing files)
- `--title TITLE` — episode title
- `--youtube-id ID` — YouTube video ID (adds embed player and clickable chapter timestamps)

## Individual Commands

```bash
./run.sh <command> [arguments...]
```

### analyze
```bash
./run.sh analyze transcript.txt [--lang en] [--top 8] [--chapters 10] [--title "Title"] [--youtube-id ID]
```
Single-pass analysis: type, summary, chapters, key themes, and top insights. Outputs `*_analysis.json`. With `--youtube-id` stores the ID for use during render.

### render
```bash
./run.sh render analysis.json [--output preview.md] [--youtube-id ID]
```
Renders analysis JSON into a clean markdown preview. No LLM call. Outputs `*_preview.md`. With `--youtube-id` adds YouTube embed and clickable chapter timestamps.

## Output Files

For input `output/episode_transcription.txt`, the pipeline generates:
- `output/episode_analysis.json` — structured analysis (type, summary, chapters, insights, themes)
- `output/episode_preview.md` — readable markdown preview

## Architecture

### Analysis Pipeline
- `analyze_podcast.py` — unified analysis (single LLM call)
- `render_preview.py` — markdown preview renderer (pure Python)

### Transcription
- `youtube_podcast_transcriber.py` — downloads and transcribes YouTube videos
- `transcribe_audio.py` / `transcribe_chunks.py` — Whisper transcription
- `chunk_audio.py` — audio splitting with silence detection
- `extract_youtube_audio.py` — YouTube audio download via yt-dlp

### Shared
- `utils.py` — common functions (transcript loading, prompt management, OpenAI client)
- `prompts.yaml` — AI prompt configuration

### Wrappers
- `run.sh` — unified command runner
- `run_youtube_transcriber.sh` — YouTube transcription wrapper
- `run_podcast_full_analysis.sh` — full pipeline orchestrator

## Configuration

### Model Selection
```bash
PODSCRIPT_ANALYSIS_MODEL=gpt-5-mini  # Override analysis model (default: gpt-5-mini)
OPENAI_MODEL=gpt-5                   # General fallback
```

### Prompt Customization
Edit the `analysis` section in `prompts.yaml` to adjust the system prompt, output structure, or insight selection criteria.

### Language Support
Language is auto-detected from transcript metadata or specified with `--lang`. Supported: en, ru, es, fr, de, it, pt, uk, pl, zh, ja, ko.

## Troubleshooting

```bash
# Recreate venv
rm -rf venv && python3 -m venv venv
source venv/bin/activate && pip install -r requirements.txt

# Check API key
grep OPENAI_API_KEY .env

# Fix permissions
chmod +x run.sh run_youtube_transcriber.sh run_podcast_full_analysis.sh
```
