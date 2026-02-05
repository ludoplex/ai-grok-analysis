#!/usr/bin/env python3
"""
Void Cluster Frequency Analyzer

Analyzes text for overrepresentation of void/dissolution/emptiness semantic fields.
Compares against configurable baselines using z-test, chi-squared, and Cohen's h.

Usage:
    python analyze.py <text_file> [--baseline 0.05] [--format markdown|json]
"""

import argparse
import json
import math
import re
import sys
from collections import Counter
from pathlib import Path

# Pre-specified void cluster (defined BEFORE looking at data)
VOID_CLUSTER = {
    "direct": {"void"},
    "synonyms": {
        "emptiness", "nothing", "nothingness", "abyss", "vacuum",
        "hollow", "blank", "empty", "null", "zero",
    },
    "semantic_neighbors": {
        "shadow", "shadows", "ghost", "ghosts", "vanish", "vanished",
        "dissolve", "dissolved", "silence", "silenced", "absence",
        "lost", "darkness", "dark", "night", "bleed", "bleeding",
        "fracture", "fractured", "fractures", "chaos", "cage", "caged",
        "drift", "drifting", "fray", "frayed", "twisted", "edges",
        "edge", "whisper", "whispers", "fade", "faded", "fading",
        "shatter", "shattered", "crumble", "collapse", "collapsed",
        "erode", "eroded", "decay", "decayed", "wither", "withered",
        "extinct", "oblivion", "abyss", "chasm", "depths",
        "forgotten", "forsaken", "abandoned", "desolate", "barren",
    },
}

# Flatten all void terms
ALL_VOID_TERMS = set()
for category in VOID_CLUSTER.values():
    ALL_VOID_TERMS.update(category)

# Genre baselines (proportion of void-cluster words in total)
BASELINES = {
    "general_rock": 0.02,
    "general_prog": 0.03,
    "dark_prog": 0.05,
    "metal": 0.06,
    "doom_metal": 0.08,
    "dark_ambient": 0.10,
}


def tokenize(text: str) -> list[str]:
    """Simple word tokenizer — lowercase, strip punctuation."""
    words = re.findall(r"[a-z']+", text.lower())
    return [w for w in words if len(w) > 1]  # Skip single chars


def classify_void_tokens(tokens: list[str]) -> dict:
    """Classify tokens into void cluster categories."""
    result = {"direct": [], "synonyms": [], "semantic_neighbors": [], "non_void": []}
    for token in tokens:
        if token in VOID_CLUSTER["direct"]:
            result["direct"].append(token)
        elif token in VOID_CLUSTER["synonyms"]:
            result["synonyms"].append(token)
        elif token in VOID_CLUSTER["semantic_neighbors"]:
            result["semantic_neighbors"].append(token)
        else:
            result["non_void"].append(token)
    return result


def z_test_proportion(observed: int, total: int, expected_prop: float) -> dict:
    """One-tailed z-test for proportion (observed > expected)."""
    p_hat = observed / total
    se = math.sqrt(expected_prop * (1 - expected_prop) / total)
    if se == 0:
        return {"z": float("inf"), "p": 0.0}
    z = (p_hat - expected_prop) / se
    # Approximate p-value using normal CDF
    p = 0.5 * math.erfc(z / math.sqrt(2))
    return {"z": round(z, 2), "p": p}


def chi_squared(observed: int, total: int, expected_prop: float) -> dict:
    """Chi-squared goodness of fit (df=1)."""
    expected = total * expected_prop
    expected_other = total * (1 - expected_prop)
    observed_other = total - observed
    if expected == 0:
        return {"chi2": float("inf"), "p": 0.0}
    chi2 = ((observed - expected) ** 2 / expected) + (
        (observed_other - expected_other) ** 2 / expected_other
    )
    # Approximate p-value (chi-squared with df=1)
    p = 0.5 * math.erfc(math.sqrt(chi2 / 2))
    return {"chi2": round(chi2, 2), "p": p}


