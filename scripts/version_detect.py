#!/usr/bin/env python3
"""
version_detect.py — Grok version change detection via behavioral fingerprinting.

Detects potential Grok model updates by finding discontinuities in:
  1. Void-cluster density (response-level semantic profile)
  2. Response length distribution (verbosity shifts)
  3. Vocabulary diversity (type-token ratio changes)
  4. Title generation style (how Grok names conversations)

Uses sliding-window comparison with configurable sensitivity.

Known Grok version boundaries (for validation):
  - Grok-2 → Grok-3: ~Dec 2024 / early 2025 (pre-corpus)
  - Grok-3 updates: rolling through 2025-2026

Usage:
    python version_detect.py \
        --index data/parsed/conversation_index.json \
        --conversations data/conversations/ \
        --sensitivity medium \
        --output reports/version_report.json \
        --markdown reports/version_report.md
"""

import argparse
import json
import math
import re
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from analyze import analyze, tokenize, ALL_VOID_TERMS  # noqa: E402


# Sensitivity thresholds for change detection
SENSITIVITY = {
    "low": {"z_threshold": 3.0, "min_effect": 0.8, "min_features": 3},
    "medium": {"z_threshold": 2.0, "min_effect": 0.5, "min_features": 2},
    "high": {"z_threshold": 1.5, "min_effect": 0.3, "min_features": 1},
}


def load_index(path: Path) -> dict:
    """Load conversation index."""
    return json.loads(path.read_text(encoding="utf-8"))


def extract_title_features(conversations: list[dict]) -> list[dict]:
    """Extract behavioral features from conversation titles."""
    features = []
    for conv in conversations:
        title = conv.get("title", "")
        tokens = tokenize(title)
        date = conv.get("date_iso")
        if not date or not tokens:
            continue

        void_count = sum(1 for t in tokens if t in ALL_VOID_TERMS)

        # Title style features
        features.append({
            "date": date,
            "title": title,
            "token_count": len(tokens),
            "unique_ratio": len(set(tokens)) / len(tokens) if tokens else 0,
            "void_density": void_count / len(tokens) if tokens else 0,
            "has_colon": ":" in title,
            "has_parenthetical": "(" in title,
            "word_count": len(title.split()),
            "char_count": len(title),
            "capitalized_ratio": sum(1 for w in title.split() if w and w[0].isupper()) / max(len(title.split()), 1),
        })

    return sorted(features, key=lambda x: x["date"])


