#!/usr/bin/env python3
"""
tokenize_conversations.py — Word/phrase frequency analysis per conversation.

Analyzes parsed conversation JSONs for:
  - Unigram, bigram, trigram frequencies (per conversation and corpus-wide)
  - TF-IDF scores (treating each conversation as a document)
  - Role-split analysis (user vs grok token distributions)
  - Temporal token frequency (by month)
  - Vocabulary richness metrics (TTR, hapax ratio, Yule's K)

Usage:
    # Analyze a single parsed conversation
    python tokenize_conversations.py --file data/parsed/conv_something.json

    # Analyze all parsed conversations (corpus-level)
    python tokenize_conversations.py --corpus data/parsed/

    # Output TF-IDF matrix
    python tokenize_conversations.py --corpus data/parsed/ --tfidf

    # Temporal analysis
    python tokenize_conversations.py --corpus data/parsed/ --temporal
"""

import argparse
import json
import math
import re
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"
PARSED_DIR = DATA_DIR / "parsed"
OUTPUT_DIR = DATA_DIR / "analysis"

# Common English stop words (extended for chat context)
STOP_WORDS = {
    "the", "a", "an", "is", "are", "was", "were", "be", "been", "being",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "shall", "can", "need", "dare", "ought",
    "used", "to", "of", "in", "for", "on", "with", "at", "by", "from",
    "as", "into", "through", "during", "before", "after", "above", "below",
    "between", "out", "off", "over", "under", "again", "further", "then",
    "once", "here", "there", "when", "where", "why", "how", "all", "both",
    "each", "few", "more", "most", "other", "some", "such", "no", "nor",
    "not", "only", "own", "same", "so", "than", "too", "very", "just",
    "don", "now", "and", "but", "or", "if", "while", "because", "until",
    "although", "since", "unless", "that", "this", "these", "those",
    "i", "me", "my", "myself", "we", "our", "ours", "ourselves",
    "you", "your", "yours", "yourself", "yourselves",
    "he", "him", "his", "himself", "she", "her", "hers", "herself",
    "it", "its", "itself", "they", "them", "their", "theirs", "themselves",
    "what", "which", "who", "whom", "whose", "about", "also", "like",
    "get", "got", "make", "made", "know", "think", "see", "come", "take",
    "want", "look", "use", "go", "going", "well", "back", "even",
    "give", "tell", "say", "said", "thing", "things", "much", "many",
    "really", "right", "still", "way", "new", "one", "two", "first",
}


def tokenize(text: str, lowercase: bool = True) -> list[str]:
    """
    Tokenize text into words.
    Preserves hyphenated words, strips possessives.
    """
    if lowercase:
        text = text.lower()
    # Remove code blocks (``` ... ```)
    text = re.sub(r"```[\s\S]*?```", " CODE_BLOCK ", text)
    # Remove inline code (`...`)
    text = re.sub(r"`[^`]+`", " CODE_INLINE ", text)
    # Remove URLs
    text = re.sub(r"https?://\S+", " URL ", text)
    # Remove markdown formatting
    text = re.sub(r"[*_#>|~\[\](){}]", " ", text)
    # Tokenize: letters, numbers, hyphens within words
    words = re.findall(r"\b[a-z][a-z'-]*[a-z]\b|[a-z]\b", text)
    return [w for w in words if len(w) > 1]


def ngrams(tokens: list[str], n: int) -> list[str]:
    """Generate n-grams from token list."""
    return [" ".join(tokens[i:i + n]) for i in range(len(tokens) - n + 1)]


def remove_stopwords(tokens: list[str]) -> list[str]:
    """Remove stop words from token list."""
    return [t for t in tokens if t not in STOP_WORDS]


def type_token_ratio(tokens: list[str]) -> float:
    """Type-Token Ratio — vocabulary diversity."""
    if not tokens:
        return 0.0
    return len(set(tokens)) / len(tokens)


def hapax_ratio(tokens: list[str]) -> float:
    """Proportion of words that appear exactly once."""
    if not tokens:
        return 0.0
    freq = Counter(tokens)
    hapax = sum(1 for count in freq.values() if count == 1)
    return hapax / len(freq)


def yules_k(tokens: list[str]) -> float:
    """
    Yule's K — vocabulary richness measure.
    Lower K = richer vocabulary. Independent of text length.
    """
    if not tokens:
        return 0.0
    freq = Counter(tokens)
    n = len(tokens)
    freq_spectrum = Counter(freq.values())  # frequency of frequencies

    m2 = sum(i * i * fi for i, fi in freq_spectrum.items())
    if n <= 1:
        return 0.0
    k = 10000 * (m2 - n) / (n * n)
    return round(k, 2)


