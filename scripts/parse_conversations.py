#!/usr/bin/env python3
"""
parse_conversations.py — Parse Grok conversation markdown dumps into structured JSON.

Handles two input formats:
  1. Sidebar title listing (conversation-history.md) — metadata only
  2. Full conversation dumps (one .md per conversation) — full text extraction

Output: data/parsed/conversations.json  (or individual .json per conversation)

Usage:
    # Parse sidebar title listing into metadata index
    python parse_conversations.py --index data/conversation-history.md

    # Parse a single full conversation dump
    python parse_conversations.py --conversation data/conversations/some-chat.md

    # Parse all conversation dumps in a directory
    python parse_conversations.py --batch data/conversations/

    # Re-index everything (rebuild master index from parsed JSONs)
    python parse_conversations.py --reindex
"""

import argparse
import json
import re
import sys
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

# Project root
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PARSED_DIR = DATA_DIR / "parsed"
CONVERSATIONS_DIR = DATA_DIR / "conversations"
INDEX_FILE = PARSED_DIR / "conversation_index.json"


def slugify(title: str) -> str:
    """Convert a conversation title to a filename-safe slug."""
    slug = re.sub(r"[^\w\s-]", "", title.lower())
    slug = re.sub(r"[\s_]+", "-", slug).strip("-")
    return slug[:80]


def parse_date(date_str: str) -> Optional[str]:
    """Parse various date formats found in conversation history into ISO format."""
    date_str = date_str.strip()

    # "3 days ago", "6 days ago" — relative dates
    m = re.match(r"(\d+)\s+days?\s+ago", date_str)
    if m:
        # Can't resolve without a reference date; return None, caller handles
        return None

    # "Jan 26", "Dec 11", "Nov 22", etc.
    month_day = re.match(
        r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})", date_str
    )
    if month_day:
        month_str, day_str = month_day.groups()
        # Infer year from section context (caller should pass)
        return f"{month_str} {day_str}"

    # "Jul 19" already covered above
    return date_str if date_str else None


def infer_year_month(section_header: str) -> tuple[Optional[int], Optional[int]]:
    """Extract year/month from section headers like '### December 2025'."""
    months = {
        "january": 1, "february": 2, "march": 3, "april": 4,
        "may": 5, "june": 6, "july": 7, "august": 8,
        "september": 9, "october": 10, "november": 11, "december": 12,
    }
    header = section_header.lower().strip("# \n")

    # "December 2025"
    for name, num in months.items():
        if name in header:
            year_match = re.search(r"(\d{4})", header)
            year = int(year_match.group(1)) if year_match else None
            return year, num

    # "This Year (Jan 2026)"
    year_match = re.search(r"(\d{4})", header)
    if year_match:
        return int(year_match.group(1)), None

    # "Last 7 Days"
    if "last" in header and "day" in header:
        return None, None

    return None, None


def parse_sidebar_index(filepath: Path, reference_date: Optional[str] = None) -> list[dict]:
    """
    Parse the sidebar conversation-history.md file into structured metadata.

    Returns list of conversation metadata dicts:
    {
        "id": str (sha256 of title),
        "title": str,
        "slug": str,
        "date_raw": str,
        "date_iso": str or null,
        "section": str,
        "section_year": int or null,
        "section_month": int or null,
        "category_hint": str (from title-level pattern notes),
        "has_full_text": bool,
        "duplicate_count": int,
    }
    """
    ref_date = datetime.fromisoformat(reference_date) if reference_date else datetime.now()

    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    conversations = []
    current_section = "Unknown"
    section_year = None
    section_month = None
    in_pattern_notes = False

    month_abbrevs = {
        "Jan": 1, "Feb": 2, "Mar": 3, "Apr": 4,
        "May": 5, "Jun": 6, "Jul": 7, "Aug": 8,
        "Sep": 9, "Oct": 10, "Nov": 11, "Dec": 12,
    }

    for line in lines:
        line = line.rstrip()

        # Section headers
        if line.startswith("###"):
            if "Pattern Notes" in line or "Void" in line or "Technical" in line or "Creative" in line or "NOTE" in line:
                in_pattern_notes = True
                continue
            in_pattern_notes = False
            current_section = line.lstrip("# ").strip()
            section_year, section_month = infer_year_month(line)
            continue

        if in_pattern_notes:
            continue

        # Skip non-list lines
        if not line.startswith("- "):
            continue

        # Parse conversation entry: "- Title (Date)" or "- Title (Date) ×N"
        entry = line[2:].strip()

        # Check for duplicate marker
        dup_match = re.search(r"×(\d+)\s*$", entry)
        dup_count = int(dup_match.group(1)) if dup_match else 1
        if dup_match:
            entry = entry[: dup_match.start()].strip()

        # Extract date from parenthetical at end
        date_match = re.search(r"\(([^)]+)\)\s*$", entry)
        date_raw = ""
        date_iso = None

        if date_match:
            date_raw = date_match.group(1).strip()
            title = entry[: date_match.start()].strip()

            # Try to build ISO date
            # "3 days ago"
            days_ago = re.match(r"(\d+)\s+days?\s+ago", date_raw)
            if days_ago:
                from datetime import timedelta
                d = ref_date - timedelta(days=int(days_ago.group(1)))
                date_iso = d.strftime("%Y-%m-%d")
            else:
                # "Jan 26" with year from section or inferred
                abbrev_match = re.match(
                    r"(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s+(\d{1,2})",
                    date_raw,
                )
                if abbrev_match:
                    mon = month_abbrevs[abbrev_match.group(1)]
                    day = int(abbrev_match.group(2))
                    year = section_year or ref_date.year
                    # If section says "Older (Jan 2026 — early)" parse differently
                    if section_year:
                        year = section_year
                    elif section_month and mon != section_month:
                        # Mismatch, guess year
                        year = ref_date.year
                    try:
                        date_iso = f"{year}-{mon:02d}-{day:02d}"
                    except Exception:
                        date_iso = None
        else:
            title = entry.strip()

        if not title:
            continue

        conv_id = hashlib.sha256(title.encode()).hexdigest()[:12]

        conversations.append({
            "id": conv_id,
            "title": title,
            "slug": slugify(title),
            "date_raw": date_raw,
            "date_iso": date_iso,
            "section": current_section,
            "section_year": section_year,
            "section_month": section_month,
            "category_hint": None,  # filled by categorize.py
            "has_full_text": False,
            "duplicate_count": dup_count,
        })

    return conversations


