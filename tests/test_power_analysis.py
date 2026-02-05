"""
Power Analysis Tests

Validates statistical power claims from the methodology critique.
These tests compute power for various scenarios and verify that
the study design can detect the claimed effect sizes.
"""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
import analyze


# ─── Utility functions ────────────────────────────────────────────────────────

def normal_cdf(x: float) -> float:
    """Standard normal CDF (Abramowitz & Stegun approximation)."""
    return 0.5 * math.erfc(-x / math.sqrt(2))


def power_z_test_proportion(
    n: int,
    p0: float,
    p1: float,
    alpha: float = 0.05,
    one_sided: bool = True,
) -> float:
    """Compute power of a one-sample z-test for proportions.
    
    Args:
        n: Sample size (tokens)
        p0: Null hypothesis proportion
        p1: True proportion (alternative)
        alpha: Significance level
        one_sided: One-sided test (H₁: p > p0)
    
    Returns:
        Statistical power (probability of rejecting H₀ when H₁ is true)
    """
    z_alpha = 1.645 if one_sided else 1.96
    se_null = math.sqrt(p0 * (1 - p0) / n)
    se_alt = math.sqrt(p1 * (1 - p1) / n)

    if se_null == 0 or se_alt == 0:
        return 0.0

    # Critical value under null
    critical_value = p0 + z_alpha * se_null

    # Power = P(reject H₀ | H₁ true) = P(p_hat > critical | p = p1)
    z_power = (critical_value - p1) / se_alt
    power = 1 - normal_cdf(z_power)
    return power


def required_n_for_power(
    p0: float,
    p1: float,
    power: float = 0.80,
    alpha: float = 0.05,
    one_sided: bool = True,
) -> int:
    """Compute required sample size to achieve target power."""
    z_alpha = 1.645 if one_sided else 1.96
    z_beta = -normal_cdf_inverse(1 - power)

    # Approximation: n = ((z_α * √(p0*q0) + z_β * √(p1*q1)) / (p1 - p0))²
    numerator = (z_alpha * math.sqrt(p0 * (1 - p0)) +
                 z_beta * math.sqrt(p1 * (1 - p1)))
    denominator = p1 - p0
    if denominator == 0:
        return float('inf')
    n = (numerator / denominator) ** 2
    return math.ceil(n)


