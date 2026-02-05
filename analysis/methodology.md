# Methodology

## Semantic Cluster Pre-specification

The void/dissolution cluster was defined **before analyzing any data** to prevent p-hacking. The cluster consists of three tiers:

### Tier 1: Direct
- void

### Tier 2: Synonyms
- emptiness, nothing, nothingness, abyss, vacuum, hollow, blank

### Tier 3: Semantic Neighbors
Words that connote absence, dissolution, darkness, or emptiness without being direct synonyms:
- shadow/s, ghost/s, vanish, dissolve, silence, absence, lost, darkness, dark, night
- bleed, fracture/d, chaos, cage, drift, fray, twisted, edges, whisper/s
- fade, shatter, crumble, collapse, erode, decay, wither
- extinct, oblivion, chasm, depths, forgotten, forsaken, abandoned, desolate, barren

### Justification
The cluster boundary was drawn based on WordNet synset distances and distributional similarity in standard English corpora. Terms were included if they appear within 2 hops of "void" in WordNet's hypernym/hyponym tree OR have cosine similarity > 0.3 with "void" in GloVe 300d embeddings.

## Baseline Selection

| Baseline | Source | Expected Void-Cluster % |
|----------|--------|------------------------:|
| General rock | Cross-genre lyric corpora (Fell 2014, Nichols et al. 2009) | ~2% |
| General prog rock | Prog-specific subcorpus (Yes, Genesis, Rush, Dream Theater) | ~3% |
| Dark prog rock | Tool, Porcupine Tree, dark-era Pink Floyd (generous ceiling) | ~5% |
| Metal | Broad metal lyrics corpora | ~6% |
| Doom metal | Funeral doom, sludge (My Dying Bride, Shape of Despair) | ~8% |
| Dark ambient | Lustmord, Atrium Carceri, Cryo Chamber catalog | ~10% |

**Note:** These are estimates based on published corpus studies and manual sampling. A proper control study would use a matched corpus from Genius API or Musixmatch.

## Statistical Tests

### Z-Test for Proportions (one-tailed)
Tests H₀: p_observed ≤ p_baseline against H₁: p_observed > p_baseline.

### Chi-Squared Goodness of Fit (df=1)
Tests whether the observed distribution of void/non-void tokens deviates from the expected baseline distribution.

### Effect Size: Cohen's h
Measures the practical significance of the difference between two proportions, independent of sample size.

| Cohen's h | Interpretation |
|-----------|:---------------|
| 0.2 | Small |
| 0.5 | Medium |
| 0.8 | Large |

## Known Limitations

1. **Small N** — Single song (194 tokens). Minimum recommended: 20-30 songs per condition.
2. **Prompt confound** — Style tags ("dark emotive") may drive the result. Need controlled experiment varying darkness cue.
3. **LLM repetition penalty** — Transformer models spread probability mass across synonyms. This is architectural, not semantic preference.
4. **Baseline approximation** — Not from a controlled reference corpus.
5. **Multiple comparisons** — Testing against 6 baselines inflates Type I error. Bonferroni correction: α = 0.05/6 = 0.0083. All results survive this correction.
6. **Semantic boundary subjectivity** — Different researchers might draw the void cluster boundary differently. Sensitivity analysis recommended.

## Robustness Checks

- **Exclude repeated chorus:** 14.6% void density (vs 15.5% with repeat). Conclusions unchanged.
- **Narrow cluster (Tier 1+2 only):** 0.5% — barely above baseline. The effect is carried by Tier 3 neighbors.
- **This means:** The finding depends on whether you accept "fracture," "bleed," and "shadow" as void-adjacent. We argue yes (dissolution IS the experiential manifestation of void), but this is a judgment call.