def parse_conversation_dump(filepath: Path) -> dict:
    """
    Parse a full conversation markdown dump into structured JSON.

    Expected format (flexible — handles Grok's export and manual copy-paste):

    # Title
    ## User
    message text...

    ## Grok
    response text...

    ## User
    ...

    Returns:
    {
        "id": str,
        "title": str,
        "slug": str,
        "source_file": str,
        "turns": [
            {"role": "user"|"grok"|"system", "content": str, "index": int}
        ],
        "metadata": {
            "total_turns": int,
            "user_turns": int,
            "grok_turns": int,
            "total_words_user": int,
            "total_words_grok": int,
            "avg_grok_response_length": float,
        }
    }
    """
    text = filepath.read_text(encoding="utf-8")
    lines = text.split("\n")

    title = filepath.stem.replace("-", " ").replace("_", " ").title()
    turns = []
    current_role = None
    current_content = []

    # Role detection patterns
    role_patterns = [
        (r"^#{1,3}\s*(User|Human|Me)\s*$", "user"),
        (r"^#{1,3}\s*(Grok|Assistant|AI|Bot)\s*$", "grok"),
        (r"^#{1,3}\s*(System)\s*$", "system"),
        # Alternate formats: "**User:**", "> User:", etc.
        (r"^\*\*(User|Human|Me)\*\*:?\s*$", "user"),
        (r"^\*\*(Grok|Assistant|AI|Bot)\*\*:?\s*$", "grok"),
        (r"^>\s*(User|Human|Me):?\s*$", "user"),
        (r"^>\s*(Grok|Assistant|AI|Bot):?\s*$", "grok"),
    ]

    for line in lines:
        stripped = line.strip()

        # Check for title (H1)
        if stripped.startswith("# ") and not stripped.startswith("## "):
            candidate_title = stripped[2:].strip()
            if candidate_title:
                title = candidate_title
            continue

        # Check for role marker
        role_found = None
        for pattern, role in role_patterns:
            if re.match(pattern, stripped, re.IGNORECASE):
                role_found = role
                break

        if role_found:
            # Save previous turn
            if current_role and current_content:
                content = "\n".join(current_content).strip()
                if content:
                    turns.append({
                        "role": current_role,
                        "content": content,
                        "index": len(turns),
                    })
            current_role = role_found
            current_content = []
        else:
            current_content.append(line)

    # Save last turn
    if current_role and current_content:
        content = "\n".join(current_content).strip()
        if content:
            turns.append({
                "role": current_role,
                "content": content,
                "index": len(turns),
            })

    # If no structured turns found, treat entire content as single grok response
    if not turns:
        content = text.strip()
        if content:
            turns.append({"role": "unknown", "content": content, "index": 0})

    # Compute metadata
    user_turns = [t for t in turns if t["role"] == "user"]
    grok_turns = [t for t in turns if t["role"] == "grok"]

    user_words = sum(len(t["content"].split()) for t in user_turns)
    grok_words = sum(len(t["content"].split()) for t in grok_turns)

    conv_id = hashlib.sha256(title.encode()).hexdigest()[:12]

    return {
        "id": conv_id,
        "title": title,
        "slug": slugify(title),
        "source_file": str(filepath.name),
        "turns": turns,
        "metadata": {
            "total_turns": len(turns),
            "user_turns": len(user_turns),
            "grok_turns": len(grok_turns),
            "total_words_user": user_words,
            "total_words_grok": grok_words,
            "avg_grok_response_length": (
                round(grok_words / len(grok_turns), 1) if grok_turns else 0
            ),
        },
    }


