#!/usr/bin/env python3
"""
Unified podcast analysis — single LLM call that produces:
type classification, summary, chapters, and top insights.

Replaces the old multi-step pipeline (outline + detect + summary + highlights).
"""

import sys
import os
import json
import argparse
from utils import (
    load_transcript, get_prompt,
    get_openai_client, get_model_for_task, save_json_file
)


def build_analysis(transcript_text, title=None, lang="en", top_insights=8, max_chapters=10):
    """Run the single-pass podcast analysis."""
    client = get_openai_client()
    if not client:
        return None

    model = get_model_for_task('analysis', default_model="gpt-5.4-mini")

    system_prompt = get_prompt('analysis', 'system')
    structure_template = get_prompt('analysis', 'structure_template')

    if not system_prompt or not structure_template:
        print("Error: Could not load analysis prompts from prompts.yaml")
        return None

    user_prompt = {
        "task": structure_template['task'],
        "output_language": structure_template['output_language'].format(lang=lang),
        "structure": structure_template['structure'],
        "constraints": {
            "max_chapters": structure_template['constraints']['max_chapters'].format(max_chapters=max_chapters),
            "max_top_insights": structure_template['constraints']['max_top_insights'].format(top_insights=top_insights),
            "chapter_duration_guideline": structure_template['constraints']['chapter_duration_guideline'],
            "insight_selection": structure_template['constraints']['insight_selection'],
            "include_unknown_info": structure_template['constraints']['include_unknown_info'],
        },
        "instructions": structure_template['instructions'],
        "transcript": transcript_text,
    }

    if title:
        user_prompt["title"] = title

    request_params = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
        ],
        "response_format": {"type": "json_object"},
    }

    try:
        print(f"Analyzing podcast with {model}...")
        response = client.chat.completions.create(**request_params)
        content = response.choices[0].message.content.strip()
        result = json.loads(content)

        result["model_used"] = model
        result["tokens_used"] = {
            "prompt": response.usage.prompt_tokens,
            "completion": response.usage.completion_tokens,
            "total": response.usage.total_tokens,
        }
        if title:
            result["title"] = title
        if "language" not in result or not result["language"]:
            result["language"] = lang

        return result
    except json.JSONDecodeError as exc:
        print(f"Error parsing JSON response: {exc}")
        return None
    except Exception as exc:
        print(f"Error during analysis: {exc}")
        return None


def main():
    parser = argparse.ArgumentParser(
        description="Unified Podcast Analyzer — type, summary, chapters & insights in one pass",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("transcript_file", help="Path to transcript file (.txt or .json)")
    parser.add_argument("--title", help="Episode title")
    parser.add_argument("--lang", default="en", help="Output language ISO code (default: en)")
    parser.add_argument("--top", type=int, default=8, help="Max top insights (default: 8)")
    parser.add_argument("--chapters", type=int, default=10, help="Max chapters (default: 10)")
    parser.add_argument("--output", help="Custom output path (default: *_analysis.json)")

    args = parser.parse_args()

    if not os.path.exists(args.transcript_file):
        print(f"Transcript file not found: {args.transcript_file}")
        sys.exit(1)
    if args.top < 1:
        print("--top must be at least 1")
        sys.exit(1)
    if args.chapters < 1:
        print("--chapters must be at least 1")
        sys.exit(1)

    transcript_text = load_transcript(args.transcript_file)
    if not transcript_text:
        sys.exit(1)

    result = build_analysis(
        transcript_text,
        title=args.title,
        lang=args.lang,
        top_insights=args.top,
        max_chapters=args.chapters,
    )
    if not result:
        sys.exit(1)

    output_file = args.output
    if not output_file:
        from utils import derive_output_path
        output_file = derive_output_path(args.transcript_file, '_analysis')

    if save_json_file(result, output_file):
        tokens = result.get("tokens_used", {})
        print(f"Analysis complete — {tokens.get('total', '?')} tokens used")
        print(f"  Type: {result.get('type_primary', '?')} / {result.get('type_secondary', '')}")
        print(f"  Chapters: {len(result.get('chapters', []))}")
        print(f"  Insights: {len(result.get('top_insights', []))}")
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