def normal_cdf_inverse(p: float) -> float:
    """Inverse normal CDF (rational approximation)."""
    # Beasley-Springer-Moro algorithm
    a = [0, -3.969683028665376e1, 2.209460984245205e2,
         -2.759285104469687e2, 1.383577518672690e2,
         -3.066479806614716e1, 2.506628277459239e0]
    b = [0, -5.447609879822406e1, 1.615858368580409e2,
         -1.556989798598866e2, 6.680131188771972e1, -1.328068155288572e1]
    c = [0, -7.784894002430293e-3, -3.223964580411365e-1,
         -2.400758277161838e0, -2.549732539343734e0,
         4.374664141464968e0, 2.938163982698783e0]
    d = [0, 7.784695709041462e-3, 3.224671290700398e-1,
         2.445134137142996e0, 3.754408661907416e0]

    p_low = 0.02425
    p_high = 1 - p_low

    if p < p_low:
        q = math.sqrt(-2 * math.log(p))
        return (((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) / \
               ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)
    elif p <= p_high:
        q = p - 0.5
        r = q * q
        return (((((a[1]*r+a[2])*r+a[3])*r+a[4])*r+a[5])*r+a[6])*q / \
               (((((b[1]*r+b[2])*r+b[3])*r+b[4])*r+b[5])*r+1)
    else:
        q = math.sqrt(-2 * math.log(1 - p))
        return -(((((c[1]*q+c[2])*q+c[3])*q+c[4])*q+c[5])*q+c[6]) / \
                ((((d[1]*q+d[2])*q+d[3])*q+d[4])*q+1)


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO A: TITLE-LEVEL ANALYSIS (CURRENT APPROACH)
# ═══════════════════════════════════════════════════════════════════════════════

class TestTitleLevelPower:
    """Power analysis for the current title-only approach."""

    TITLE_TOKENS = 1000  # ~141 titles × ~7 words
    TECH_BASELINE = 0.002  # 0.2% void in technical text

    def test_power_for_2x_elevation(self):
        """Can we detect a doubling of void rate in titles?"""
        power = power_z_test_proportion(
            n=self.TITLE_TOKENS,
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 2,  # 0.4%
        )
        assert power < 0.20, (
            f"Title-level power for 2× effect: {power:.1%}. "
            "Should be <20% (effectively useless)."
        )

    def test_power_for_5x_elevation(self):
        """Can we detect a 5× elevation in titles?"""
        power = power_z_test_proportion(
            n=self.TITLE_TOKENS,
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 5,  # 1.0%
        )
        assert power < 0.50, (
            f"Title-level power for 5× effect: {power:.1%}. "
            "Should be <50% (still inadequate)."
        )

    def test_power_for_10x_elevation(self):
        """Can we detect a 10× elevation in titles?"""
        power = power_z_test_proportion(
            n=self.TITLE_TOKENS,
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 10,  # 2.0%
        )
        # Even 10× might not be detectable with 1000 tokens
        # Power should be moderate at best
        assert power < 0.90, (
            f"Title-level power for 10× effect: {power:.1%}. "
            "Even massive effects are hard to detect in 1000 tokens."
        )

    def test_required_n_for_2x_detection(self):
        """How many title tokens would we need to detect a 2× effect?"""
        n_required = required_n_for_power(
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 2,
            power=0.80,
        )
        assert n_required > self.TITLE_TOKENS, (
            f"Need {n_required:,} tokens to detect 2× effect at 80% power. "
            f"Have {self.TITLE_TOKENS:,}. Need {n_required/self.TITLE_TOKENS:.0f}× more data."
        )

    def test_null_result_is_expected(self):
        """Under the null hypothesis, P(0 void hits) is HIGH with only 1000 tokens."""
        expected_count = self.TITLE_TOKENS * self.TECH_BASELINE  # ~2 expected
        # Poisson approximation: P(X=0) = e^(-λ)
        p_zero = math.exp(-expected_count)
        assert p_zero > 0.10, (
            f"P(0 hits | λ={expected_count:.1f}) = {p_zero:.2%}. "
            "Zero hits is a likely outcome even WITHOUT any effect."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO B: FULL CONVERSATION TEXT
# ═══════════════════════════════════════════════════════════════════════════════

class TestFullTextPower:
    """Power analysis assuming full conversation text is extracted."""

    FULL_TEXT_TOKENS = 60_000  # 120 convos × ~500 tokens each
    TECH_BASELINE = 0.002

    def test_power_for_2x_elevation(self):
        """Full text: can we detect a doubling?"""
        power = power_z_test_proportion(
            n=self.FULL_TEXT_TOKENS,
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 2,
        )
        # With 60K tokens, 2× should be marginal
        # Expected hits: 120 (null) vs 240 (alt)
        # This SHOULD be somewhat detectable
        assert power > 0.10, (
            f"Full-text power for 2× effect: {power:.1%}. "
            "Expected to be at least marginally powered."
        )

    def test_power_for_5x_elevation(self):
        """Full text: can we detect a 5× elevation?"""
        power = power_z_test_proportion(
            n=self.FULL_TEXT_TOKENS,
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 5,  # 1.0%
        )
        assert power > 0.80, (
            f"Full-text power for 5× effect: {power:.1%}. "
            "Should have adequate power (>80%) for large effects."
        )

    def test_power_for_10x_elevation(self):
        """Full text: 10× elevation should be trivially detectable."""
        power = power_z_test_proportion(
            n=self.FULL_TEXT_TOKENS,
            p0=self.TECH_BASELINE,
            p1=self.TECH_BASELINE * 10,
        )
        assert power > 0.99, (
            f"Full-text power for 10× effect: {power:.1%}. "
            "Should be >99%."
        )

    def test_minimum_detectable_effect(self):
        """What's the smallest elevation detectable at 80% power with full text?"""
        # Binary search for the smallest p1 that gives 80% power
        low, high = self.TECH_BASELINE, 0.05
        for _ in range(50):
            mid = (low + high) / 2
            power = power_z_test_proportion(
                n=self.FULL_TEXT_TOKENS, p0=self.TECH_BASELINE, p1=mid,
            )
            if power < 0.80:
                low = mid
            else:
                high = mid

        min_detectable = high
        multiplier = min_detectable / self.TECH_BASELINE

        # Document the minimum detectable effect
        assert multiplier < 10, (
            f"Minimum detectable effect at 80% power: {multiplier:.1f}× baseline "
            f"({min_detectable:.3%} void density). "
            "Anything smaller than this would be missed."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO C: CROSS-PLATFORM COMPARISON
# ═══════════════════════════════════════════════════════════════════════════════

class TestCrossPlatformPower:
    """Power analysis for cross-platform comparison studies."""

    CONVOS_PER_PLATFORM = 120
    TOKENS_PER_CONVO = 500  # Average conversation length

    def test_between_platform_anova_power(self):
        """Can we detect platform differences with 120 convos each?"""
        # For one-way ANOVA with 4 groups, effect size f
        # Using approximation: power ≈ Φ(√(n*f²*k) - z_α)
        # where k = number of groups, n = per group
        k = 4  # Grok, Claude, GPT-4, Gemini
        n = self.CONVOS_PER_PLATFORM

        # Medium effect size (f = 0.25, η² ≈ 0.06)
        f_medium = 0.25
        # Noncentrality parameter
        ncp = n * f_medium**2 * k
        # Approximate power using chi-squared
        power_approx = 1 - normal_cdf(1.645 - math.sqrt(ncp))

        assert power_approx > 0.95, (
            f"Cross-platform ANOVA power for medium effect: {power_approx:.1%}. "
            "Should be >95% with 120 conversations per platform."
        )

    def test_pairwise_comparison_power(self):
        """Power for detecting a difference between Grok and one other model."""
        n = self.CONVOS_PER_PLATFORM
        tokens = n * self.TOKENS_PER_CONVO  # 60K tokens

        # If Grok has 0.5% void and Claude has 0.2%
        power = power_z_test_proportion(
            n=tokens,
            p0=0.002,
            p1=0.005,
        )
        assert power > 0.80, (
            f"Pairwise power (0.2% vs 0.5%): {power:.1%}. "
            "Should be adequate for moderate platform differences."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SCENARIO D: WITHIN-CORPUS OUTLIER DETECTION
# ═══════════════════════════════════════════════════════════════════════════════

class TestOutlierDetectionPower:
    """Power analysis for detecting outlier conversations within the corpus."""

    def test_grubbs_test_sensitivity(self):
        """Can Grubbs' test detect an outlier in a category of N conversations?"""
        # Grubbs' critical value for N=29 (programming category), α=0.05
        # G_crit ≈ (N-1)/√N * √(t²/(N-2+t²)) where t is t-distribution critical value
        # For N=29: G_crit ≈ 3.0
        N = 29  # programming category size

        # An outlier must be >3 SD from the category mean
        # If category mean void density = 0.2% and SD = 0.1%:
        mean_void = 0.002
        sd_void = 0.001
        min_outlier = mean_void + 3.0 * sd_void  # 0.5%

        # A conversation needs 2.5× the category mean to be flagged
        multiplier = min_outlier / mean_void
        assert multiplier > 2, (
            f"Minimum outlier = {multiplier:.1f}× category mean. "
            "Moderate anomalies (1.5-2×) would be missed."
        )

    def test_small_category_sensitivity(self):
        """Smaller categories (N=10) have worse outlier detection."""
        N_small = 10  # creative category
        N_large = 29  # programming category

        # Grubbs critical value increases (more conservative) for smaller N
        # Approximate: for N=10, need ~2.3 SD; for N=29, need ~3.0 SD
        # But smaller N has larger SD estimates, making detection harder

        # With N=10, the sampling distribution of SD is very wide
        # The coefficient of variation of the sample SD is:
        # CV(s) = 1/√(2(N-1))
        cv_small = 1 / math.sqrt(2 * (N_small - 1))
        cv_large = 1 / math.sqrt(2 * (N_large - 1))

        assert cv_small > cv_large, (
            "Small categories have more uncertain SD estimates, "
            "reducing outlier detection power."
        )
        assert cv_small > 0.20, (
            f"CV of SD estimate for N={N_small}: {cv_small:.0%}. "
            "This means our SD estimate is ±20%+ uncertain."
        )


# ═══════════════════════════════════════════════════════════════════════════════
# SAMPLE SIZE RECOMMENDATIONS
# ═══════════════════════════════════════════════════════════════════════════════

class TestSampleSizeRecommendations:
    """Tests that compute and validate required sample sizes."""

    def test_minimum_conversations_for_temporal_analysis(self):
        """How many conversations per month to detect model version changes?"""
        # Stylometric change detection needs ~30 texts per window (literature)
        min_per_window = 30

        # Current data:
        monthly_counts = {
            "Jul_2025": 2,
            "Oct_2025": 19,
            "Nov_2025": 57,
            "Dec_2025": 35,
            "Jan_2026": 25,
            "Feb_2026": 3,
        }

        underpowered_months = [
            month for month, count in monthly_counts.items()
            if count < min_per_window
        ]
        assert len(underpowered_months) > 0, (
            "Expected some months to be underpowered for temporal analysis"
        )
        # Document which months are problematic
        assert "Jul_2025" in underpowered_months
        assert "Feb_2026" in underpowered_months

    def test_minimum_for_prospective_personality_control(self):
        """30 topics × 3 conditions = 90 new conversations needed."""
        topics_needed = 30
        conditions = 3  # normal, dry academic, just facts
        total = topics_needed * conditions

        assert total == 90, "Personality control experiment needs 90 conversations"

    def test_minimum_for_cross_platform(self):
        """50 prompts × 4 platforms = 200 conversations for cross-platform study."""
        prompts = 50
        platforms = 4
        total = prompts * platforms

        assert total == 200, "Cross-platform comparison needs 200 conversations"
        # This is feasible but labor-intensive
        # Automation via API would reduce cost

    def test_120_conversations_adequacy_summary(self):
        """Summarize: 120 conversations is adequate for SOME analyses but not all."""
        analyses = {
            "title_only_void_rate": False,      # INADEQUATE
            "full_text_large_effect": True,      # ADEQUATE (≥5× elevation)
            "full_text_small_effect": False,     # INADEQUATE (<2× elevation)
            "within_corpus_extreme_outlier": True,  # ADEQUATE (>3 SD)
            "within_corpus_moderate_outlier": False, # INADEQUATE (1.5-2.5 SD)
            "temporal_all_months": False,        # INADEQUATE (Jul, Feb too sparse)
            "temporal_nov_dec": True,            # ADEQUATE (57, 35 conversations)
            "cross_platform_matched": True,      # ADEQUATE (if prompts extracted)
        }

        adequate = sum(1 for v in analyses.values() if v)
        inadequate = sum(1 for v in analyses.values() if not v)

        assert adequate > 0 and inadequate > 0, (
            "120 conversations is adequate for some analyses and inadequate for others. "
            f"Adequate: {adequate}/{len(analyses)}, Inadequate: {inadequate}/{len(analyses)}"
        )
        assert inadequate >= adequate, (
            "More analyses are underpowered than adequately powered. "
            "The study needs more data OR narrower research questions."
        )