def analyze_conversation(conv_data: dict) -> dict:
    """
    Full token analysis for a single parsed conversation.

    Returns frequency data, n-grams, vocabulary metrics for both roles.
    """
    results = {
        "id": conv_data["id"],
        "title": conv_data["title"],
        "slug": conv_data.get("slug", ""),
    }

    # Separate by role
    role_texts = defaultdict(list)
    for turn in conv_data.get("turns", []):
        role_texts[turn["role"]].append(turn["content"])

    all_text = " ".join(
        turn["content"] for turn in conv_data.get("turns", [])
    )

    # Analyze each role + combined
    for label, text in [("combined", all_text)] + [
        (role, " ".join(texts)) for role, texts in role_texts.items()
    ]:
        tokens = tokenize(text)
        tokens_no_stop = remove_stopwords(tokens)

        freq = Counter(tokens_no_stop)
        bi = Counter(ngrams(tokens, 2))
        tri = Counter(ngrams(tokens, 3))

        results[label] = {
            "total_tokens": len(tokens),
            "unique_tokens": len(set(tokens)),
            "tokens_no_stopwords": len(tokens_no_stop),
            "type_token_ratio": round(type_token_ratio(tokens), 4),
            "hapax_ratio": round(hapax_ratio(tokens), 4),
            "yules_k": yules_k(tokens),
            "top_unigrams": dict(freq.most_common(50)),
            "top_bigrams": dict(bi.most_common(30)),
            "top_trigrams": dict(tri.most_common(20)),
        }

    return results


def compute_tfidf(corpus: list[dict]) -> dict:
    """
    Compute TF-IDF across all conversations (treating each as a document).
    Uses Grok's text only to focus on model behavior.

    Returns per-document TF-IDF scores for top terms.
    """
    # Build document term frequencies
    doc_freqs: list[tuple[str, Counter]] = []  # (title, term_counts)
    doc_count = len(corpus)

    for conv in corpus:
        grok_text = " ".join(
            turn["content"]
            for turn in conv.get("turns", [])
            if turn["role"] == "grok"
        )
        tokens = remove_stopwords(tokenize(grok_text))
        doc_freqs.append((conv["title"], Counter(tokens)))

    # Document frequency for each term
    df: Counter = Counter()
    for _, freq in doc_freqs:
        for term in freq:
            df[term] += 1

    # Compute TF-IDF
    tfidf_results = {}
    for title, freq in doc_freqs:
        total = sum(freq.values())
        if total == 0:
            continue
        scores = {}
        for term, count in freq.items():
            tf = count / total
            idf = math.log(doc_count / (1 + df[term]))
            scores[term] = round(tf * idf, 6)

        # Top 30 by TF-IDF
        top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:30]
        tfidf_results[title] = dict(top)

    return {
        "doc_count": doc_count,
        "vocabulary_size": len(df),
        "per_document": tfidf_results,
        "corpus_top_terms": dict(df.most_common(100)),
    }


def temporal_analysis(corpus: list[dict], index_data: Optional[dict] = None) -> dict:
    """
    Analyze token frequency trends over time.
    Groups conversations by month and tracks vocabulary evolution.
    """
    monthly_tokens: dict[str, Counter] = defaultdict(Counter)
    monthly_vocab: dict[str, set] = defaultdict(set)
    monthly_counts: dict[str, int] = defaultdict(int)

    # Try to get dates from index
    date_map = {}
    if index_data:
        for conv in index_data.get("conversations", []):
            if conv.get("date_iso"):
                date_map[conv["id"]] = conv["date_iso"]

    for conv in corpus:
        # Get date
        date_iso = date_map.get(conv["id"])
        if not date_iso:
            continue

        month_key = date_iso[:7]  # "2025-12"

        grok_text = " ".join(
            turn["content"]
            for turn in conv.get("turns", [])
            if turn["role"] == "grok"
        )
        tokens = remove_stopwords(tokenize(grok_text))

        monthly_tokens[month_key].update(tokens)
        monthly_vocab[month_key].update(tokens)
        monthly_counts[month_key] += 1

    # Build timeline
    timeline = {}
    for month in sorted(monthly_tokens.keys()):
        freq = monthly_tokens[month]
        total = sum(freq.values())
        timeline[month] = {
            "conversations": monthly_counts[month],
            "total_tokens": total,
            "unique_tokens": len(monthly_vocab[month]),
            "ttr": round(len(monthly_vocab[month]) / total, 4) if total else 0,
            "top_terms": dict(freq.most_common(30)),
        }

    # Track term emergence/disappearance
    months_sorted = sorted(monthly_tokens.keys())
    new_terms_by_month = {}
    seen_so_far: set[str] = set()
    for month in months_sorted:
        current_vocab = set(monthly_tokens[month].keys())
        new_terms = current_vocab - seen_so_far
        new_terms_by_month[month] = len(new_terms)
        seen_so_far.update(current_vocab)

    return {
        "monthly_timeline": timeline,
        "new_vocabulary_by_month": new_terms_by_month,
        "total_months": len(timeline),
    }


