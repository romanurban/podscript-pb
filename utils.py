#!/usr/bin/env python3
"""
Shared utility functions for Podscript pipeline.
"""

import json
import yaml
import os
from pathlib import Path
from dotenv import load_dotenv


def load_transcript(file_path):
    """Load transcript from TXT or JSON file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            if file_path.endswith('.json'):
                data = json.load(f)
                if 'segments' in data:
                    transcript_lines = []
                    for segment in data['segments']:
                        start_time = format_timestamp(segment['start'])
                        text = segment['text'].strip()
                        transcript_lines.append(f"[{start_time}] {text}")
                    return '\n'.join(transcript_lines)
                else:
                    return str(data)
            else:
                return f.read()
    except Exception as e:
        print(f"Error loading transcript: {e}")
        return None


def format_timestamp(seconds):
    """Format seconds to HH:MM:SS or MM:SS."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    else:
        return f"{minutes:02d}:{secs:02d}"


def derive_output_path(input_file, suffix, extension='.json'):
    """Derive output file path from input file."""
    input_path = Path(input_file)
    name = input_path.name
    for transcript_suffix in ['_transcription.txt', '_transcription.json']:
        if name.endswith(transcript_suffix):
            base = name[:-len(transcript_suffix)]
            return str(input_path.parent / f"{base}{suffix}{extension}")
    return str(input_path.parent / f"{input_path.stem}{suffix}{extension}")


# Cache for loaded prompts
_PROMPTS_CACHE = None


def load_prompts(prompts_file='prompts.yaml'):
    """Load prompts from YAML file."""
    global _PROMPTS_CACHE
    if _PROMPTS_CACHE is not None:
        return _PROMPTS_CACHE
    try:
        prompts_path = Path(__file__).parent / prompts_file
        with open(prompts_path, 'r', encoding='utf-8') as f:
            _PROMPTS_CACHE = yaml.safe_load(f)
            return _PROMPTS_CACHE
    except Exception as e:
        print(f"Error loading prompts from {prompts_file}: {e}")
        return None


def get_prompt(category, subcategory=None):
    """Get a specific prompt from the prompts file."""
    prompts = load_prompts()
    if not prompts:
        return None
    if subcategory:
        return prompts.get(category, {}).get(subcategory)
    return prompts.get(category)


def get_openai_client():
    """Initialize and return OpenAI client."""
    load_dotenv()
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        print("Error: OPENAI_API_KEY not found. Create a .env file with your API key.")
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=api_key, organization=os.getenv("OPENAI_ORG_ID"))
    except Exception as e:
        print(f"Error initializing OpenAI client: {e}")
        return None


def get_model_for_task(task_name, default_model="gpt-5-mini"):
    """Get model for a task. Checks PODSCRIPT_ANALYSIS_MODEL, then OPENAI_MODEL, then default."""
    task_env_vars = {
        'analysis': 'PODSCRIPT_ANALYSIS_MODEL',
    }
    task_var = task_env_vars.get(task_name)
    if task_var:
        task_model = os.getenv(task_var)
        if task_model:
            return task_model
    general = os.getenv("OPENAI_MODEL")
    if general:
        return general
    return default_model


def format_time_srt(seconds):
    """Convert seconds to SRT time format (HH:MM:SS,mmm)."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    milliseconds = int((seconds % 1) * 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{milliseconds:03d}"


def format_time_simple(seconds):
    """Convert seconds to H:MM:SS or MM:SS format."""
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    if hours > 0:
        return f"{hours}:{minutes:02d}:{secs:02d}"
    return f"{minutes:02d}:{secs:02d}"


def save_json_file(data, output_path, success_message=None):
    """Save data to JSON file."""
    try:
        os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(success_message or f"Saved to: {output_path}")
        return True
    except Exception as exc:
        print(f"Error saving JSON to '{output_path}': {exc}")
        return False