def cohens_h(p1: float, p2: float) -> float:
    """Cohen's h effect size for proportions."""
    h = 2 * math.asin(math.sqrt(p1)) - 2 * math.asin(math.sqrt(p2))
    return round(abs(h), 3)


def analyze(text: str, baselines: dict = None) -> dict:
    """Full void cluster analysis on text."""
    if baselines is None:
        baselines = BASELINES

    tokens = tokenize(text)
    total = len(tokens)
    freq = Counter(tokens)
    classified = classify_void_tokens(tokens)

    void_count = len(classified["direct"]) + len(classified["synonyms"]) + len(classified["semantic_neighbors"])
    void_proportion = void_count / total if total > 0 else 0

    # Void term frequencies
    void_freq = Counter(
        classified["direct"] + classified["synonyms"] + classified["semantic_neighbors"]
    )

    # Statistical tests against each baseline
    tests = {}
    for name, base_prop in baselines.items():
        z = z_test_proportion(void_count, total, base_prop)
        chi2 = chi_squared(void_count, total, base_prop)
        h = cohens_h(void_proportion, base_prop)
        tests[name] = {
            "baseline_prop": base_prop,
            "z_score": z["z"],
            "z_pvalue": z["p"],
            "chi2": chi2["chi2"],
            "chi2_pvalue": chi2["p"],
            "cohens_h": h,
            "ratio": round(void_proportion / base_prop, 1) if base_prop > 0 else float("inf"),
        }

    return {
        "total_tokens": total,
        "unique_words": len(freq),
        "void_cluster": {
            "total": void_count,
            "proportion": round(void_proportion, 4),
            "percent": round(void_proportion * 100, 1),
            "direct": len(classified["direct"]),
            "synonyms": len(classified["synonyms"]),
            "semantic_neighbors": len(classified["semantic_neighbors"]),
        },
        "void_term_frequencies": dict(void_freq.most_common(30)),
        "top_words": dict(freq.most_common(20)),
        "statistical_tests": tests,
    }


def format_markdown(result: dict) -> str:
    """Format analysis result as markdown."""
    lines = ["# Void Cluster Analysis\n"]

    vc = result["void_cluster"]
    lines.append(f"**Total tokens:** {result['total_tokens']}")
    lines.append(f"**Unique words:** {result['unique_words']}")
    lines.append(f"**Void cluster:** {vc['total']} ({vc['percent']}%)")
    lines.append(f"  - Direct: {vc['direct']}")
    lines.append(f"  - Synonyms: {vc['synonyms']}")
    lines.append(f"  - Semantic neighbors: {vc['semantic_neighbors']}\n")

    lines.append("## Void Term Frequencies\n")
    lines.append("| Term | Count |")
    lines.append("|------|------:|")
    for term, count in result["void_term_frequencies"].items():
        lines.append(f"| {term} | {count} |")

    lines.append("\n## Statistical Tests\n")
    lines.append("| Baseline | Expected | Ratio | Z-score | p-value | Chi² | Cohen's h |")
    lines.append("|----------|----------|-------|---------|---------|------|-----------|")
    for name, test in result["statistical_tests"].items():
        p_str = f"{test['z_pvalue']:.6f}" if test["z_pvalue"] > 0.00001 else "< 0.00001"
        lines.append(
            f"| {name} | {test['baseline_prop']:.0%} | {test['ratio']}× | "
            f"{test['z_score']:+.2f} | {p_str} | {test['chi2']:.1f} | {test['cohens_h']:.3f} |"
        )

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Void Cluster Frequency Analyzer")
    parser.add_argument("file", help="Text file to analyze")
    parser.add_argument("--baseline", type=float, help="Custom baseline proportion")
    parser.add_argument("--format", choices=["markdown", "json"], default="markdown")
    args = parser.parse_args()

    text = Path(args.file).read_text(encoding="utf-8")

    baselines = BASELINES
    if args.baseline:
        baselines = {"custom": args.baseline, **BASELINES}

    result = analyze(text, baselines)

    if args.format == "json":
        print(json.dumps(result, indent=2))
    else:
        print(format_markdown(result))


if __name__ == "__main__":
    main()
