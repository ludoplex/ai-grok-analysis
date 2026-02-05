#!/usr/bin/env python3
"""
categorize.py — Auto-categorize Grok conversations as technical/creative/mixed.

Categorization is keyword/heuristic-based (no ML dependency) with optional
TF-IDF refinement when sklearn is available.

Categories:
  - technical: programming, hardware, networking, security, devops, math
  - creative: art, image editing, storytelling, game design, music
  - business: SOP, contracts, proposals, legal, marketing
  - gaming: game rules, strategy, esports, card games
  - research: analysis, comparison, investigation, methodology
  - personal: greetings, personal questions, casual chat
  - mixed: significant overlap between categories

Usage:
    # Categorize from title only (sidebar index)
    python categorize.py --index data/parsed/conversation_index.json

    # Categorize from full conversation text
    python categorize.py --conversations data/parsed/

    # Categorize a single conversation
    python categorize.py --file data/parsed/conv_something.json

    # Output enriched index with categories
    python categorize.py --index data/parsed/conversation_index.json -o data/parsed/categorized_index.json
"""

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PARSED_DIR = DATA_DIR / "parsed"
OUTPUT_DIR = DATA_DIR / "analysis"

# ── Category keyword dictionaries ──────────────────────────────────────────

CATEGORY_KEYWORDS = {
    "technical": {
        # Programming
        "python", "javascript", "typescript", "rust", "c++", "masm", "masm64",
        "assembly", "code", "coding", "programming", "script", "scripting",
        "compiler", "binary", "rewriting", "algorithm", "api", "sdk",
        "fastapi", "node", "npm", "git", "github", "svn", "cli",
        "powershell", "bash", "terminal", "debug", "debugging", "bug",
        "function", "class", "module", "library", "framework", "stack",
        "frontend", "backend", "fullstack", "database", "sql", "sqlite",
        "directx", "opengl", "vulkan", "shader", "rendering",
        "xcode", "ios", "android", "app", "development",
        # Hardware/Networking
        "server", "gpu", "nvidia", "cpu", "hardware", "network", "sonic",
        "ace", "switch", "router", "protocol", "tcp", "udp", "p2p",
        "latency", "bandwidth", "cdn", "dns", "ssl", "tls", "mitm",
        # DevOps
        "docker", "kubernetes", "ci/cd", "pipeline", "automation",
        "codespaces", "actions", "deployment", "kiosk",
        # Security
        "security", "vulnerability", "exploit", "bug bounty", "attack",
        "scanning", "filtering", "encryption",
        # Data/Math
        "algorithm", "data", "analysis", "statistics", "ballistics",
        "calculator", "equation", "permutation", "visualization",
        "branchless", "simd", "parallel", "multi-core",
    },
    "creative": {
        "image", "editing", "art", "design", "style", "collage",
        "crystal", "gems", "transformation", "kavinsky", "weeknd",
        "kanye", "glasses", "turtle neck", "knight", "dragon",
        "harley", "quinn", "halloween", "ad", "retro",
        "video", "generation", "caption", "aesthetic",
        "waifu", "kawaii", "anime",
        "music", "audio", "song", "lyrics",
        "story", "creative", "writing", "narrative",
    },
    "business": {
        "sop", "store", "computer store", "business", "contract",
        "proposal", "partnership", "kyndryl", "alliance",
        "budget", "cost", "pricing", "resale", "ebay",
        "training", "certification", "pearson", "vue",
        "marketing", "engagement", "brand", "community",
        "legal", "lawyer", "subpoena", "discovery",
        "invoice", "payment", "subscription",
        "mighty house", "wheatland",
    },
    "gaming": {
        "game", "gaming", "chess", "tournament", "rules",
        "yu-gi-oh", "yugioh", "card game", "ccg", "tcg",
        "trap", "archetype", "xyz", "paleozoic",
        "fighting game", "2.5d", "frame data", "oni",
        "ff6", "snes", "combat", "rpg",
        "rock paper scissors", "multiplayer",
        "stellar clash", "starpiece", "vs system",
        "marvel", "tokon", "gundom",
        "quest", "meta quest", "vr", "mod",
        "diablo", "battle.net",
        "genesys", "dominion", "variant",
    },
    "research": {
        "analysis", "comparison", "vs", "investigation",
        "methodology", "review", "study", "research",
        "ethics", "framework", "constitution",
        "features", "limitations", "functionality",
        "health", "benefits", "red bull", "coffee",
        "history", "legacy", "evolution",
        "trends", "future", "prediction",
        "ethnicity", "demographics",
        "webcam", "live data", "resources",
        "venues", "list", "guide",
    },
    "personal": {
        "greeting", "hello", "hi", "hey", "name",
        "acknowledgment", "introduction", "inquiry",
        "simple", "resuming", "previous", "discussion",
        "fixing", "settings", "under-18",
        "things to do", "santa fe",
        "wrestling", "coach", "anderson",
        "funeral", "cremated", "remains", "flights",
        "tanahashi", "retirement", "joshi",
    },
}