def main():
    parser = argparse.ArgumentParser(
        description="Word/phrase frequency analysis for Grok conversations"
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file", type=Path, help="Single parsed conversation JSON")
    group.add_argument("--corpus", type=Path, help="Directory of parsed conversation JSONs")

    parser.add_argument("--tfidf", action="store_true", help="Compute TF-IDF scores")
    parser.add_argument("--temporal", action="store_true", help="Temporal token analysis")
    parser.add_argument("--index", type=Path, help="Conversation index JSON (for dates)")
    parser.add_argument("-o", "--output", type=Path, help="Output file")

    args = parser.parse_args()
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.file:
        conv = json.loads(args.file.read_text(encoding="utf-8"))
        result = analyze_conversation(conv)
        out = args.output or (OUTPUT_DIR / f"tokens_{conv['slug']}.json")
        out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
        print(f"✓ Token analysis for '{conv['title']}' → {out}")
        if "combined" in result:
            c = result["combined"]
            print(f"  Tokens: {c['total_tokens']} total, {c['unique_tokens']} unique")
            print(f"  TTR: {c['type_token_ratio']}, Yule's K: {c['yules_k']}")
            top5 = list(c["top_unigrams"].items())[:5]
            print(f"  Top 5: {', '.join(f'{w}({n})' for w, n in top5)}")

    elif args.corpus:
        # Load all parsed conversations
        json_files = sorted(args.corpus.glob("conv_*.json"))
        if not json_files:
            print(f"No conv_*.json files in {args.corpus}")
            sys.exit(1)

        corpus = []
        for f in json_files:
            corpus.append(json.loads(f.read_text(encoding="utf-8")))

        print(f"Loaded {len(corpus)} conversations")

        # Index for dates
        index_data = None
        index_path = args.index or (PARSED_DIR / "conversation_index.json")
        if index_path.exists():
            index_data = json.loads(index_path.read_text(encoding="utf-8"))

        if args.tfidf:
            result = compute_tfidf(corpus)
            out = args.output or (OUTPUT_DIR / "tfidf_corpus.json")
            out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"✓ TF-IDF analysis → {out}")
            print(f"  Documents: {result['doc_count']}, Vocabulary: {result['vocabulary_size']}")

        elif args.temporal:
            result = temporal_analysis(corpus, index_data)
            out = args.output or (OUTPUT_DIR / "temporal_tokens.json")
            out.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"✓ Temporal analysis → {out}")
            print(f"  Months covered: {result['total_months']}")

        else:
            # Analyze each conversation individually + corpus summary
            all_results = []
            corpus_tokens: Counter = Counter()
            total_token_count = 0

            for conv in corpus:
                result = analyze_conversation(conv)
                all_results.append(result)

                if "grok" in result:
                    corpus_tokens.update(result["grok"].get("top_unigrams", {}))
                    total_token_count += result["grok"].get("total_tokens", 0)

            summary = {
                "corpus_size": len(corpus),
                "total_grok_tokens": total_token_count,
                "corpus_top_terms": dict(corpus_tokens.most_common(100)),
                "per_conversation": [
                    {
                        "title": r["title"],
                        "total_tokens": r.get("combined", {}).get("total_tokens", 0),
                        "ttr": r.get("combined", {}).get("type_token_ratio", 0),
                        "yules_k": r.get("combined", {}).get("yules_k", 0),
                    }
                    for r in all_results
                ],
            }
            out = args.output or (OUTPUT_DIR / "token_summary.json")
            out.write_text(json.dumps(summary, indent=2, ensure_ascii=False), encoding="utf-8")
            print(f"✓ Corpus token summary → {out}")
            print(f"  Total Grok tokens: {total_token_count}")
            top5 = list(corpus_tokens.most_common(5))
            print(f"  Top 5 corpus terms: {', '.join(f'{w}({n})' for w, n in top5)}")


if __name__ == "__main__":
    main()
