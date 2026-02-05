#!/usr/bin/env python3
"""
run_pipeline.py — Orchestrate the full analysis pipeline.

Runs all pipeline stages in order:
  1. Parse sidebar index → conversation_index.json
  2. Parse any conversation dumps → conv_*.json
  3. Categorize (title-based → categorized_index.json)
  4. Categorize (content-based → categories.json, if full text available)
  5. Token analysis → token_summary.json, tfidf_corpus.json, temporal_tokens.json
  6. Build baselines → baselines.json
  7. Anomaly detection → full_anomaly_report.json

Usage:
    python run_pipeline.py                    # Run full pipeline
    python run_pipeline.py --from-step 5      # Resume from step 5
    python run_pipeline.py --only-index       # Only parse & categorize index
    python run_pipeline.py --dry-run          # Show what would run
"""

import argparse
import subprocess
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = PROJECT_ROOT / "scripts"
DATA_DIR = PROJECT_ROOT / "data"
PARSED_DIR = DATA_DIR / "parsed"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
ANALYSIS_DIR = DATA_DIR / "analysis"

PYTHON = sys.executable


def run_step(name: str, cmd: list[str], dry_run: bool = False) -> bool:
    """Run a pipeline step. Returns True on success."""
    print(f"\n{'='*60}")
    print(f"  Step: {name}")
    print(f"  Command: {' '.join(cmd)}")
    print(f"{'='*60}")

    if dry_run:
        print("  [DRY RUN — skipped]")
        return True

    try:
        result = subprocess.run(cmd, cwd=str(PROJECT_ROOT), capture_output=False)
        if result.returncode != 0:
            print(f"\n  ⚠ Step '{name}' exited with code {result.returncode}")
            return False
        return True
    except Exception as e:
        print(f"\n  ✗ Step '{name}' failed: {e}")
        return False


def main():
    parser = argparse.ArgumentParser(description="Run full analysis pipeline")
    parser.add_argument("--from-step", type=int, default=1, help="Start from step N")
    parser.add_argument("--only-index", action="store_true", help="Only parse & categorize index")
    parser.add_argument("--dry-run", action="store_true", help="Show commands without running")
    parser.add_argument("--reference-date", default="2026-02-04", help="Reference date")
    args = parser.parse_args()

    # Ensure directories exist
    for d in [PARSED_DIR, CONVERSATIONS_DIR, ANALYSIS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

    steps = []

    # Step 1: Parse sidebar index
    index_file = DATA_DIR / "conversation-history.md"
    if index_file.exists():
        steps.append((
            "Parse sidebar index",
            [PYTHON, str(SCRIPTS_DIR / "parse_conversations.py"),
             "--index", str(index_file),
             "--reference-date", args.reference_date],
        ))
    else:
        print(f"⚠ No index file at {index_file}")

    # Step 2: Parse conversation dumps (if any exist)
    md_files = list(CONVERSATIONS_DIR.glob("*.md"))
    if md_files:
        steps.append((
            f"Parse {len(md_files)} conversation dumps",
            [PYTHON, str(SCRIPTS_DIR / "parse_conversations.py"),
             "--batch", str(CONVERSATIONS_DIR)],
        ))
    else:
        steps.append((
            "Parse conversation dumps [SKIPPED — no .md files in conversations/]",
            [],
        ))

    # Step 3: Categorize index (title-based)
    steps.append((
        "Categorize conversations (title-based)",
        [PYTHON, str(SCRIPTS_DIR / "categorize.py"),
         "--index", str(PARSED_DIR / "conversation_index.json")],
    ))

    if args.only_index:
        steps = steps[:3]

    # Step 4: Categorize by content (if parsed conversations exist)
    if not args.only_index:
        steps.append((
            "Categorize conversations (content-based)",
            [PYTHON, str(SCRIPTS_DIR / "categorize.py"),
             "--conversations", str(PARSED_DIR)],
        ))

        # Step 5: Token analysis
        steps.append((
            "Token frequency analysis",
            [PYTHON, str(SCRIPTS_DIR / "tokenize_conversations.py"),
             "--corpus", str(PARSED_DIR)],
        ))

        # Step 6: TF-IDF
        steps.append((
            "TF-IDF analysis",
            [PYTHON, str(SCRIPTS_DIR / "tokenize_conversations.py"),
             "--corpus", str(PARSED_DIR), "--tfidf"],
        ))

        # Step 7: Temporal token analysis
        steps.append((
            "Temporal token analysis",
            [PYTHON, str(SCRIPTS_DIR / "tokenize_conversations.py"),
             "--corpus", str(PARSED_DIR), "--temporal"],
        ))

        # Step 8: Build baselines
        steps.append((
            "Build anomaly detection baselines",
            [PYTHON, str(SCRIPTS_DIR / "anomaly_detect.py"),
             "--build-baselines", str(PARSED_DIR),
             "--categories", str(ANALYSIS_DIR / "categories.json")],
        ))

        # Step 9: Full anomaly report
        steps.append((
            "Full anomaly detection report",
            [PYTHON, str(SCRIPTS_DIR / "anomaly_detect.py"),
             "--full-report", str(PARSED_DIR),
             "--categories", str(ANALYSIS_DIR / "categories.json"),
             "--index", str(PARSED_DIR / "conversation_index.json")],
        ))

    # Run steps
    print(f"\n🔬 AI Grok Analysis Pipeline")
    print(f"   Steps to run: {len(steps)} (starting from step {args.from_step})")
    print(f"   Reference date: {args.reference_date}")
    if args.dry_run:
        print("   Mode: DRY RUN")

    success_count = 0
    for i, (name, cmd) in enumerate(steps, 1):
        if i < args.from_step:
            print(f"\n  [Step {i} skipped — starting from step {args.from_step}]")
            continue

        if not cmd:
            print(f"\n  [Step {i}: {name}]")
            continue

        ok = run_step(f"{i}. {name}", cmd, args.dry_run)
        if ok:
            success_count += 1
        else:
            print(f"\n⚠ Pipeline halted at step {i}. Resume with: --from-step {i}")
            break

    print(f"\n{'='*60}")
    print(f"  Pipeline complete: {success_count}/{len(steps)} steps succeeded")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()
