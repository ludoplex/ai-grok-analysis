#!/usr/bin/env python3
"""
anomaly_detect.py — Flag statistically unusual word patterns in Grok conversations.

Detects multiple types of anomalies:
  1. Lexical outliers: words that appear at unusual rates vs. category baseline
  2. Semantic drift: vocabulary shifts over time (model update detection)
  3. Response length anomalies: unusually long/short responses for category
  4. Vocabulary richness outliers: TTR/Yule's K that deviate from norms
  5. Cross-category contamination: technical terms in creative contexts, etc.
  6. Repetition patterns: unusual word/phrase repetition within single responses
  7. Void cluster analysis: overrepresentation of dissolution/emptiness semantics

Uses z-scores, IQR method, and isolation forests when sklearn is available.

Usage:
    # Run all anomaly detections on corpus
    python anomaly_detect.py --corpus data/parsed/ --categories data/analysis/categories.json

    # Check single conversation against corpus baselines
    python anomaly_detect.py --file data/parsed/conv_something.json --baselines data/analysis/baselines.json

    # Build category baselines from corpus (run first)
    python anomaly_detect.py --build-baselines data/parsed/ --categories data/analysis/categories.json

    # Temporal drift analysis (model update detection)
    python anomaly_detect.py --drift data/parsed/ --index data/parsed/conversation_index.json

    # Full report
    python anomaly_detect.py --full-report data/parsed/
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

import numpy as np

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PARSED_DIR = DATA_DIR / "parsed"
OUTPUT_DIR = DATA_DIR / "analysis"

# Try importing sklearn for isolation forest
try:
    from sklearn.ensemble import IsolationForest
    HAS_SKLEARN = True
except ImportError:
    HAS_SKLEARN = False

# ── Void/Dissolution semantic cluster (from existing analyze.py) ───────────

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
        "extinct", "oblivion", "chasm", "depths",
        "forgotten", "forsaken", "abandoned", "desolate", "barren",
    },
}

ALL_VOID_TERMS = set()
for _cat_terms in VOID_CLUSTER.values():
    ALL_VOID_TERMS.update(_cat_terms)

# ── Technical jargon that's expected in tech but anomalous elsewhere ──────

TECHNICAL_JARGON = {
    "function", "variable", "class", "object", "method", "parameter",
    "argument", "return", "compile", "debug", "error", "exception",
    "thread", "process", "memory", "stack", "heap", "pointer",
    "array", "list", "dictionary", "hash", "tree", "graph",
    "api", "endpoint", "request", "response", "server", "client",
    "protocol", "packet", "socket", "port", "firewall",
    "algorithm", "complexity", "optimization", "binary", "hex",
    "register", "instruction", "pipeline", "cache", "buffer",
    "kernel", "driver", "interrupt", "syscall", "mutex", "semaphore",
}

CREATIVE_LANGUAGE = {
    "beautiful", "stunning", "vibrant", "ethereal", "haunting",
    "poetic", "lyrical", "whimsical", "surreal", "dreamlike",
    "narrative", "character", "protagonist", "antagonist",
    "metaphor", "symbolism", "imagery", "aesthetic",
    "composition", "palette", "texture", "contrast",
    "emotion", "feeling", "soul", "spirit", "essence",
    "imagine", "envision", "inspiration", "muse",
}


def tokenize(text: str) -> list[str]:
    """Tokenize text into lowercase words."""
    text = text.lower()
    text = re.sub(r"```[\s\S]*?```", " ", text)  # Remove code blocks
    text = re.sub(r"`[^`]+`", " ", text)  # Remove inline code
    text = re.sub(r"https?://\S+", " ", text)  # Remove URLs
    words = re.findall(r"\b[a-z][a-z'-]*[a-z]\b|[a-z]\b", text)
    return [w for w in words if len(w) > 1]


def extract_features(conv_data: dict) -> dict:
    """Extract numerical features from a conversation for anomaly detection."""
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

    grok_tokens = tokenize(grok_text)
    user_tokens = tokenize(user_text)
    grok_freq = Counter(grok_tokens)

    total_grok = len(grok_tokens)
    unique_grok = len(set(grok_tokens))

    # Void cluster metrics
    void_count = sum(1 for t in grok_tokens if t in ALL_VOID_TERMS)
    void_proportion = void_count / total_grok if total_grok > 0 else 0

    # Technical jargon density
    tech_count = sum(1 for t in grok_tokens if t in TECHNICAL_JARGON)
    tech_density = tech_count / total_grok if total_grok > 0 else 0

    # Creative language density
    creative_count = sum(1 for t in grok_tokens if t in CREATIVE_LANGUAGE)
    creative_density = creative_count / total_grok if total_grok > 0 else 0

    # Type-token ratio
    ttr = unique_grok / total_grok if total_grok > 0 else 0

    # Hapax legomena ratio
    hapax = sum(1 for c in grok_freq.values() if c == 1)
    hapax_ratio = hapax / unique_grok if unique_grok > 0 else 0

    # Repetition index: max single-word frequency / total
    max_freq = max(grok_freq.values()) if grok_freq else 0
    repetition_idx = max_freq / total_grok if total_grok > 0 else 0

    # Response length stats per turn
    grok_turns = [
        turn for turn in conv_data.get("turns", []) if turn["role"] == "grok"
    ]
    turn_lengths = [len(turn["content"].split()) for turn in grok_turns]
    avg_turn_len = np.mean(turn_lengths) if turn_lengths else 0
    std_turn_len = np.std(turn_lengths) if len(turn_lengths) > 1 else 0

    # User/Grok word ratio
    user_grok_ratio = len(user_tokens) / total_grok if total_grok > 0 else 0

    return {
        "total_grok_tokens": total_grok,
        "unique_grok_tokens": unique_grok,
        "void_proportion": void_proportion,
        "void_count": void_count,
        "tech_density": tech_density,
        "creative_density": creative_density,
        "ttr": ttr,
        "hapax_ratio": hapax_ratio,
        "repetition_index": repetition_idx,
        "avg_turn_length": float(avg_turn_len),
        "std_turn_length": float(std_turn_len),
        "num_grok_turns": len(grok_turns),
        "user_grok_ratio": user_grok_ratio,
    }


def build_baselines(corpus: list[dict], categories: Optional[dict] = None) -> dict:
    """
    Build per-category baselines from the corpus.
    Returns mean ± std for each feature per category.
    """
    # Map conversation IDs to categories
    cat_map = {}
    if categories:
        for item in categories:
            cat_map[item.get("id", "")] = item.get("primary_category", "uncategorized")

    # Group features by category
    cat_features: dict[str, list[dict]] = defaultdict(list)

    for conv in corpus:
        features = extract_features(conv)
        category = cat_map.get(conv["id"], "uncategorized")
        features["category"] = category
        features["title"] = conv["title"]
        cat_features[category].append(features)

    # Also compute corpus-wide baseline
    all_features = []
    for feats_list in cat_features.values():
        all_features.extend(feats_list)
    cat_features["_corpus"] = all_features

    # Compute statistics per category
    baselines = {}
    feature_keys = [
        "total_grok_tokens", "void_proportion", "tech_density",
        "creative_density", "ttr", "hapax_ratio", "repetition_index",
        "avg_turn_length", "user_grok_ratio",
    ]

    for category, features_list in cat_features.items():
        if not features_list:
            continue
        stats = {"count": len(features_list)}
        for key in feature_keys:
            values = [f[key] for f in features_list if key in f]
            if values:
                stats[key] = {
                    "mean": float(np.mean(values)),
                    "std": float(np.std(values)),
                    "median": float(np.median(values)),
                    "min": float(np.min(values)),
                    "max": float(np.max(values)),
                    "q1": float(np.percentile(values, 25)),
                    "q3": float(np.percentile(values, 75)),
                }
        baselines[category] = stats

    return baselines


def detect_zscore_anomalies(
    conv_data: dict,
    baselines: dict,
    category: str = "_corpus",
    threshold: float = 2.0,
) -> list[dict]:
    """
    Detect features that deviate > threshold standard deviations from baseline.
    """
    features = extract_features(conv_data)
    baseline = baselines.get(category, baselines.get("_corpus", {}))
    anomalies = []

    for key, value in features.items():
        if key in ("total_grok_tokens", "void_count", "num_grok_turns"):
            continue  # Skip count features, analyze proportions
        if not isinstance(value, (int, float)):
            continue

        stats = baseline.get(key)
        if not stats or not isinstance(stats, dict):
            continue

        mean = stats.get("mean", 0)
        std = stats.get("std", 0)

        if std == 0:
            continue

        z = (value - mean) / std

        if abs(z) > threshold:
            anomalies.append({
                "feature": key,
                "value": round(value, 6),
                "z_score": round(z, 2),
                "baseline_mean": round(mean, 6),
                "baseline_std": round(std, 6),
                "category": category,
                "direction": "high" if z > 0 else "low",
                "severity": "extreme" if abs(z) > 3 else "notable",
            })

    return anomalies


def detect_void_cluster_anomaly(conv_data: dict, baselines: dict, category: str) -> Optional[dict]:
    """
    Specifically check if void/dissolution language is anomalous for this category.
    Technical conversations should have near-zero void cluster density.
    """
    grok_text = " ".join(
        turn["content"]
        for turn in conv_data.get("turns", [])
        if turn["role"] == "grok"
    )
    tokens = tokenize(grok_text)
    total = len(tokens)
    if total < 50:  # Too short for meaningful analysis
        return None

    void_tokens = [t for t in tokens if t in ALL_VOID_TERMS]
    void_count = len(void_tokens)
    void_prop = void_count / total

    # Category-specific expected rate
    baseline = baselines.get(category, baselines.get("_corpus", {}))
    void_stats = baseline.get("void_proportion", {})

    if not void_stats:
        return None

    mean = void_stats.get("mean", 0)
    std = void_stats.get("std", 0)

    if std == 0:
        std = 0.001  # Prevent division by zero

    z = (void_prop - mean) / std

    if z > 1.5:  # Lower threshold for void specifically
        void_freq = Counter(void_tokens)
        return {
            "type": "void_cluster_overrepresentation",
            "void_proportion": round(void_prop, 6),
            "void_count": void_count,
            "total_tokens": total,
            "z_score": round(z, 2),
            "expected_mean": round(mean, 6),
            "expected_std": round(std, 6),
            "category": category,
            "top_void_terms": dict(void_freq.most_common(10)),
            "void_by_tier": {
                "direct": sum(1 for t in void_tokens if t in VOID_CLUSTER["direct"]),
                "synonyms": sum(1 for t in void_tokens if t in VOID_CLUSTER["synonyms"]),
                "semantic_neighbors": sum(1 for t in void_tokens if t in VOID_CLUSTER["semantic_neighbors"]),
            },
        }
    return None


def detect_cross_contamination(conv_data: dict, category: str) -> list[dict]:
    """
    Detect when a conversation's language doesn't match its expected category.
    E.g., heavy technical jargon in a 'creative' conversation.
    """
    features = extract_features(conv_data)
    anomalies = []

    if category == "creative" and features["tech_density"] > 0.05:
        anomalies.append({
            "type": "cross_contamination",
            "detail": f"Technical jargon density {features['tech_density']:.1%} in creative conversation",
            "tech_density": features["tech_density"],
            "expected_category": category,
        })

    if category == "technical" and features["creative_density"] > 0.03:
        anomalies.append({
            "type": "cross_contamination",
            "detail": f"Creative language density {features['creative_density']:.1%} in technical conversation",
            "creative_density": features["creative_density"],
            "expected_category": category,
        })

    if category in ("technical", "business") and features["void_proportion"] > 0.02:
        anomalies.append({
            "type": "unexpected_void_language",
            "detail": f"Void/dissolution density {features['void_proportion']:.1%} in {category} conversation",
            "void_proportion": features["void_proportion"],
            "expected_category": category,
        })

    return anomalies


def detect_repetition_anomalies(conv_data: dict) -> list[dict]:
    """
    Detect unusual repetition patterns within individual Grok responses.
    Flags responses where specific words/phrases repeat at abnormal rates.
    """
    anomalies = []
    grok_turns = [
        turn for turn in conv_data.get("turns", [])
        if turn["role"] == "grok"
    ]

    for turn in grok_turns:
        tokens = tokenize(turn["content"])
        if len(tokens) < 30:
            continue

        freq = Counter(tokens)
        total = len(tokens)

        # Flag any non-stop-word appearing > 3% of total tokens
        stop_words = {
            "the", "a", "an", "is", "are", "was", "were", "be", "been",
            "have", "has", "had", "do", "does", "did", "will", "would",
            "can", "could", "should", "may", "might", "to", "of", "in",
            "for", "on", "with", "at", "by", "from", "and", "or", "but",
            "not", "this", "that", "it", "you", "your", "we", "they",
        }

        for word, count in freq.most_common(20):
            if word in stop_words:
                continue
            rate = count / total
            if rate > 0.03 and count >= 5:
                anomalies.append({
                    "type": "word_repetition",
                    "word": word,
                    "count": count,
                    "rate": round(rate, 4),
                    "turn_index": turn["index"],
                    "turn_length": total,
                })

    return anomalies


def temporal_drift_analysis(
    corpus: list[dict],
    index_data: dict,
    window_months: int = 2,
) -> dict:
    """
    Detect if Grok's response patterns changed over time.
    Groups conversations by time window and compares feature distributions.

    Key insight: model updates should produce discontinuities in:
    - Vocabulary richness (TTR, Yule's K)
    - Response length distribution
    - Void cluster density
    - Technical jargon density patterns
    """
    # Map conversation IDs to dates
    date_map = {}
    for conv in index_data.get("conversations", []):
        if conv.get("date_iso"):
            date_map[conv["id"]] = conv["date_iso"]

    # Extract features with dates
    dated_features: list[tuple[str, dict]] = []
    for conv in corpus:
        date_iso = date_map.get(conv["id"])
        if not date_iso:
            continue
        features = extract_features(conv)
        features["title"] = conv["title"]
        features["date"] = date_iso
        dated_features.append((date_iso, features))

    dated_features.sort(key=lambda x: x[0])

    if len(dated_features) < 4:
        return {"error": "Not enough dated conversations for drift analysis", "count": len(dated_features)}

    # Group by month
    monthly: dict[str, list[dict]] = defaultdict(list)
    for date, features in dated_features:
        month_key = date[:7]
        monthly[month_key].append(features)

    months_sorted = sorted(monthly.keys())

    # Compute per-month aggregates
    timeline = {}
    feature_keys = [
        "void_proportion", "tech_density", "creative_density",
        "ttr", "hapax_ratio", "repetition_index", "avg_turn_length",
    ]

    for month in months_sorted:
        feats = monthly[month]
        month_stats = {"count": len(feats)}
        for key in feature_keys:
            vals = [f[key] for f in feats if key in f]
            if vals:
                month_stats[key] = {
                    "mean": round(float(np.mean(vals)), 6),
                    "std": round(float(np.std(vals)), 6),
                }
        timeline[month] = month_stats

    # Detect change points: compare each month to the previous
    change_points = []
    for i in range(1, len(months_sorted)):
        prev_month = months_sorted[i - 1]
        curr_month = months_sorted[i]
        prev_stats = timeline[prev_month]
        curr_stats = timeline[curr_month]

        significant_changes = []
        for key in feature_keys:
            if key not in prev_stats or key not in curr_stats:
                continue
            prev_val = prev_stats[key]["mean"]
            curr_val = curr_stats[key]["mean"]
            prev_std = prev_stats[key].get("std", 0)

            if prev_std > 0:
                change = abs(curr_val - prev_val) / prev_std
            elif prev_val > 0:
                change = abs(curr_val - prev_val) / prev_val
            else:
                change = 0

            if change > 1.5:  # 1.5 standard deviations shift
                significant_changes.append({
                    "feature": key,
                    "prev_mean": prev_val,
                    "curr_mean": curr_val,
                    "change_magnitude": round(change, 2),
                    "direction": "increase" if curr_val > prev_val else "decrease",
                })

        if significant_changes:
            change_points.append({
                "transition": f"{prev_month} → {curr_month}",
                "changes": significant_changes,
                "possible_model_update": len(significant_changes) >= 3,
            })

    # Known Grok model update dates (add as discovered)
    known_updates = [
        {"date": "2025-11-01", "version": "Grok-2 (estimated)", "note": "Approximate"},
        {"date": "2025-12-15", "version": "Grok-2.5 (estimated)", "note": "Approximate"},
    ]

    return {
        "monthly_timeline": timeline,
        "change_points": change_points,
        "known_model_updates": known_updates,
        "total_dated_conversations": len(dated_features),
        "date_range": {
            "earliest": dated_features[0][0] if dated_features else None,
            "latest": dated_features[-1][0] if dated_features else None,
        },
    }


def isolation_forest_anomalies(corpus: list[dict], contamination: float = 0.1) -> list[dict]:
    """
    Use Isolation Forest to detect multivariate anomalies.
    Considers all features simultaneously.
    """
    if not HAS_SKLEARN:
        return [{"error": "scikit-learn not installed, skipping isolation forest"}]

    feature_keys = [
        "total_grok_tokens", "void_proportion", "tech_density",
        "creative_density", "ttr", "hapax_ratio", "repetition_index",
        "avg_turn_length", "user_grok_ratio",
    ]

    # Build feature matrix
    titles = []
    feature_matrix = []
    for conv in corpus:
        features = extract_features(conv)
        row = [features.get(k, 0) for k in feature_keys]
        if all(v == 0 for v in row):
            continue
        feature_matrix.append(row)
        titles.append(conv["title"])

    if len(feature_matrix) < 10:
        return [{"error": f"Too few conversations ({len(feature_matrix)}) for isolation forest"}]

    X = np.array(feature_matrix)

    # Normalize
    means = X.mean(axis=0)
    stds = X.std(axis=0)
    stds[stds == 0] = 1
    X_norm = (X - means) / stds

    clf = IsolationForest(contamination=contamination, random_state=42, n_estimators=100)
    predictions = clf.fit_predict(X_norm)
    scores = clf.decision_function(X_norm)

    anomalies = []
    for i, (pred, score) in enumerate(zip(predictions, scores)):
        if pred == -1:
            # Find which features are most anomalous
            feature_zscores = {
                feature_keys[j]: round(float(X_norm[i][j]), 2)
                for j in range(len(feature_keys))
                if abs(X_norm[i][j]) > 1.5
            }
            anomalies.append({
                "title": titles[i],
                "anomaly_score": round(float(score), 4),
                "outlier_features": feature_zscores,
                "raw_features": {
                    feature_keys[j]: round(float(X[i][j]), 6)
                    for j in range(len(feature_keys))
                },
            })

    anomalies.sort(key=lambda x: x["anomaly_score"])
    return anomalies


def full_anomaly_report(
    corpus: list[dict],
    categories: Optional[list[dict]] = None,
    index_data: Optional[dict] = None,
) -> dict:
    """
    Run ALL anomaly detection methods and produce comprehensive report.
    """
    # Build category map
    cat_map = {}
    if categories:
        for item in categories:
            cat_map[item.get("id", "")] = item.get("primary_category", "uncategorized")

    # Build baselines
    baselines = build_baselines(corpus, categories)

    # Per-conversation anomalies
    conversation_anomalies = []
    for conv in corpus:
        category = cat_map.get(conv["id"], "_corpus")
        title = conv["title"]

        all_anomalies = []

        # Z-score anomalies
        z_anomalies = detect_zscore_anomalies(conv, baselines, category)
        all_anomalies.extend(z_anomalies)

        # Also check against corpus baseline
        if category != "_corpus":
            corpus_anomalies = detect_zscore_anomalies(conv, baselines, "_corpus")
            for a in corpus_anomalies:
                a["note"] = "vs corpus baseline"
            all_anomalies.extend(corpus_anomalies)

        # Void cluster
        void_anomaly = detect_void_cluster_anomaly(conv, baselines, category)
        if void_anomaly:
            all_anomalies.append(void_anomaly)

        # Cross-contamination
        cross = detect_cross_contamination(conv, category)
        all_anomalies.extend(cross)

        # Repetition
        repetition = detect_repetition_anomalies(conv)
        all_anomalies.extend(repetition)

        if all_anomalies:
            conversation_anomalies.append({
                "title": title,
                "id": conv["id"],
                "category": category,
                "anomaly_count": len(all_anomalies),
                "anomalies": all_anomalies,
            })

    # Sort by anomaly count (most anomalous first)
    conversation_anomalies.sort(key=lambda x: -x["anomaly_count"])

    # Isolation forest (multivariate)
    iso_anomalies = isolation_forest_anomalies(corpus)

    # Temporal drift
    drift = {}
    if index_data:
        drift = temporal_drift_analysis(corpus, index_data)

    # Summary statistics
    total_convs = len(corpus)
    anomalous_convs = len(conversation_anomalies)

    return {
        "summary": {
            "total_conversations": total_convs,
            "anomalous_conversations": anomalous_convs,
            "anomaly_rate": round(anomalous_convs / total_convs, 3) if total_convs else 0,
            "total_anomalies": sum(c["anomaly_count"] for c in conversation_anomalies),
        },
        "baselines": baselines,
        "per_conversation": conversation_anomalies[:50],  # Top 50 most anomalous
        "isolation_forest": iso_anomalies,
        "temporal_drift": drift,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Detect statistical anomalies in Grok conversation patterns"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--corpus", type=Path, help="Directory of parsed conversation JSONs")
    group.add_argument("--file", type=Path, help="Single conversation to check")
    group.add_argument("--build-baselines", type=Path, help="Build baselines from corpus dir")
    group.add_argument("--drift", type=Path, help="Temporal drift analysis on corpus dir")
    group.add_argument("--full-report", type=Path, help="Full anomaly report on corpus dir")

    parser.add_argument("--categories", type=Path, help="Categories JSON from categorize.py")
    parser.add_argument("--index", type=Path, help="Conversation index JSON")
    parser.add_argument("--baselines", type=Path, help="Pre-built baselines JSON")
    parser.add_argument("-o", "--output", type=Path, help="Output file")
    parser.add_argument("--threshold", type=float, default=2.0, help="Z-score threshold (default: 2.0)")

    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    def load_corpus(path: Path) -> list[dict]:
        files = sorted(path.glob("conv_*.json"))
        return [json.loads(f.read_text(encoding="utf-8")) for f in files]

    def load_json(path: Optional[Path]) -> Optional[dict | list]:
        if path and path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
        return None

    if args.build_baselines:
        corpus = load_corpus(args.build_baselines)
        categories = load_json(args.categories)
        baselines = build_baselines(corpus, categories)
        out = args.output or (OUTPUT_DIR / "baselines.json")
        out.write_text(json.dumps(baselines, indent=2), encoding="utf-8")
        print(f"✓ Built baselines from {len(corpus)} conversations → {out}")
        for cat, stats in baselines.items():
            print(f"  {cat}: {stats['count']} conversations")

    elif args.file:
        conv = json.loads(args.file.read_text(encoding="utf-8"))
        baselines_data = load_json(args.baselines)
        if not baselines_data:
            print("⚠ No baselines file. Run --build-baselines first.")
            print("  Running with minimal defaults...")
            baselines_data = {"_corpus": {"count": 1}}

        anomalies = detect_zscore_anomalies(conv, baselines_data, threshold=args.threshold)
        void = detect_void_cluster_anomaly(conv, baselines_data, "_corpus")
        repetition = detect_repetition_anomalies(conv)

        all_anomalies = anomalies + ([void] if void else []) + repetition

        print(f"\nAnomalies for: {conv['title']}")
        print(f"  Total anomalies: {len(all_anomalies)}")
        for a in all_anomalies:
            atype = a.get("type", a.get("feature", "unknown"))
            detail = a.get("detail", f"z={a.get('z_score', '?')}")
            print(f"  ⚠ {atype}: {detail}")

        if args.output:
            result = {"title": conv["title"], "anomalies": all_anomalies}
            args.output.write_text(json.dumps(result, indent=2), encoding="utf-8")

    elif args.corpus:
        corpus = load_corpus(args.corpus)
        categories = load_json(args.categories)
        baselines = build_baselines(corpus, categories)
        out = args.output or (OUTPUT_DIR / "anomalies.json")

        all_anomalies = []
        cat_map = {}
        if categories:
            for item in categories:
                cat_map[item.get("id", "")] = item.get("primary_category", "uncategorized")

        for conv in corpus:
            category = cat_map.get(conv["id"], "_corpus")
            anomalies = detect_zscore_anomalies(conv, baselines, category, args.threshold)
            if anomalies:
                all_anomalies.append({
                    "title": conv["title"],
                    "category": category,
                    "anomalies": anomalies,
                })

        all_anomalies.sort(key=lambda x: -len(x["anomalies"]))
        result = {"total": len(all_anomalies), "conversations": all_anomalies}
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"✓ Found anomalies in {len(all_anomalies)}/{len(corpus)} conversations → {out}")

    elif args.drift:
        corpus = load_corpus(args.drift)
        index_path = args.index or (PARSED_DIR / "conversation_index.json")
        index_data = load_json(index_path)
        if not index_data:
            print("⚠ Need --index with conversation dates for drift analysis")
            sys.exit(1)

        result = temporal_drift_analysis(corpus, index_data)
        out = args.output or (OUTPUT_DIR / "temporal_drift.json")
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")
        print(f"✓ Temporal drift analysis → {out}")
        print(f"  Dated conversations: {result['total_dated_conversations']}")
        print(f"  Change points detected: {len(result['change_points'])}")
        for cp in result["change_points"]:
            marker = " 🔴 POSSIBLE MODEL UPDATE" if cp["possible_model_update"] else ""
            print(f"  {cp['transition']}: {len(cp['changes'])} features changed{marker}")

    elif args.full_report:
        corpus = load_corpus(args.full_report)
        categories = load_json(args.categories)
        index_path = args.index or (PARSED_DIR / "conversation_index.json")
        index_data = load_json(index_path)

        result = full_anomaly_report(corpus, categories, index_data)
        out = args.output or (OUTPUT_DIR / "full_anomaly_report.json")
        out.write_text(json.dumps(result, indent=2), encoding="utf-8")

        s = result["summary"]
        print(f"✓ Full anomaly report → {out}")
        print(f"  Conversations: {s['total_conversations']}")
        print(f"  Anomalous: {s['anomalous_conversations']} ({s['anomaly_rate']:.0%})")
        print(f"  Total anomalies: {s['total_anomalies']}")

        if result["isolation_forest"] and not isinstance(result["isolation_forest"][0], dict) or (
            result["isolation_forest"] and "error" not in result["isolation_forest"][0]
        ):
            print(f"  Isolation forest outliers: {len(result['isolation_forest'])}")

        if result["temporal_drift"].get("change_points"):
            print(f"  Temporal change points: {len(result['temporal_drift']['change_points'])}")


if __name__ == "__main__":
    main()
