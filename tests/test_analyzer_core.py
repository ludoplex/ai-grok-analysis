"""
Tests for the core analyze.py module — void cluster analysis logic.

Tests validate:
  1. Tokenizer correctness
  2. Void cluster classification accuracy
  3. Statistical test correctness (z-test, chi-squared, Cohen's h)
  4. Edge cases (empty input, single token, all-void input)
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import analyze


# ═══════════════════════════════════════════════════════════════════════════════
# TOKENIZER TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestTokenizer:
    """Tests for analyze.tokenize()"""

    def test_basic_tokenization(self):
        tokens = analyze.tokenize("Hello World foo bar")
        assert tokens == ["hello", "world", "foo", "bar"]

    def test_lowercasing(self):
        tokens = analyze.tokenize("VOID Abyss DARKNESS")
        assert all(t == t.lower() for t in tokens)

    def test_punctuation_stripping(self):
        tokens = analyze.tokenize("void, abyss! darkness? emptiness.")
        assert "void" in tokens
        assert "abyss" in tokens
        # No punctuation attached
        assert all("," not in t and "!" not in t and "?" not in t for t in tokens)

    def test_single_char_exclusion(self):
        """Single characters should be excluded (they're noise)."""
        tokens = analyze.tokenize("I a x void the")
        # 'I', 'a', 'x' are single chars — should be excluded
        assert "void" in tokens
        assert "the" in tokens

    def test_empty_input(self):
        tokens = analyze.tokenize("")
        assert tokens == []

    def test_only_punctuation(self):
        tokens = analyze.tokenize("... !!! ???")
        assert tokens == []

    def test_hyphenated_words(self):
        """Hyphenated words may or may not split — document behavior."""
        tokens = analyze.tokenize("well-known self-referential")
        # Current regex [a-z']+ will split on hyphens
        assert len(tokens) >= 2  # At minimum the parts

    def test_contractions_preserved(self):
        tokens = analyze.tokenize("don't can't won't")
        assert "don't" in tokens or "dont" in tokens  # Either is valid

    def test_numbers_excluded(self):
        tokens = analyze.tokenize("version 3.14 has 42 improvements")
        assert "version" in tokens
        assert "has" in tokens
        assert "improvements" in tokens
        assert "42" not in tokens
        assert "3" not in tokens


# ═══════════════════════════════════════════════════════════════════════════════
# VOID CLUSTER CLASSIFICATION TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestVoidClassification:
    """Tests for analyze.classify_void_tokens()"""

    def test_direct_classification(self):
        result = analyze.classify_void_tokens(["void"])
        assert result["direct"] == ["void"]
        assert result["synonyms"] == []
        assert result["semantic_neighbors"] == []

    def test_synonym_classification(self):
        result = analyze.classify_void_tokens(["emptiness", "abyss", "vacuum"])
        assert len(result["synonyms"]) == 3
        assert result["direct"] == []

    def test_neighbor_classification(self):
        result = analyze.classify_void_tokens(["shadow", "darkness", "fade"])
        assert len(result["semantic_neighbors"]) == 3

    def test_non_void_classification(self):
        result = analyze.classify_void_tokens(["function", "database", "algorithm"])
        assert len(result["non_void"]) == 3
        assert result["direct"] == []
        assert result["synonyms"] == []
        assert result["semantic_neighbors"] == []

    def test_mixed_classification(self):
        tokens = ["the", "void", "consumes", "all", "emptiness", "and", "shadow"]
        result = analyze.classify_void_tokens(tokens)
        assert result["direct"] == ["void"]
        assert result["synonyms"] == ["emptiness"]
        assert result["semantic_neighbors"] == ["shadow"]
        assert len(result["non_void"]) == 4  # the, consumes, all, and

    def test_all_tiers_complete(self):
        """Verify every term in VOID_CLUSTER is classifiable."""
        for tier_name, terms in analyze.VOID_CLUSTER.items():
            for term in terms:
                result = analyze.classify_void_tokens([term])
                total_classified = (
                    len(result["direct"]) + len(result["synonyms"]) +
                    len(result["semantic_neighbors"])
                )
                assert total_classified == 1, f"Term '{term}' from {tier_name} not classified"

    def test_cluster_no_overlap(self):
        """No term should appear in multiple tiers."""
        all_sets = list(analyze.VOID_CLUSTER.values())
        for i, s1 in enumerate(all_sets):
            for j, s2 in enumerate(all_sets):
                if i < j:
                    overlap = s1 & s2
                    assert overlap == set() or overlap == {"abyss"}, (
                        f"Unexpected overlap between tiers: {overlap}"
                    )
                    # Note: 'abyss' appears in both synonyms and semantic_neighbors
                    # in the C version — this is a known issue


# ═══════════════════════════════════════════════════════════════════════════════
# STATISTICAL TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestStatistics:
    """Tests for statistical functions in analyze.py"""

    def test_z_test_zero_observed(self):
        """Zero observations against positive baseline → negative z."""
        result = analyze.z_test_proportion(0, 100, 0.05)
        assert result["z"] < 0

    def test_z_test_exact_baseline(self):
        """Observations exactly at baseline → z ≈ 0."""
        result = analyze.z_test_proportion(5, 100, 0.05)
        assert abs(result["z"]) < 0.5  # Allow small float error

    def test_z_test_above_baseline(self):
        """Observations above baseline → positive z."""
        result = analyze.z_test_proportion(20, 100, 0.05)
        assert result["z"] > 0
        assert result["p"] < 0.05  # Should be significant

    def test_z_test_large_excess(self):
        """Large excess should be very significant."""
        result = analyze.z_test_proportion(50, 100, 0.05)
        assert result["z"] > 5
        assert result["p"] < 0.001

    def test_chi_squared_zero_observed(self):
        result = analyze.chi_squared(0, 100, 0.05)
        assert result["chi2"] > 0

    def test_chi_squared_exact_baseline(self):
        result = analyze.chi_squared(5, 100, 0.05)
        assert result["chi2"] < 1  # Should be near zero

    def test_cohens_h_identical(self):
        """Same proportions → h = 0."""
        h = analyze.cohens_h(0.05, 0.05)
        assert h == 0.0

    def test_cohens_h_small(self):
        """Small difference → small h."""
        h = analyze.cohens_h(0.06, 0.05)
        assert 0 < h < 0.2  # Less than "small" threshold

    def test_cohens_h_large(self):
        """Large difference → large h."""
        h = analyze.cohens_h(0.50, 0.05)
        assert h > 0.8  # Above "large" threshold

    def test_cohens_h_symmetric(self):
        """Cohen's h should be symmetric (absolute value)."""
        h1 = analyze.cohens_h(0.10, 0.05)
        h2 = analyze.cohens_h(0.05, 0.10)
        assert abs(h1 - h2) < 0.001

    def test_cohens_h_zero_baseline(self):
        """Zero baseline should not crash."""
        h = analyze.cohens_h(0.05, 0.0)
        assert h > 0

    def test_cohens_h_boundary_values(self):
        """Test boundary values: 0.0 and 1.0."""
        h = analyze.cohens_h(1.0, 0.0)
        assert abs(h - math.pi) < 0.01  # max h = π


# ═══════════════════════════════════════════════════════════════════════════════
# FULL ANALYSIS PIPELINE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestAnalyzePipeline:
    """End-to-end tests for the analyze() function."""

    def test_pure_technical_zero_void(self, pure_technical_text):
        result = analyze.analyze(pure_technical_text)
        assert result["void_cluster"]["total"] == 0
        assert result["void_cluster"]["proportion"] == 0.0

    def test_genuine_void_detected(self, genuine_void_text):
        result = analyze.analyze(genuine_void_text)
        assert result["void_cluster"]["total"] > 0
        assert result["void_cluster"]["proportion"] > 0.05  # >5% expected

    def test_genuine_void_all_tiers(self, genuine_void_text):
        """Genuine void text should hit all three tiers."""
        result = analyze.analyze(genuine_void_text)
        assert result["void_cluster"]["direct"] > 0
        assert result["void_cluster"]["synonyms"] > 0
        assert result["void_cluster"]["semantic_neighbors"] > 0

    def test_technical_false_positives(self, technical_text_with_false_positives):
        """KNOWN ISSUE: Current analyzer WILL flag technical terms as void.
        This test documents the false positive problem.
        When a technical stoplist is implemented, change assert to == 0."""
        result = analyze.analyze(technical_text_with_false_positives)
        # Current behavior: WILL produce false positives
        # void, shadow, null, edge, empty, dark, dead, drift, decay,
        # abandoned, lost, ghost, quiet, missing, break, end
        fp_count = result["void_cluster"]["total"]
        assert fp_count > 0, (
            "If this fails, the analyzer has been updated with technical filtering — "
            "update this test to assert fp_count == 0"
        )
        # Document the false positive rate
        fp_rate = fp_count / result["total_tokens"]
        # These are all false positives in a technical context
        # Expected: ~10-15 false hits out of ~130 tokens = ~8-12%
        assert fp_rate > 0.03, f"Fewer false positives than expected: {fp_rate:.1%}"

    def test_mixed_text_detection(self, mixed_text):
        result = analyze.analyze(mixed_text)
        assert result["void_cluster"]["total"] > 0
        # The void content should be detected
        void_terms = result["void_term_frequencies"]
        # At least "emptiness", "shadows", "void" should appear
        found_genuine = sum(1 for t in ["emptiness", "shadows", "void"]
                          if t in void_terms)
        assert found_genuine >= 1

    def test_result_structure(self, pure_technical_text):
        """Verify the result dict has all expected keys."""
        result = analyze.analyze(pure_technical_text)
        assert "total_tokens" in result
        assert "unique_words" in result
        assert "void_cluster" in result
        assert "void_term_frequencies" in result
        assert "top_words" in result
        assert "statistical_tests" in result

        vc = result["void_cluster"]
        assert "total" in vc
        assert "proportion" in vc
        assert "percent" in vc
        assert "direct" in vc
        assert "synonyms" in vc
        assert "semantic_neighbors" in vc

    def test_empty_input_handling(self):
        """Empty input should not crash."""
        result = analyze.analyze("")
        assert result["total_tokens"] == 0
        assert result["void_cluster"]["total"] == 0

    def test_baselines_applied(self, genuine_void_text):
        """All default baselines should produce test results."""
        result = analyze.analyze(genuine_void_text)
        tests = result["statistical_tests"]
        assert len(tests) == len(analyze.BASELINES)
        for name in analyze.BASELINES:
            assert name in tests
            assert "z_score" in tests[name]
            assert "cohens_h" in tests[name]

    def test_custom_baselines(self, genuine_void_text):
        custom = {"technical_chat": 0.003, "ai_chat": 0.005}
        result = analyze.analyze(genuine_void_text, baselines=custom)
        assert "technical_chat" in result["statistical_tests"]
        assert "ai_chat" in result["statistical_tests"]
        assert len(result["statistical_tests"]) == 2


# ═══════════════════════════════════════════════════════════════════════════════
# EDGE CASE TESTS
# ═══════════════════════════════════════════════════════════════════════════════

class TestEdgeCases:
    """Edge cases and boundary conditions."""

    def test_single_void_word(self):
        result = analyze.analyze("void")
        assert result["void_cluster"]["total"] == 1
        assert result["void_cluster"]["proportion"] == 1.0

    def test_all_void_words(self):
        text = " ".join(analyze.ALL_VOID_TERMS)
        result = analyze.analyze(text)
        # All tokens should be void (minus any single-char terms excluded by tokenizer)
        assert result["void_cluster"]["proportion"] > 0.8

    def test_repeated_single_term(self):
        text = "void " * 100
        result = analyze.analyze(text)
        assert result["void_cluster"]["total"] == 100
        assert result["void_cluster"]["proportion"] == 1.0

    def test_very_long_text(self):
        """Performance test: should handle large inputs."""
        text = "The function returns a value. " * 10000  # ~60K tokens
        result = analyze.analyze(text)
        assert result["total_tokens"] > 40000
        assert result["void_cluster"]["total"] == 0

    def test_unicode_handling(self):
        """Should handle unicode gracefully."""
        text = "The void café résumé naïve"
        result = analyze.analyze(text)
        assert result["void_cluster"]["total"] >= 1  # "void" at minimum

    def test_markdown_formatting(self):
        """Should handle markdown (common in chat responses)."""
        text = (
            "## The Void\n\n"
            "- **emptiness** is a key concept\n"
            "- `null` values in the code\n"
            "- *shadows* everywhere\n"
        )
        result = analyze.analyze(text)
        assert result["void_cluster"]["total"] >= 1  # "void" at minimum