def extract_text_features(conversations_dir: Path) -> dict[str, dict]:
    """Extract features from full conversation texts."""
    results = {}
    if not conversations_dir.exists():
        return results

    for md_file in sorted(conversations_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        tokens = tokenize(text)
        if len(tokens) < 10:
            continue

        analysis = analyze(text)
        void_terms = analysis["void_term_frequencies"]

        results[md_file.stem] = {
            "file": md_file.name,
            "total_tokens": len(tokens),
            "unique_tokens": len(set(tokens)),
            "ttr": len(set(tokens)) / len(tokens),
            "void_density": analysis["void_cluster"]["proportion"],
            "void_percent": analysis["void_cluster"]["percent"],
            "top_void_terms": dict(list(void_terms.items())[:5]),
            "avg_word_length": sum(len(t) for t in tokens) / len(tokens),
        }

    return results


def sliding_window_compare(
    features: list[dict],
    window_size: int = 5,
    step: int = 1,
) -> list[dict]:
    """
    Compare adjacent sliding windows for behavioral discontinuities.

    For each feature dimension, compute z-score of the difference
    between the mean of window_A (before) and window_B (after).
    """
    if len(features) < window_size * 2:
        return []

    comparisons = []
    numeric_keys = [
        "token_count", "unique_ratio", "void_density",
        "word_count", "char_count", "capitalized_ratio",
    ]

    for i in range(window_size, len(features) - window_size + 1, step):
        window_a = features[max(0, i - window_size):i]
        window_b = features[i:i + window_size]

        if len(window_a) < 2 or len(window_b) < 2:
            continue

        feature_diffs = {}
        for key in numeric_keys:
            vals_a = [f[key] for f in window_a]
            vals_b = [f[key] for f in window_b]

            mean_a = sum(vals_a) / len(vals_a)
            mean_b = sum(vals_b) / len(vals_b)

            # Pooled standard deviation
            var_a = sum((v - mean_a) ** 2 for v in vals_a) / max(len(vals_a) - 1, 1)
            var_b = sum((v - mean_b) ** 2 for v in vals_b) / max(len(vals_b) - 1, 1)
            pooled_std = math.sqrt((var_a + var_b) / 2) if (var_a + var_b) > 0 else 0.001

            z = (mean_b - mean_a) / pooled_std
            cohen_d = abs(mean_b - mean_a) / pooled_std

            feature_diffs[key] = {
                "mean_before": round(mean_a, 4),
                "mean_after": round(mean_b, 4),
                "z_score": round(z, 2),
                "cohen_d": round(cohen_d, 3),
            }

        boundary_date = features[i]["date"]
        comparisons.append({
            "boundary_index": i,
            "boundary_date": boundary_date,
            "window_a_dates": f"{window_a[0]['date']} — {window_a[-1]['date']}",
            "window_b_dates": f"{window_b[0]['date']} — {window_b[-1]['date']}",
            "feature_diffs": feature_diffs,
        })

    return comparisons


def find_change_candidates(
    comparisons: list[dict],
    sensitivity: str = "medium",
) -> list[dict]:
    """Identify the most likely version change points."""
    thresholds = SENSITIVITY.get(sensitivity, SENSITIVITY["medium"])
    candidates = []

    for comp in comparisons:
        significant_features = []
        for key, diff in comp["feature_diffs"].items():
            if abs(diff["z_score"]) > thresholds["z_threshold"] and diff["cohen_d"] > thresholds["min_effect"]:
                significant_features.append({
                    "feature": key,
                    "z_score": diff["z_score"],
                    "effect_size": diff["cohen_d"],
                    "before": diff["mean_before"],
                    "after": diff["mean_after"],
                })

        if len(significant_features) >= thresholds["min_features"]:
            # Compute aggregate confidence
            avg_z = sum(abs(f["z_score"]) for f in significant_features) / len(significant_features)
            avg_d = sum(f["effect_size"] for f in significant_features) / len(significant_features)

            confidence = "high" if avg_z > 3.0 and avg_d > 0.8 else "medium" if avg_z > 2.0 else "low"

            candidates.append({
                "date": comp["boundary_date"],
                "window_before": comp["window_a_dates"],
                "window_after": comp["window_b_dates"],
                "significant_features": significant_features,
                "aggregate_z": round(avg_z, 2),
                "aggregate_effect": round(avg_d, 3),
                "confidence": confidence,
                "description": (
                    f"Behavioral shift at {comp['boundary_date']}: "
                    f"{len(significant_features)} features changed significantly"
                ),
                "evidence": ", ".join(
                    f"{f['feature']} (z={f['z_score']:+.1f}, d={f['effect_size']:.2f})"
                    for f in significant_features
                ),
            })

    # Deduplicate nearby candidates (within 7 days)
    if candidates:
        deduped = [candidates[0]]
        for c in candidates[1:]:
            if c["date"] > deduped[-1]["date"][:8] + str(int(deduped[-1]["date"][8:10]) + 7).zfill(2):
                deduped.append(c)
            elif c["aggregate_z"] > deduped[-1]["aggregate_z"]:
                deduped[-1] = c  # Replace with stronger candidate
        candidates = deduped

    return candidates


def format_markdown(
    title_features: list[dict],
    comparisons: list[dict],
    candidates: list[dict],
    metadata: dict,
) -> str:
    """Format version detection report as markdown."""
    lines = [
        "# Grok Version Change Detection Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Sensitivity:** {metadata.get('sensitivity', 'medium')}",
        f"**Conversations analyzed:** {len(title_features)}",
        f"**Window comparisons:** {len(comparisons)}",
        "",
    ]

    if candidates:
        lines.extend([
            "## 🔄 Version Change Candidates",
            "",
        ])
        for c in candidates:
            lines.extend([
                f"### {c['date']} — Confidence: {c['confidence'].upper()}",
                "",
                f"- **Before:** {c['window_before']}",
                f"- **After:** {c['window_after']}",
                f"- **Aggregate Z:** {c['aggregate_z']}",
                f"- **Aggregate Effect Size:** {c['aggregate_effect']}",
                "",
                "| Feature | Before | After | Z-Score | Cohen's d |",
                "|---------|--------|-------|---------|-----------|",
            ])
            for f in c["significant_features"]:
                lines.append(
                    f"| {f['feature']} | {f['before']:.4f} | {f['after']:.4f} | "
                    f"{f['z_score']:+.2f} | {f['effect_size']:.3f} |"
                )
            lines.append("")
    else:
        lines.extend([
            "## ✅ No Version Changes Detected",
            "",
            "No statistically significant behavioral discontinuities found.",
            "",
        ])

    # Title style summary
    lines.extend([
        "## Title Style Distribution",
        "",
    ])
    if title_features:
        colon_pct = 100 * sum(1 for f in title_features if f["has_colon"]) / len(title_features)
        paren_pct = 100 * sum(1 for f in title_features if f["has_parenthetical"]) / len(title_features)
        avg_words = sum(f["word_count"] for f in title_features) / len(title_features)
        lines.extend([
            f"- Titles with colon separator: {colon_pct:.0f}%",
            f"- Titles with parenthetical: {paren_pct:.0f}%",
            f"- Average title word count: {avg_words:.1f}",
            "",
        ])

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Grok version change detection")
    parser.add_argument("--index", type=Path, required=True)
    parser.add_argument("--conversations", type=Path, default=None)
    parser.add_argument("--sensitivity", choices=["low", "medium", "high"], default="medium")
    parser.add_argument("--min-window", type=int, default=5)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--markdown", type=Path, default=None)
    args = parser.parse_args()

    # Load data
    index = load_index(args.index)
    conversations = index.get("conversations", [])

    # Extract features
    title_features = extract_title_features(conversations)
    print(f"  Title features extracted: {len(title_features)}")

    text_features = {}
    if args.conversations and args.conversations.exists():
        text_features = extract_text_features(args.conversations)
        print(f"  Text features extracted: {len(text_features)}")

    # Sliding window comparison
    comparisons = sliding_window_compare(
        title_features,
        window_size=max(args.min_window, 3),
    )
    print(f"  Window comparisons: {len(comparisons)}")

    # Find change candidates
    candidates = find_change_candidates(comparisons, args.sensitivity)
    print(f"  Version change candidates: {len(candidates)}")

    metadata = {
        "sensitivity": args.sensitivity,
        "min_window": args.min_window,
        "total_conversations": len(conversations),
        "title_features_count": len(title_features),
        "text_features_count": len(text_features),
        "generated_at": datetime.now().isoformat(),
    }

    # Build report
    report = {
        "metadata": metadata,
        "version_change_candidates": candidates,
        "comparisons_count": len(comparisons),
        "title_style_summary": {
            "total": len(title_features),
            "with_colon": sum(1 for f in title_features if f["has_colon"]),
            "with_parenthetical": sum(1 for f in title_features if f["has_parenthetical"]),
            "avg_word_count": round(
                sum(f["word_count"] for f in title_features) / max(len(title_features), 1), 1
            ),
        },
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Version report → {args.output}")

    if args.markdown:
        md = format_markdown(title_features, comparisons, candidates, metadata)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(md, encoding="utf-8")
        print(f"✓ Markdown report → {args.markdown}")


if __name__ == "__main__":
    main()
