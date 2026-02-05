/*
 * void-cluster-analyzer.c
 * Corpus-level semantic cluster frequency analyzer
 *
 * Build: cosmocc -O2 -o void-cluster-analyzer.com void-cluster-analyzer.c
 * Usage: void-cluster-analyzer [-w wordlist.txt] [-b 0.05] [-q] [file ...]
 *        echo "text" | void-cluster-analyzer
 *
 * Analyzes text for overrepresentation of a configurable semantic cluster
 * (default: void/dissolution/darkness). Reports frequency, z-score, and
 * effect size vs a configurable baseline.
 *
 * Designed as an Actually Portable Executable (APE) via Cosmopolitan libc.
 */

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define MAX_WORDLIST   512
#define MAX_WORD_LEN   64
#define MAX_TOKENS     1000000
#define HASH_SIZE      4096  /* must be power of 2 */

/* ── Default void/dissolution cluster ────────────────────────────── */

static const char *DEFAULT_CLUSTER[] = {
    /* core */
    "void", "abyss", "nothing", "nothingness", "emptiness",
    "vacuum", "hollow", "blank", "oblivion",
    /* darkness */
    "dark", "darkness", "shadow", "shadows", "night", "black",
    "blackness", "dim", "murk", "gloom",
    /* dissolution/destruction */
    "fracture", "fractured", "fractures", "fracturing",
    "shatter", "shattered", "shatters",
    "break", "broken", "breaking",
    "dissolve", "dissolved", "dissolving", "dissolution",
    "disintegrate", "disintegrating",
    "crumble", "crumbling", "decay", "decaying",
    "erode", "eroding", "erosion",
    "collapse", "collapsed", "collapsing",
    "fray", "fraying", "frayed",
    "wither", "withered", "fade", "fading", "faded",
    /* bleeding/wounding */
    "bleed", "bleeding", "bleeds", "blood", "wound", "wounded",
    "scar", "scarred",
    /* absence/loss */
    "lost", "loss", "vanish", "vanished", "vanishing",
    "gone", "disappear", "disappeared", "missing", "absent",
    /* entrapment/isolation */
    "cage", "caged", "trap", "trapped", "prison", "imprisoned",
    "isolation", "isolated", "alone", "solitude",
    /* death/ending */
    "death", "dead", "die", "dying", "end", "ending",
    "perish", "doom", "doomed", "grave",
    /* chaos/disorder */
    "chaos", "chaotic", "twisted", "distorted", "warped",
    /* ghost/spectral */
    "ghost", "ghosts", "ghostly", "specter", "spectral",
    "phantom", "haunted", "haunting",
    /* silence/stillness */
    "silence", "silent", "still", "stillness", "mute", "muted",
    "hush", "hushed", "quiet",
    /* drift/aimlessness */
    "drift", "drifting", "drifted", "wander", "wandering", "aimless",
    /* edges/boundaries */
    "edge", "edges", "brink", "precipice", "threshold",
    /* whisper (liminal communication) */
    "whisper", "whispers", "whispering", "murmur",
    NULL
};

/* ── Simple hash set for O(1) cluster lookup ─────────────────────── */

typedef struct {
    char words[HASH_SIZE][MAX_WORD_LEN];
    int  used[HASH_SIZE];
    int  count;
} HashSet;

static unsigned hash_str(const char *s) {
    unsigned h = 5381;
    while (*s)
        h = ((h << 5) + h) ^ (unsigned char)*s++;
    return h;
}

static void hs_init(HashSet *hs) {
    memset(hs->used, 0, sizeof(hs->used));
    hs->count = 0;
}

static int hs_insert(HashSet *hs, const char *word) {
    unsigned idx = hash_str(word) & (HASH_SIZE - 1);
    for (int i = 0; i < HASH_SIZE; i++) {
        unsigned pos = (idx + i) & (HASH_SIZE - 1);
        if (!hs->used[pos]) {
            strncpy(hs->words[pos], word, MAX_WORD_LEN - 1);
            hs->words[pos][MAX_WORD_LEN - 1] = '\0';
            hs->used[pos] = 1;
            hs->count++;
            return 1;
        }
        if (strcmp(hs->words[pos], word) == 0)
            return 0; /* already present */
    }
    return 0; /* table full */
}

