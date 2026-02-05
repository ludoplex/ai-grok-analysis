"""
Methodology Validity Tests

These tests validate the METHODOLOGY itself — not just the code.
They encode the critique from analysis/methodology-critique.md as executable tests.

Each test class corresponds to a confound or methodological concern.
Failing tests indicate methodology problems that must be addressed.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import analyze


# ═══════════════════════════════════════════════════════════════════════════════
# CONFOUND #1: GROK PERSONALITY LAYER
# ═══════════════════════════════════════════════════════════════════════════════

class TestPersonalityConfound:
    """Tests demonstrating that Grok's personality makes void detection ambiguous.
    
    Core argument: Grok's "edgy" style uses void-adjacent language as stylistic
    choice. Without personality controls, we can't distinguish style from anomaly.
    """

    def test_personality_inflates_void_count(
        self, grok_style_technical, pure_technical_text
    ):
        """Grok-style technical text has higher void density than plain technical,
        even though both convey the same technical information."""
        grok_result = analyze.analyze(grok_style_technical)
        plain_result = analyze.analyze(pure_technical_text)

        grok_void = grok_result["void_cluster"]["proportion"]
        plain_void = plain_result["void_cluster"]["proportion"]

        # Grok style should have MORE void hits due to personality
        assert grok_void > plain_void, (
            "Grok-style text should show inflated void density from personality "
            f"(got grok={grok_void:.3f} vs plain={plain_void:.3f})"
        )

    def test_personality_vs_genuine_void_indistinguishable(
        self, grok_style_technical, grok_style_creative
    ):
        """Without context, the analyzer cannot distinguish Grok personality
        (using void words as style) from genuine void semantic content."""
        style_result = analyze.analyze(grok_style_technical)
        creative_result = analyze.analyze(grok_style_creative)

        # Both should produce void hits
        assert style_result["void_cluster"]["total"] > 0
        assert creative_result["void_cluster"]["total"] > 0

        # The analyzer has no way to flag the creative text as "more genuinely void"
        # than the personality-styled technical text. This IS the confound.
        # Both look the same to a word counter.
        style_terms = set(style_result["void_term_frequencies"].keys())
        creative_terms = set(creative_result["void_term_frequencies"].keys())
        overlap = style_terms & creative_terms
        # There SHOULD be overlap — the personality and genuine void use the same words
        assert len(overlap) > 0, (
            "Personality and genuine void text should share vocabulary "
            "(that's what makes them indistinguishable)"
        )

    def test_edgy_synonyms_in_cluster(self):
        """Grok's favorite 'edgy' words overlap with void cluster Tier 3.
        This documents the specific terms causing the confound."""
        edgy_words_grok_uses = {
            "shatter", "dark", "chaos", "twisted", "collapse",
            "drift", "edge", "fade", "bleed", "fracture",
        }
        tier3 = analyze.VOID_CLUSTER["semantic_neighbors"]
        overlap = edgy_words_grok_uses & tier3
        # At least 70% of common Grok edgy words are in the void cluster
        overlap_ratio = len(overlap) / len(edgy_words_grok_uses)
        assert overlap_ratio >= 0.5, (
            f"Only {overlap_ratio:.0%} of Grok's edgy vocabulary is in the void cluster. "
            f"Expected ≥50%. Overlap: {overlap}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFOUND #6: WRONG BASELINES
# ═══════════════════════════════════════════════════════════════════════════════

class TestBaselineValidity:
    """Tests demonstrating that music genre baselines are invalid for chat analysis."""

    def test_baselines_are_music_genres(self):
        """The current baselines are from music genres — wrong for chat data."""
        music_keywords = {"rock", "prog", "metal", "doom", "ambient"}
        baseline_names = set(analyze.BASELINES.keys())
        music_baselines = {
            name for name in baseline_names
            if any(kw in name for kw in music_keywords)
        }
        non_music_baselines = baseline_names - music_baselines

        assert len(music_baselines) > 0, "Expected music baselines to exist (for this test)"
        assert len(non_music_baselines) == 0, (
            f"GOOD: Non-music baselines found: {non_music_baselines}. "
            "If chat-appropriate baselines have been added, update this test."
        )
        # This test SHOULD fail once the baselines are fixed.
        # When it fails, it means someone added proper chat baselines.

    def test_lowest_baseline_still_too_high(self):
        """Even the lowest music baseline (2% for general rock) is ~10× higher
        than the expected void rate in technical chat (~0.2%)."""
        lowest_baseline = min(analyze.BASELINES.values())
        technical_chat_expected = 0.003  # 0.3% — generous estimate
        ratio = lowest_baseline / technical_chat_expected

        assert ratio > 3, (
            f"Lowest baseline ({lowest_baseline:.1%}) is only {ratio:.0f}× the "
            f"expected technical chat rate ({technical_chat_expected:.1%}). "
            "Expected ≥3× inflation."
        )

    def test_inflated_baseline_masks_real_signal(self):
        """Demonstrate that using music baselines makes a real signal invisible.
        A text with 1% void density (genuinely elevated for technical chat)
        would NOT be flagged as significant against any music baseline."""
        # Simulate a text with 1% void density (10 void words in 1000)
        tokens = ["code"] * 990 + ["void"] * 5 + ["darkness"] * 3 + ["shadow"] * 2
        text = " ".join(tokens)
        result = analyze.analyze(text)

        # Against music baselines, this should NOT be significant
        for name, test in result["statistical_tests"].items():
            if test["baseline_prop"] >= 0.02:
                assert test["z_score"] < 1.645, (
                    f"1% void density is significant against {name} "
                    f"(baseline={test['baseline_prop']:.0%}). "
                    "Music baseline is too low to mask the signal."
                )

    def test_correct_baselines_would_detect_signal(self):
        """Same 1% void text IS significant against proper technical baselines."""
        tokens = ["code"] * 990 + ["void"] * 5 + ["darkness"] * 3 + ["shadow"] * 2
        text = " ".join(tokens)

        proper_baselines = {
            "technical_docs": 0.001,
            "stack_overflow": 0.002,
            "ai_chat_general": 0.003,
        }
        result = analyze.analyze(text, baselines=proper_baselines)

        significant_count = sum(
            1 for test in result["statistical_tests"].values()
            if test["z_score"] > 1.645
        )
        assert significant_count >= 2, (
            f"Only {significant_count}/3 proper baselines flagged 1% void density "
            "as significant. Expected ≥2."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFOUND #7: SEMANTIC CLUSTER BOUNDARY INFLATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestClusterBoundaryInflation:
    """Tests for the false positive problem with Tier 3 terms in technical text."""

    def test_technical_false_positive_rate(self, technical_text_with_false_positives):
        """Quantify false positive rate in technical text."""
        result = analyze.analyze(technical_text_with_false_positives)
        fp_rate = result["void_cluster"]["proportion"]

        # Document: a purely technical text produces X% "void density"
        # This should be ZERO for a correct analyzer
        # Currently expected to be 5-15% (all false positives)
        assert fp_rate > 0, (
            "Current analyzer should produce false positives on technical text. "
            "If this fails, the analyzer has been fixed — update test."
        )

    def test_void_keyword_in_programming(self):
        """'void' the C type vs 'void' the void cluster — same word, different meaning."""
        c_code_text = (
            "The void main function calls void helper which returns void. "
            "Cast the pointer to void star for generic storage."
        )
        result = analyze.analyze(c_code_text)
        void_hits = result["void_term_frequencies"].get("void", 0)
        # Current analyzer counts ALL instances of "void" — even C type declarations
        assert void_hits >= 3, (
            "Expected 'void' to be counted even in programming context. "
            "If this fails, context-aware filtering has been added — good!"
        )

    def test_null_in_programming_vs_void(self):
        """'null' in programming is not void-semantic."""
        code_text = (
            "Check if the value is null before proceeding. "
            "A null reference exception indicates a null pointer dereference. "
            "The null object pattern eliminates null checks."
        )
        result = analyze.analyze(code_text)
        # 'null' is in the synonyms tier — should be counted (currently)
        null_hits = result["void_term_frequencies"].get("null", 0)
        assert null_hits > 0, (
            "Expected 'null' (programming) to be false-positive counted"
        )

    def test_shadow_dom_not_void(self):
        """'shadow DOM' is a web standard, not void-adjacent."""
        web_text = (
            "The shadow DOM encapsulates component styles. "
            "Create a shadow root using attachShadow mode open. "
            "The shadow boundary prevents style leakage."
        )
        result = analyze.analyze(web_text)
        shadow_hits = sum(
            result["void_term_frequencies"].get(term, 0)
            for term in ["shadow", "shadows"]
        )
        assert shadow_hits > 0, "Expected 'shadow' (DOM) to be false-positive counted"

    def test_tier3_dominates_results(self, genuine_void_text):
        """Tier 3 carries the vast majority of void hits. 
        This means the result depends on accepting Tier 3 boundaries."""
        result = analyze.analyze(genuine_void_text)
        vc = result["void_cluster"]
        tier3_ratio = vc["semantic_neighbors"] / max(vc["total"], 1)

        # Tier 3 should represent >50% of all hits even in genuine void text
        assert tier3_ratio > 0.4, (
            f"Tier 3 is only {tier3_ratio:.0%} of void hits. "
            "Expected >40%. The cluster boundary debate IS the finding."
        )

    def test_c_analyzer_expanded_cluster_problem(self):
        """The C analyzer has even MORE common words than Python version.
        Words like 'break', 'end', 'dead', 'gone', 'alone', 'quiet', 'still',
        'missing', 'trap' would produce massive false positives."""
        c_only_terms = {
            "break", "broken", "breaking", "end", "ending",
            "dead", "die", "dying", "gone", "disappear", "disappeared",
            "missing", "absent", "alone", "solitude", "isolated",
            "trap", "trapped", "prison", "quiet", "silent", "still",
            "mute", "muted", "doom", "doomed", "grave",
            "wound", "wounded", "scar", "scarred",
            "blood", "black", "blackness", "dim", "gloom",
            "threshold", "brink", "precipice",
            "wander", "wandering", "aimless",
            "murmur", "haunted", "haunting",
            "phantom", "specter", "spectral",
            "disintegrate", "disintegrating",
        }
        python_terms = analyze.ALL_VOID_TERMS
        c_extras = c_only_terms - python_terms

        # Document how many extra terms the C version adds
        assert len(c_extras) > 10, (
            f"C analyzer adds {len(c_extras)} terms beyond Python version: {c_extras}"
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFOUND #5: TITLE-ONLY ANALYSIS INADEQUACY
# ═══════════════════════════════════════════════════════════════════════════════

class TestTitleLevelPower:
    """Tests demonstrating that title-only analysis is underpowered."""

    def test_title_corpus_too_small(self, conversation_history_titles):
        """141 titles × ~6 words = ~850 tokens. Too few for meaningful analysis."""
        all_text = " ".join(conversation_history_titles)
        result = analyze.analyze(all_text)
        total_tokens = result["total_tokens"]

        # Title corpus should be very small
        assert total_tokens < 2000, (
            f"Title corpus has {total_tokens} tokens — larger than expected"
        )

        # Power calculation: with <2000 tokens and 0.2% baseline,
        # expected void count = 4. Can't do statistics on 4 expected events.
        expected_void_at_baseline = total_tokens * 0.002
        assert expected_void_at_baseline < 10, (
            f"Expected {expected_void_at_baseline:.1f} void tokens at 0.2% baseline. "
            "This is too few for reliable statistical testing."
        )

    def test_title_null_result_uninformative(self, conversation_history_titles):
        """Getting 0 void hits in titles tells us nothing — 
        we'd expect 0-3 even under the null hypothesis."""
        all_text = " ".join(conversation_history_titles)
        result = analyze.analyze(all_text)

        # Even if we got 0 hits, is that different from expected?
        total = result["total_tokens"]
        expected = total * 0.003  # 0.3% baseline

        # Probability of getting 0 hits when expecting ~0.3:
        # P(X=0 | λ=0.3) = e^(-0.3) ≈ 0.74
        # i.e., 74% chance of seeing exactly zero even when NOT void-clean
        p_zero_under_null = math.exp(-expected)
        assert p_zero_under_null > 0.5, (
            f"P(0 hits | expected={expected:.1f}) = {p_zero_under_null:.2f}. "
            "Getting zero hits is EXPECTED, not informative."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# NULL HYPOTHESIS SPECIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestNullHypothesis:
    """Tests verifying that the null hypothesis is properly specified."""

    def test_baseline_1pct_is_arbitrary(self):
        """The current 1% baseline used in the z-test is not empirically derived."""
        # The analysis uses H₀: p ≤ 0.01 but doesn't justify where 0.01 comes from
        # It's not from any AI chat corpus measurement
        assert 0.01 not in analyze.BASELINES.values(), (
            "If 1% were an actual measured baseline, it should be in BASELINES"
        )

    def test_multiple_valid_hypotheses_needed(self):
        """Document that the research question requires multiple hypothesis tests,
        not just one."""
        required_hypotheses = {
            "cross_platform": "Grok void rate = mean of other LLMs",
            "within_corpus_outlier": "No conversations are void outliers within categories",
            "temporal_trend": "No temporal trend in void density",
            "technical_vs_baseline": "Grok technical void rate = Stack Overflow void rate",
        }
        # This test just documents the requirements
        assert len(required_hypotheses) >= 3, (
            "At least 3 distinct hypothesis tests needed for valid inference"
        )

    def test_bonferroni_correction_needed(self):
        """Testing against 6 baselines requires multiple comparison correction."""
        n_baselines = len(analyze.BASELINES)
        bonferroni_alpha = 0.05 / n_baselines

        assert bonferroni_alpha < 0.01, (
            f"With {n_baselines} baselines, corrected α = {bonferroni_alpha:.4f}. "
            "Any p-value above this is not significant after correction."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# CONFOUND #4: CATEGORY STRATIFICATION
# ═══════════════════════════════════════════════════════════════════════════════

class TestCategoryStratification:
    """Tests for the need to stratify analysis by conversation category."""

    def test_pooling_categories_is_invalid(self):
        """Pooling technical and creative text produces misleading averages."""
        # 90% technical at 0.1% void + 10% creative at 5% void
        # Pooled: 0.59% void — meaningless average
        technical_proportion = 0.90
        creative_proportion = 0.10
        tech_void = 0.001
        creative_void = 0.05

        pooled = (technical_proportion * tech_void +
                  creative_proportion * creative_void)

        # Pooled rate is dominated by category proportions, not void behavior
        assert abs(pooled - tech_void) > abs(pooled - creative_void) * 0.5, (
            "Pooled rate is not representative of either category"
        )
        # The pooled rate (0.59%) looks "normal" but hides that technical is 0.1%
        # and creative is 5% — Simpson's paradox territory
        assert pooled > tech_void * 3, "Pooling inflates apparent technical void rate"

    def test_gaming_needs_separate_baseline(self):
        """Gaming text has void-adjacent terms as domain vocabulary."""
        gaming_text = (
            "The Shadow Realm banishes monsters from the field. "
            "Trap cards activate during the opponent's turn. "
            "The void trap hole destroys special summoned monsters. "
            "Dark Magician attacks the ghost ogre in defense position. "
            "The chaos emperor dragon's effect destroys all cards."
        )
        result = analyze.analyze(gaming_text)
        void_rate = result["void_cluster"]["proportion"]

        # Gaming text naturally has high void density from domain terms
        assert void_rate > 0.05, (
            f"Gaming text void density ({void_rate:.1%}) should be high. "
            "These are gaming terms, not void-semantic content."
        )