def build_master_index(conversations_meta: list[dict]) -> dict:
    """Build the master index with summary statistics."""
    dates = [c["date_iso"] for c in conversations_meta if c.get("date_iso")]
    dates.sort()

    return {
        "generated_at": datetime.now().isoformat(),
        "total_conversations": len(conversations_meta),
        "date_range": {
            "earliest": dates[0] if dates else None,
            "latest": dates[-1] if dates else None,
        },
        "by_section": _group_count(conversations_meta, "section"),
        "with_full_text": sum(1 for c in conversations_meta if c.get("has_full_text")),
        "conversations": conversations_meta,
    }


def _group_count(items: list[dict], key: str) -> dict[str, int]:
    """Count items by a key."""
    counts: dict[str, int] = {}
    for item in items:
        val = item.get(key, "Unknown")
        counts[val] = counts.get(val, 0) + 1
    return counts


def reindex(parsed_dir: Path) -> dict:
    """Rebuild master index from all parsed JSON files."""
    conversations = []
    for json_file in sorted(parsed_dir.glob("conv_*.json")):
        data = json.loads(json_file.read_text(encoding="utf-8"))
        meta = {
            "id": data["id"],
            "title": data["title"],
            "slug": data["slug"],
            "source_file": data.get("source_file", ""),
            "has_full_text": bool(data.get("turns")),
            "metadata": data.get("metadata", {}),
        }
        conversations.append(meta)
    return build_master_index(conversations)


def main():
    parser = argparse.ArgumentParser(
        description="Parse Grok conversation dumps into structured JSON"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument(
        "--index", type=Path,
        help="Parse sidebar title listing (conversation-history.md)"
    )
    group.add_argument(
        "--conversation", type=Path,
        help="Parse a single full conversation dump (.md)"
    )
    group.add_argument(
        "--batch", type=Path,
        help="Parse all .md files in a directory"
    )
    group.add_argument(
        "--reindex", action="store_true",
        help="Rebuild master index from parsed JSONs"
    )
    parser.add_argument(
        "--reference-date", type=str, default="2026-02-04",
        help="Reference date for resolving relative dates (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--output", "-o", type=Path,
        help="Output file (default: auto-generated in data/parsed/)"
    )

    args = parser.parse_args()

    # Ensure output dirs exist
    PARSED_DIR.mkdir(parents=True, exist_ok=True)
    CONVERSATIONS_DIR.mkdir(parents=True, exist_ok=True)

    if args.index:
        conversations = parse_sidebar_index(args.index, args.reference_date)
        index = build_master_index(conversations)
        out = args.output or INDEX_FILE
        out.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Parsed {len(conversations)} conversation titles → {out}")
        print(f"  Date range: {index['date_range']['earliest']} — {index['date_range']['latest']}")
        print(f"  Sections: {index['by_section']}")

    elif args.conversation:
        result = parse_conversation_dump(args.conversation)
        out = args.output or (PARSED_DIR / f"conv_{result['slug']}.json")
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        m = result["metadata"]
        print(f"✓ Parsed '{result['title']}' → {out}")
        print(f"  Turns: {m['total_turns']} (user: {m['user_turns']}, grok: {m['grok_turns']})")
        print(f"  Words: user={m['total_words_user']}, grok={m['total_words_grok']}")

    elif args.batch:
        md_files = sorted(args.batch.glob("*.md"))
        if not md_files:
            print(f"No .md files found in {args.batch}")
            sys.exit(1)
        for md_file in md_files:
            result = parse_conversation_dump(md_file)
            out = PARSED_DIR / f"conv_{result['slug']}.json"
            out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            m = result["metadata"]
            print(f"  ✓ {result['title']} ({m['total_turns']} turns, {m['total_words_grok']} grok words)")
        print(f"\n✓ Batch parsed {len(md_files)} conversations → {PARSED_DIR}")

    elif args.reindex:
        index = reindex(PARSED_DIR)
        out = args.output or INDEX_FILE
        out.write_text(json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Reindexed {index['total_conversations']} conversations → {out}")


if __name__ == "__main__":
    main()