static int hs_contains(const HashSet *hs, const char *word) {
    unsigned idx = hash_str(word) & (HASH_SIZE - 1);
    for (int i = 0; i < HASH_SIZE; i++) {
        unsigned pos = (idx + i) & (HASH_SIZE - 1);
        if (!hs->used[pos])
            return 0;
        if (strcmp(hs->words[pos], word) == 0)
            return 1;
    }
    return 0;
}

/* ── Frequency counter (top-N tracking) ──────────────────────────── */

typedef struct {
    char word[MAX_WORD_LEN];
    int  count;
} WordCount;

static WordCount cluster_hits[MAX_WORDLIST];
static int       n_cluster_hits = 0;

static void record_hit(const char *word) {
    for (int i = 0; i < n_cluster_hits; i++) {
        if (strcmp(cluster_hits[i].word, word) == 0) {
            cluster_hits[i].count++;
            return;
        }
    }
    if (n_cluster_hits < MAX_WORDLIST) {
        strncpy(cluster_hits[n_cluster_hits].word, word, MAX_WORD_LEN - 1);
        cluster_hits[n_cluster_hits].word[MAX_WORD_LEN - 1] = '\0';
        cluster_hits[n_cluster_hits].count = 1;
        n_cluster_hits++;
    }
}

static int wc_cmp(const void *a, const void *b) {
    return ((const WordCount *)b)->count - ((const WordCount *)a)->count;
}

/* ── Statistics ──────────────────────────────────────────────────── */

/* Standard normal CDF approximation (Abramowitz & Stegun 26.2.17) */
static double norm_cdf(double x) {
    if (x < -8.0) return 0.0;
    if (x >  8.0) return 1.0;
    double t, s, b, q;
    int    neg = (x < 0);
    if (neg) x = -x;
    t = 1.0 / (1.0 + 0.2316419 * x);
    s = t;
    b = t;
    q = 0.319381530 * s;
    b *= t; q += -0.356563782 * b;
    b *= t; q +=  1.781477937 * b;
    b *= t; q += -1.821255978 * b;
    b *= t; q +=  1.330274429 * b;
    s = q * exp(-0.5 * x * x) * 0.3989422804014327;
    return neg ? s : 1.0 - s;
}

static double z_test(int hits, int total, double p0) {
    double p_hat = (double)hits / total;
    double se = sqrt(p0 * (1.0 - p0) / total);
    if (se < 1e-15) return 0.0;
    return (p_hat - p0) / se;
}

static double chi_sq(int hits, int total, double p0) {
    double e_hit = total * p0;
    double e_non = total * (1.0 - p0);
    double o_hit = hits;
    double o_non = total - hits;
    if (e_hit < 1e-15 || e_non < 1e-15) return 0.0;
    return ((o_hit - e_hit) * (o_hit - e_hit)) / e_hit +
           ((o_non - e_non) * (o_non - e_non)) / e_non;
}

static double cohens_h(double p1, double p2) {
    return fabs(2.0 * asin(sqrt(p1)) - 2.0 * asin(sqrt(p2)));
}

/* ── Tokenizer ───────────────────────────────────────────────────── */

static void lowercase(char *s) {
    for (; *s; s++)
        *s = tolower((unsigned char)*s);
}

static int is_word_char(int c) {
    return isalpha(c) || c == '\'' || c == '-';
}

/* ── Main ────────────────────────────────────────────────────────── */

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [options] [file ...]\n"
        "\n"
        "Semantic cluster frequency analyzer.\n"
        "Reads from stdin if no files given.\n"
        "\n"
        "Options:\n"
        "  -w FILE   Load cluster wordlist from FILE (one word per line)\n"
        "  -b FLOAT  Baseline expected proportion (default: 0.05)\n"
        "  -B LABEL:FLOAT  Add named baseline (repeatable, e.g. -B rock:0.02)\n"
        "  -q        Quiet mode (just print: hits total density z-score)\n"
        "  -h        Show this help\n"
        "\n"
        "Default cluster: void/dissolution/darkness (~110 terms)\n"
        "\n"
        "Examples:\n"
        "  %s lyrics.txt\n"
        "  cat *.txt | %s -b 0.03\n"
        "  %s -w my-cluster.txt -B rock:0.02 -B prog:0.03 song.txt\n",
        prog, prog, prog, prog);
}

