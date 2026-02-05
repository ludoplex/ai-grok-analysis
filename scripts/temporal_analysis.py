#!/usr/bin/env python3
"""
temporal_analysis.py — Track void-cluster patterns across the 7-month conversation window.

Analyzes conversation data for:
  - Monthly void-cluster density trends
  - Rolling-window drift detection
  - Seasonal / periodic patterns
  - Outlier periods (months with unexpected spikes)

Usage:
    python temporal_analysis.py \
        --index data/parsed/conversation_index.json \
        --conversations data/conversations/ \
        --window 7 \
        --output reports/temporal_report.json \
        --markdown reports/temporal_report.md
"""

import argparse
import json
import math
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

# Import the analyzer from sibling module
sys.path.insert(0, str(Path(__file__).parent))
from analyze import analyze, tokenize, ALL_VOID_TERMS  # noqa: E402


def load_index(index_path: Path) -> dict:
    """Load the conversation index JSON."""
    return json.loads(index_path.read_text(encoding="utf-8"))


def group_by_month(conversations: list[dict]) -> dict[str, list[dict]]:
    """Group conversations by YYYY-MM."""
    monthly = defaultdict(list)
    for conv in conversations:
        date_iso = conv.get("date_iso")
        if date_iso:
            month_key = date_iso[:7]  # YYYY-MM
            monthly[month_key].append(conv)
    return dict(sorted(monthly.items()))


def analyze_title_void_density(conversations: list[dict]) -> dict:
    """Compute void-cluster density across conversation titles."""
    all_title_tokens = []
    void_hits = []

    for conv in conversations:
        title = conv.get("title", "")
        tokens = tokenize(title)
        all_title_tokens.extend(tokens)
        hits = [t for t in tokens if t in ALL_VOID_TERMS]
        if hits:
            void_hits.append({
                "title": title,
                "date": conv.get("date_iso", "unknown"),
                "hits": hits,
            })

    total = len(all_title_tokens)
    void_count = sum(len(h["hits"]) for h in void_hits)

    return {
        "total_tokens": total,
        "void_count": void_count,
        "void_proportion": round(void_count / total, 6) if total > 0 else 0,
        "void_titles": void_hits,
    }


def analyze_conversation_texts(conversations_dir: Path) -> dict[str, dict]:
    """Analyze full conversation text files, keyed by slug."""
    results = {}
    if not conversations_dir.exists():
        return results

    for md_file in sorted(conversations_dir.glob("*.md")):
        text = md_file.read_text(encoding="utf-8")
        result = analyze(text)
        results[md_file.stem] = {
            "file": md_file.name,
            "void_percent": result["void_cluster"]["percent"],
            "void_total": result["void_cluster"]["total"],
            "total_tokens": result["total_tokens"],
            "top_void_terms": dict(list(result["void_term_frequencies"].items())[:10]),
        }
    return results


def compute_monthly_summary(
    monthly_groups: dict[str, list[dict]],
    text_results: dict[str, dict],
) -> list[dict]:
    """Compute per-month summary statistics."""
    summaries = []

    for month, convs in monthly_groups.items():
        title_analysis = analyze_title_void_density(convs)

        # Match conversations to text analysis results if available
        text_void_pcts = []
        for conv in convs:
            slug = conv.get("slug", "")
            if slug in text_results:
                text_void_pcts.append(text_results[slug]["void_percent"])

        summaries.append({
            "month": month,
            "conversation_count": len(convs),
            "title_void_density": title_analysis["void_proportion"],
            "title_void_count": title_analysis["void_count"],
            "text_analyses_available": len(text_void_pcts),
            "text_void_mean": (
                round(sum(text_void_pcts) / len(text_void_pcts), 2)
                if text_void_pcts else None
            ),
            "text_void_max": max(text_void_pcts) if text_void_pcts else None,
            "titles_with_void": title_analysis["void_titles"],
        })

    return summaries


def detect_drift(monthly_summaries: list[dict], threshold: float = 2.0) -> list[dict]:
    """
    Detect drift in void-cluster density across months.

    Uses a simple rolling z-score: for each month, compare its density
    against the running mean of all previous months.
    """
    alerts = []
    running_values = []

    for summary in monthly_summaries:
        density = summary["title_void_density"]
        count = summary["conversation_count"]

        if len(running_values) >= 2:
            mean = sum(running_values) / len(running_values)
            variance = sum((v - mean) ** 2 for v in running_values) / len(running_values)
            std = math.sqrt(variance) if variance > 0 else 0.001

            z = (density - mean) / std

            if abs(z) > threshold:
                alerts.append({
                    "period": summary["month"],
                    "density": density,
                    "running_mean": round(mean, 6),
                    "z_score": round(z, 2),
                    "severity": "high" if abs(z) > 3.0 else "medium",
                    "message": (
                        f"Void density {density:.4%} deviates from running mean "
                        f"{mean:.4%} (z={z:.2f}, n={count} conversations)"
                    ),
                })

        running_values.append(density)

    return alerts