# Grok-specific topic markers
GROK_META_KEYWORDS = {
    "grok", "xai", "grok's", "companion", "companions",
    "agentic", "search", "share link", "conversation link",
    "ai privacy", "ai interface", "ai purpose",
}


def normalize_text(text: str) -> str:
    """Lowercase and normalize for keyword matching."""
    return text.lower().strip()


def categorize_by_title(title: str) -> dict:
    """
    Categorize a conversation based on its title alone.
    Returns category scores and final classification.
    """
    title_lower = normalize_text(title)
    title_words = set(re.findall(r"[a-z][a-z'-]+", title_lower))

    scores: dict[str, float] = defaultdict(float)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            kw_lower = keyword.lower()
            # Exact word match or substring in title
            if kw_lower in title_words or kw_lower in title_lower:
                # Multi-word keywords get bonus
                word_count = len(kw_lower.split())
                scores[category] += 1.0 * word_count

    # Check for Grok meta-discussions
    is_grok_meta = any(kw in title_lower for kw in GROK_META_KEYWORDS)

    # Determine primary category
    if not scores:
        primary = "uncategorized"
        confidence = 0.0
    else:
        sorted_cats = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_cats[0][0]
        total_score = sum(scores.values())
        confidence = sorted_cats[0][1] / total_score if total_score > 0 else 0

        # Check for mixed: if top two are close
        if len(sorted_cats) >= 2:
            ratio = sorted_cats[1][1] / sorted_cats[0][1] if sorted_cats[0][1] > 0 else 0
            if ratio > 0.6:
                primary = "mixed"
                confidence = 1 - ratio  # lower confidence for mixed

    return {
        "primary_category": primary,
        "confidence": round(confidence, 3),
        "scores": dict(scores),
        "is_grok_meta": is_grok_meta,
    }


def categorize_by_content(conv_data: dict) -> dict:
    """
    Categorize based on full conversation content.
    Uses both title and content analysis.
    """
    title = conv_data.get("title", "")
    title_result = categorize_by_title(title)

    # Analyze conversation content
    grok_text = " ".join(
        turn["content"]
        for turn in conv_data.get("turns", [])
        if turn["role"] == "grok"
    )
    user_text = " ".join(
        turn["content"]
        for turn in conv_data.get("turns", [])
        if turn["role"] == "user"
    )

    all_text = f"{title} {user_text} {grok_text}"
    text_lower = normalize_text(all_text)
    text_words = set(re.findall(r"[a-z][a-z'-]+", text_lower))

    content_scores: dict[str, float] = defaultdict(float)

    for category, keywords in CATEGORY_KEYWORDS.items():
        for keyword in keywords:
            kw_lower = keyword.lower()
            if kw_lower in text_words:
                # Count occurrences for weighting
                count = text_lower.count(kw_lower)
                content_scores[category] += min(count, 10)  # cap at 10 per keyword

    # Merge title and content scores (title 30%, content 70%)
    merged_scores: dict[str, float] = defaultdict(float)
    for cat in set(list(title_result["scores"].keys()) + list(content_scores.keys())):
        t_score = title_result["scores"].get(cat, 0)
        c_score = content_scores.get(cat, 0)
        merged_scores[cat] = t_score * 0.3 + c_score * 0.7

    # Determine category
    if not merged_scores:
        primary = "uncategorized"
        confidence = 0.0
        secondary = None
    else:
        sorted_cats = sorted(merged_scores.items(), key=lambda x: x[1], reverse=True)
        primary = sorted_cats[0][0]
        total = sum(merged_scores.values())
        confidence = sorted_cats[0][1] / total if total > 0 else 0

        secondary = sorted_cats[1][0] if len(sorted_cats) >= 2 else None

        if len(sorted_cats) >= 2:
            ratio = sorted_cats[1][1] / sorted_cats[0][1] if sorted_cats[0][1] > 0 else 0
            if ratio > 0.6:
                primary = "mixed"
                confidence = 1 - ratio

    # Code density heuristic
    code_blocks = len(re.findall(r"```", grok_text))
    inline_code = len(re.findall(r"`[^`]+`", grok_text))
    total_words = len(grok_text.split())
    code_density = (code_blocks * 50 + inline_code * 5) / max(total_words, 1)

    # If high code density, boost technical score
    if code_density > 0.1 and primary != "technical":
        merged_scores["technical"] += code_density * 100
        sorted_cats = sorted(merged_scores.items(), key=lambda x: x[1], reverse=True)
        if sorted_cats[0][0] == "technical":
            primary = "technical"
            confidence = sorted_cats[0][1] / sum(merged_scores.values())

    return {
        "primary_category": primary,
        "secondary_category": secondary,
        "confidence": round(confidence, 3),
        "scores": dict(merged_scores),
        "is_grok_meta": title_result["is_grok_meta"],
        "code_density": round(code_density, 4),
        "analysis_method": "content",
    }