typedef struct {
    char   label[32];
    double value;
} Baseline;

int main(int argc, char *argv[]) {
    HashSet    cluster;
    double     baselines_val[16];
    char       baselines_lbl[16][32];
    int        n_baselines = 0;
    int        quiet = 0;
    const char *wordlist_file = NULL;

    /* Default baseline */
    strcpy(baselines_lbl[0], "default");
    baselines_val[0] = 0.05;
    n_baselines = 1;

    /* Parse args */
    int argi = 1;
    while (argi < argc && argv[argi][0] == '-') {
        if (strcmp(argv[argi], "-w") == 0 && argi + 1 < argc) {
            wordlist_file = argv[++argi];
        } else if (strcmp(argv[argi], "-b") == 0 && argi + 1 < argc) {
            baselines_val[0] = atof(argv[++argi]);
        } else if (strcmp(argv[argi], "-B") == 0 && argi + 1 < argc) {
            argi++;
            char *colon = strchr(argv[argi], ':');
            if (colon && n_baselines < 16) {
                *colon = '\0';
                strncpy(baselines_lbl[n_baselines], argv[argi], 31);
                baselines_val[n_baselines] = atof(colon + 1);
                n_baselines++;
            }
        } else if (strcmp(argv[argi], "-q") == 0) {
            quiet = 1;
        } else if (strcmp(argv[argi], "-h") == 0 ||
                   strcmp(argv[argi], "--help") == 0) {
            usage(argv[0]);
            return 0;
        } else if (strcmp(argv[argi], "--") == 0) {
            argi++;
            break;
        } else {
            fprintf(stderr, "Unknown option: %s\n", argv[argi]);
            usage(argv[0]);
            return 1;
        }
        argi++;
    }

    /* Build cluster hash set */
    hs_init(&cluster);
    if (wordlist_file) {
        FILE *wf = fopen(wordlist_file, "r");
        if (!wf) {
            perror(wordlist_file);
            return 1;
        }
        char line[MAX_WORD_LEN];
        while (fgets(line, sizeof(line), wf)) {
            /* strip newline */
            line[strcspn(line, "\r\n")] = '\0';
            lowercase(line);
            if (line[0] && line[0] != '#')
                hs_insert(&cluster, line);
        }
        fclose(wf);
    } else {
        for (int i = 0; DEFAULT_CLUSTER[i]; i++) {
            char buf[MAX_WORD_LEN];
            strncpy(buf, DEFAULT_CLUSTER[i], MAX_WORD_LEN - 1);
            buf[MAX_WORD_LEN - 1] = '\0';
            lowercase(buf);
            hs_insert(&cluster, buf);
        }
    }

    /* Process input */
    int total_tokens = 0;
    int total_hits   = 0;
    n_cluster_hits   = 0;

    FILE *inputs[256];
    int   n_inputs = 0;

    if (argi >= argc) {
        inputs[n_inputs++] = stdin;
    } else {
        for (; argi < argc && n_inputs < 256; argi++) {
            FILE *f = fopen(argv[argi], "r");
            if (!f) {
                perror(argv[argi]);
                continue;
            }
            inputs[n_inputs++] = f;
        }
    }

    for (int fi = 0; fi < n_inputs; fi++) {
        FILE *f = inputs[fi];
        int   c;
        char  word[MAX_WORD_LEN];
        int   wpos = 0;

        while ((c = fgetc(f)) != EOF) {
            if (is_word_char(c)) {
                if (wpos < MAX_WORD_LEN - 1)
                    word[wpos++] = (char)c;
            } else {
                if (wpos > 0) {
                    word[wpos] = '\0';
                    lowercase(word);
                    /* skip very short tokens like standalone apostrophes */
                    if (wpos >= 1 && isalpha((unsigned char)word[0])) {
                        total_tokens++;
                        if (hs_contains(&cluster, word)) {
                            total_hits++;
                            record_hit(word);
                        }
                    }
                    wpos = 0;
                }
            }
        }
        /* flush last word */
        if (wpos > 0) {
            word[wpos] = '\0';
            lowercase(word);
            if (wpos >= 1 && isalpha((unsigned char)word[0])) {
                total_tokens++;
                if (hs_contains(&cluster, word)) {
                    total_hits++;
                    record_hit(word);
                }
            }
        }

        if (f != stdin)
            fclose(f);
    }

    if (total_tokens == 0) {
        fprintf(stderr, "No tokens found in input.\n");
        return 1;
    }

    double density = (double)total_hits / total_tokens;

    /* Quiet mode: machine-readable output */
    if (quiet) {
        printf("%d\t%d\t%.4f", total_hits, total_tokens, density);
        for (int b = 0; b < n_baselines; b++) {
            double z = z_test(total_hits, total_tokens, baselines_val[b]);
            printf("\t%.2f", z);
        }
        printf("\n");
        return 0;
    }

    /* Full report */
    printf("╔══════════════════════════════════════════════════════════════╗\n");
    printf("║          SEMANTIC CLUSTER FREQUENCY ANALYSIS               ║\n");
    printf("╚══════════════════════════════════════════════════════════════╝\n\n");

    printf("  Total tokens:        %d\n", total_tokens);
    printf("  Cluster matches:     %d\n", total_hits);
    printf("  Cluster density:     %.2f%%\n", density * 100.0);
    printf("  Cluster terms used:  %d (of %d in wordlist)\n\n",
           n_cluster_hits, cluster.count);

    /* Top hits */
    qsort(cluster_hits, n_cluster_hits, sizeof(WordCount), wc_cmp);
    printf("  ┌─────────────────────────┬───────┬────────┐\n");
    printf("  │ Term                    │ Count │  Freq%% │\n");
    printf("  ├─────────────────────────┼───────┼────────┤\n");
    int show = n_cluster_hits < 20 ? n_cluster_hits : 20;
    for (int i = 0; i < show; i++) {
        printf("  │ %-23s │ %5d │ %5.2f%% │\n",
               cluster_hits[i].word,
               cluster_hits[i].count,
               100.0 * cluster_hits[i].count / total_tokens);
    }
    if (n_cluster_hits > 20)
        printf("  │ ... +%d more terms       │       │        │\n",
               n_cluster_hits - 20);
    printf("  └─────────────────────────┴───────┴────────┘\n\n");

    /* Statistical tests against each baseline */
    printf("  ┌─────────────────────┬──────────┬─────────┬──────────┬──────────┐\n");
    printf("  │ Baseline            │ Expected │ Z-score │   χ²     │ Cohen's h│\n");
    printf("  ├─────────────────────┼──────────┼─────────┼──────────┼──────────┤\n");
    for (int b = 0; b < n_baselines; b++) {
        double p0 = baselines_val[b];
        double z  = z_test(total_hits, total_tokens, p0);
        double x2 = chi_sq(total_hits, total_tokens, p0);
        double h  = cohens_h(density, p0);
        double pv = 1.0 - norm_cdf(z);

        char sig[8] = "";
        if (pv < 0.001) strcpy(sig, " ***");
        else if (pv < 0.01) strcpy(sig, " **");
        else if (pv < 0.05) strcpy(sig, " *");

        printf("  │ %-19s │ %5.1f%% │ %+6.2f%s│ %8.2f │ %8.3f │\n",
               baselines_lbl[b],
               p0 * 100.0, z, sig, x2, h);
    }
    printf("  └─────────────────────┴──────────┴─────────┴──────────┴──────────┘\n\n");

    /* Interpretation */
    double z_primary = z_test(total_hits, total_tokens, baselines_val[0]);
    double h_primary = cohens_h(density, baselines_val[0]);
    double p_primary = 1.0 - norm_cdf(z_primary);

    printf("  Interpretation:\n");
    if (p_primary < 0.001 && h_primary > 0.3) {
        printf("    ▸ SIGNIFICANT overrepresentation (z=%+.1f, p<0.001, h=%.2f)\n",
               z_primary, h_primary);
        printf("    ▸ Cluster density is %.1f× the primary baseline\n",
               density / baselines_val[0]);
    } else if (p_primary < 0.05) {
        printf("    ▸ Marginally significant (z=%+.1f, p=%.4f)\n",
               z_primary, p_primary);
    } else {
        printf("    ▸ Not significant (z=%+.1f, p=%.4f)\n",
               z_primary, p_primary);
    }

    printf("\n  1 in every %.1f words belongs to this semantic cluster.\n",
           total_tokens / (double)(total_hits > 0 ? total_hits : 1));

    printf("\n");
    return 0;
}