def detect_volume_anomalies(monthly_summaries: list[dict]) -> list[dict]:
    """Flag months with unusually high or low conversation volume."""
    alerts = []
    counts = [s["conversation_count"] for s in monthly_summaries]

    if len(counts) < 3:
        return alerts

    mean = sum(counts) / len(counts)
    variance = sum((c - mean) ** 2 for c in counts) / len(counts)
    std = math.sqrt(variance) if variance > 0 else 1

    for summary in monthly_summaries:
        z = (summary["conversation_count"] - mean) / std
        if abs(z) > 2.0:
            direction = "spike" if z > 0 else "drop"
            alerts.append({
                "period": summary["month"],
                "count": summary["conversation_count"],
                "mean": round(mean, 1),
                "z_score": round(z, 2),
                "severity": "info",
                "message": (
                    f"Volume {direction}: {summary['conversation_count']} conversations "
                    f"(mean={mean:.0f}, z={z:.2f})"
                ),
            })

    return alerts


def format_markdown_report(
    monthly_summaries: list[dict],
    drift_alerts: list[dict],
    volume_alerts: list[dict],
    metadata: dict,
) -> str:
    """Format temporal analysis as a markdown report."""
    lines = [
        "# Temporal Pattern Analysis Report",
        "",
        f"**Generated:** {datetime.now().isoformat()}",
        f"**Window:** {metadata.get('window_months', 7)} months",
        f"**Total conversations:** {metadata.get('total_conversations', 'N/A')}",
        "",
    ]

    # Monthly summary table
    lines.extend([
        "## Monthly Summary",
        "",
        "| Month | Sessions | Title Void Density | Text Analyses | Text Void Mean |",
        "|-------|----------|-------------------|---------------|----------------|",
    ])

    for s in monthly_summaries:
        text_mean = f"{s['text_void_mean']:.1f}%" if s["text_void_mean"] is not None else "—"
        lines.append(
            f"| {s['month']} | {s['conversation_count']} | "
            f"{s['title_void_density']:.4%} | "
            f"{s['text_analyses_available']} | {text_mean} |"
        )

    # Drift alerts
    all_alerts = drift_alerts + volume_alerts
    if all_alerts:
        lines.extend(["", "## ⚠️ Alerts", ""])
        for alert in all_alerts:
            icon = "🔴" if alert["severity"] == "high" else "🟡" if alert["severity"] == "medium" else "ℹ️"
            lines.append(f"- {icon} **{alert['period']}**: {alert['message']}")
    else:
        lines.extend(["", "## ✅ No Drift Detected", ""])
        lines.append("All months within expected void-cluster density range.")

    # Volume distribution
    lines.extend([
        "",
        "## Volume Distribution",
        "",
        "```",
    ])
    max_count = max((s["conversation_count"] for s in monthly_summaries), default=1)
    for s in monthly_summaries:
        bar_len = int(40 * s["conversation_count"] / max_count) if max_count > 0 else 0
        bar = "█" * bar_len
        lines.append(f"  {s['month']}  {bar} {s['conversation_count']}")
    lines.append("```")

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Temporal void-cluster pattern analysis")
    parser.add_argument("--index", type=Path, required=True, help="Conversation index JSON")
    parser.add_argument("--conversations", type=Path, default=None, help="Directory of conversation .md files")
    parser.add_argument("--window", type=int, default=7, help="Analysis window in months")
    parser.add_argument("--output", type=Path, required=True, help="Output JSON report")
    parser.add_argument("--markdown", type=Path, default=None, help="Output markdown report")
    args = parser.parse_args()

    # Load data
    index = load_index(args.index)
    conversations = index.get("conversations", [])

    # Group by month
    monthly = group_by_month(conversations)

    # Analyze conversation texts if directory provided
    text_results = {}
    if args.conversations and args.conversations.exists():
        text_results = analyze_conversation_texts(args.conversations)

    # Compute summaries
    monthly_summaries = compute_monthly_summary(monthly, text_results)

    # Detect anomalies
    drift_alerts = detect_drift(monthly_summaries)
    volume_alerts = detect_volume_anomalies(monthly_summaries)

    metadata = {
        "window_months": args.window,
        "total_conversations": len(conversations),
        "date_range": index.get("date_range", {}),
        "generated_at": datetime.now().isoformat(),
    }

    # Build report
    report = {
        "metadata": metadata,
        "monthly_summary": monthly_summaries,
        "alerts": drift_alerts + volume_alerts,
        "text_analysis_count": len(text_results),
    }

    # Write outputs
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"✓ Temporal report → {args.output}")

    if args.markdown:
        md = format_markdown_report(monthly_summaries, drift_alerts, volume_alerts, metadata)
        args.markdown.parent.mkdir(parents=True, exist_ok=True)
        args.markdown.write_text(md, encoding="utf-8")
        print(f"✓ Markdown report → {args.markdown}")

    # Print summary
    print(f"\n  Months analyzed: {len(monthly_summaries)}")
    print(f"  Conversations: {len(conversations)}")
    print(f"  Text files analyzed: {len(text_results)}")
    print(f"  Alerts: {len(drift_alerts + volume_alerts)}")


if __name__ == "__main__":
    main()