def categorize_index(index_data: dict) -> dict:
    """
    Categorize all conversations in the index by title.
    Returns enriched index + category distribution.
    """
    category_counts: Counter = Counter()

    for conv in index_data.get("conversations", []):
        result = categorize_by_title(conv["title"])
        conv["category"] = result["primary_category"]
        conv["category_confidence"] = result["confidence"]
        conv["category_scores"] = result["scores"]
        conv["is_grok_meta"] = result["is_grok_meta"]
        category_counts[result["primary_category"]] += 1

    index_data["category_distribution"] = dict(category_counts.most_common())
    index_data["categorization_method"] = "title-only"

    return index_data


def categorize_corpus(parsed_dir: Path) -> list[dict]:
    """Categorize all parsed conversation JSONs by content."""
    results = []
    json_files = sorted(parsed_dir.glob("conv_*.json"))

    for f in json_files:
        conv = json.loads(f.read_text(encoding="utf-8"))
        cat = categorize_by_content(conv)
        cat["id"] = conv["id"]
        cat["title"] = conv["title"]
        cat["slug"] = conv.get("slug", "")
        results.append(cat)

    return results


def print_distribution(categorized: list[dict]):
    """Pretty-print category distribution."""
    counts: Counter = Counter()
    for item in categorized:
        counts[item.get("primary_category", item.get("category", "unknown"))] += 1

    total = sum(counts.values())
    print(f"\n{'Category':<20} {'Count':>5} {'%':>6}")
    print("-" * 33)
    for cat, count in counts.most_common():
        pct = count / total * 100
        bar = "█" * int(pct / 3)
        print(f"{cat:<20} {count:>5} {pct:>5.1f}% {bar}")
    print("-" * 33)
    print(f"{'Total':<20} {total:>5}")


def main():
    parser = argparse.ArgumentParser(
        description="Auto-categorize Grok conversations"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--index", type=Path, help="Conversation index JSON (title-based)")
    group.add_argument("--conversations", type=Path, help="Directory of parsed conv JSONs")
    group.add_argument("--file", type=Path, help="Single parsed conversation JSON")

    parser.add_argument("-o", "--output", type=Path, help="Output file")
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.index:
        index_data = json.loads(args.index.read_text(encoding="utf-8"))
        result = categorize_index(index_data)

        out = args.output or (PARSED_DIR / "categorized_index.json")
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Categorized {len(result['conversations'])} conversations → {out}")
        print_distribution(result["conversations"])

    elif args.conversations:
        results = categorize_corpus(args.conversations)
        out = args.output or (OUTPUT_DIR / "categories.json")
        out.write_text(json.dumps(results, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Categorized {len(results)} conversations → {out}")
        print_distribution(results)

    elif args.file:
        conv = json.loads(args.file.read_text(encoding="utf-8"))
        result = categorize_by_content(conv)
        result["title"] = conv["title"]
        print(f"Title: {conv['title']}")
        print(f"Category: {result['primary_category']} ({result['confidence']:.0%} confidence)")
        print(f"Secondary: {result.get('secondary_category', 'none')}")
        print(f"Code density: {result['code_density']:.2%}")
        print(f"Grok meta: {result['is_grok_meta']}")
        if result["scores"]:
            print("Scores:")
            for cat, score in sorted(result["scores"].items(), key=lambda x: -x[1]):
                print(f"  {cat}: {score:.1f}")

        if args.output:
            args.output.write_text(
                json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8"
            )


if __name__ == "__main__":
    main()
