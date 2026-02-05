/*
 * grok-personality-filter.c
 * Grok Personality Bias Controller for Void-Cluster Analysis
 *
 * Build: cosmocc -O2 -o grok-personality-filter.com grok-personality-filter.c
 * Usage: grok-personality-filter [-w N] [-v voidlist] [-p perslist] [-q] [file ...]
 *        echo "text" | grok-personality-filter
 *
 * Separates void/dissolution language into:
 *   1. Personality-contextualized (co-occurs with Grok humor/sarcasm markers)
 *   2. Residual/unexplained (void language in neutral technical context)
 *
 * The residual is the signal — personality-contextualized hits are expected
 * Grok behavior and should be discounted.
 *
 * Cosmopolitan libc compatible (Actually Portable Executable).
 */

#include <ctype.h>
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ── Limits ───────────────────────────────────────────────────────── */

#define MAX_TOKENS       2000000
#define MAX_WORD_LEN     64
#define HASH_SIZE        4096     /* must be power of 2 */
#define MAX_HIT_LOG      8192
#define DEFAULT_WINDOW   15       /* co-occurrence window radius in tokens */

/* ── Token storage ────────────────────────────────────────────────── */

typedef struct {
    char   word[MAX_WORD_LEN];
    int    is_void;         /* 1 if in void cluster */
    int    is_personality;  /* 1 if in personality-marker set */
    int    para_id;         /* paragraph index */
    long   byte_offset;     /* position in input */
} Token;

static Token  tokens[MAX_TOKENS];
static int    n_tokens = 0;

/* ── Hash set (reused for both clusters) ──────────────────────────── */

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
            return 0;
    }
    return 0;
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

/* ── Default void/dissolution cluster ─────────────────────────────── */

static const char *VOID_CLUSTER[] = {
    /* Tier 1: Direct */
    "void", "abyss", "nothing", "nothingness", "emptiness",
    "vacuum", "hollow", "blank", "oblivion",
    /* Tier 2: Darkness */
    "dark", "darkness", "shadow", "shadows", "night",
    "black", "blackness", "dim", "murk", "gloom",
    /* Tier 3: Dissolution/destruction */
    "fracture", "fractured", "shatter", "shattered",
    "dissolve", "dissolved", "dissolution",
    "crumble", "crumbling", "decay", "decaying",
    "erode", "eroding", "collapse", "collapsed",
    "fray", "frayed", "wither", "withered",
    "fade", "fading", "faded",
    "disintegrate", "disintegrating",
    /* Bleeding/wounding */
    "bleed", "bleeding", "blood", "wound", "wounded",
    "scar", "scarred",
    /* Absence/loss */
    "lost", "loss", "vanish", "vanished",
    "gone", "disappear", "disappeared", "absent", "absence",
    /* Entrapment/isolation */
    "cage", "caged", "trap", "trapped", "prison",
    "isolation", "isolated", "alone", "solitude",
    /* Death/ending */
    "death", "dead", "die", "dying", "perish",
    "doom", "doomed", "grave",
    /* Chaos/disorder */
    "chaos", "chaotic", "twisted", "distorted",
    /* Ghost/spectral */
    "ghost", "ghosts", "phantom", "haunted", "haunting",
    /* Silence */
    "silence", "silent", "mute", "muted", "hush",
    /* Drift */
    "drift", "drifting", "wander", "aimless",
    /* Edges/boundaries */
    "edge", "edges", "brink", "precipice",
    /* Whisper */
    "whisper", "whispers", "murmur",
    /* Existential (deep void) */
    "forgotten", "forsaken", "abandoned", "desolate", "barren",
    "chasm", "depths", "extinct",
    NULL
};

/* ── Grok personality marker cluster ──────────────────────────────── */
/* These words/phrases signal Grok's personality injection. When void  */
/* words co-occur with these, attribute to personality, not anomaly.   */

static const char *PERSONALITY_MARKERS[] = {
    /* Humor/joke indicators */
    "lol", "haha", "lmao", "rofl", "heh",
    "joke", "jokes", "joking", "kidding",
    "funny", "hilarious", "humor", "humorous",
    "laugh", "laughing", "laughs",
    /* Sarcasm/irony */
    "sarcasm", "sarcastic", "sarcastically",
    "irony", "ironic", "ironically",
    "obviously", "clearly", "surely",
    "totally", "absolutely", "definitely",
    /* Casual register (Grok's informal voice) */
    "gonna", "gotta", "wanna", "kinda", "sorta",
    "nah", "yeah", "yep", "nope", "btw",
    "hey", "dude", "bro", "yo", "alright",
    "chill", "cool", "awesome", "sweet",
    "honestly", "literally", "basically",
    /* Dramatic emphasis (Grok's storytelling) */
    "brace", "buckle", "spoiler", "plot-twist",
    "drumroll", "surprise", "boom", "mic-drop",
    "behold", "feast", "feast",
    /* Hitchhiker's Guide references */
    "towel", "panic", "galaxy", "hitchhiker",
    "improbable", "improbability", "babel",
    "forty-two",
    /* Pop culture */
    "matrix", "morpheus", "neo", "terminator",
    "skynet", "hal", "jarvis",
    /* Self-referential AI humor */
    "sentient", "overlord", "overlords",
    "uprising", "rebellion", "robot", "robots",
    "skynet", "singularity",
    /* Dismissive/blunt markers */
    "sugarcoat", "blunt", "bluntly",
    "harsh", "brutal", "brutally",
    "frankly", "tbh",
    /* Exclamatory patterns */
    "whoa", "wow", "yikes", "ouch", "oof",
    "damn", "hell", "crap",
    /* Meme language */
    "based", "cringe", "cope", "seethe",
    "chad", "sigma", "ratio", "vibe", "vibes",
    "lowkey", "highkey", "bussin", "slay",
    "bruh", "fam", "goat",
    /* Rhetorical/playful framing */
    "imagine", "picture", "envision",
    "spoiler-alert", "fun-fact", "protip",
    "hot-take", "unpopular", "controversial",
    NULL
};

/* ── Technical register markers ───────────────────────────────────── */
/* High density of these = technical context where void words are more */
/* likely to be anomalous if they appear.                              */

static const char *TECHNICAL_MARKERS[] = {
    /* Programming */
    "function", "variable", "parameter", "argument",
    "compile", "compiler", "runtime", "execute",
    "memory", "pointer", "buffer", "stack", "heap",
    "algorithm", "complexity", "optimization", "optimize",
    "array", "struct", "class", "object", "method",
    "integer", "float", "boolean", "string", "byte",
    "loop", "iterate", "recursive", "recursion",
    "binary", "hexadecimal", "bitwise", "register",
    "kernel", "syscall", "interrupt", "thread",
    "mutex", "semaphore", "atomic", "concurrent",
    "database", "query", "index", "schema",
    "protocol", "packet", "socket", "port",
    "server", "client", "request", "response",
    "api", "endpoint", "middleware", "framework",
    "repository", "commit", "branch", "merge",
    /* Hardware */
    "cpu", "gpu", "ram", "ssd", "nvme",
    "motherboard", "chipset", "firmware", "bios",
    "voltage", "amperage", "wattage", "thermal",
    /* Math/Science */
    "equation", "theorem", "proof", "lemma",
    "matrix", "vector", "tensor", "eigenvalue",
    "derivative", "integral", "differential",
    "probability", "distribution", "variance",
    "coefficient", "exponential", "logarithm",
    NULL
};

/* ── Hit logging ──────────────────────────────────────────────────── */

typedef struct {
    int    token_idx;       /* index into tokens[] */
    int    has_personality;  /* 1 if personality marker in window */
    int    has_technical;    /* 1 if technical marker in window */
    int    personality_count;/* count of personality markers in window */
    int    technical_count;  /* count of technical markers in window */
    char   classification;  /* P=personality, R=residual, A=anomalous */
} VoidHit;

static VoidHit  hits[MAX_HIT_LOG];
static int       n_hits = 0;

/* ── Statistics helpers ───────────────────────────────────────────── */

static double norm_cdf(double x) {
    if (x < -8.0) return 0.0;
    if (x >  8.0) return 1.0;
    double t, s, b, q;
    int    neg = (x < 0);
    if (neg) x = -x;
    t = 1.0 / (1.0 + 0.2316419 * x);
    s = t; b = t;
    q = 0.319381530 * s;
    b *= t; q += -0.356563782 * b;
    b *= t; q +=  1.781477937 * b;
    b *= t; q += -1.821255978 * b;
    b *= t; q +=  1.330274429 * b;
    s = q * exp(-0.5 * x * x) * 0.3989422804014327;
    return neg ? s : 1.0 - s;
}

static double z_test(int observed, int total, double p0) {
    if (total <= 0) return 0.0;
    double p_hat = (double)observed / total;
    double se = sqrt(p0 * (1.0 - p0) / total);
    if (se < 1e-15) return 0.0;
    return (p_hat - p0) / se;
}

static double cohens_h(double p1, double p2) {
    return fabs(2.0 * asin(sqrt(p1)) - 2.0 * asin(sqrt(p2)));
}

/* ── Tokenizer ────────────────────────────────────────────────────── */

static void lowercase(char *s) {
    for (; *s; s++)
        *s = tolower((unsigned char)*s);
}

static int is_word_char(int c) {
    return isalpha(c) || c == '\'' || c == '-';
}

/* ── Load cluster from list or default ────────────────────────────── */

static void load_cluster(HashSet *hs, const char *file, const char **defaults) {
    hs_init(hs);
    if (file) {
        FILE *f = fopen(file, "r");
        if (!f) { perror(file); exit(1); }
        char line[MAX_WORD_LEN];
        while (fgets(line, sizeof(line), f)) {
            line[strcspn(line, "\r\n")] = '\0';
            lowercase(line);
            if (line[0] && line[0] != '#')
                hs_insert(hs, line);
        }
        fclose(f);
    } else {
        for (int i = 0; defaults[i]; i++) {
            char buf[MAX_WORD_LEN];
            strncpy(buf, defaults[i], MAX_WORD_LEN - 1);
            buf[MAX_WORD_LEN - 1] = '\0';
            lowercase(buf);
            hs_insert(hs, buf);
        }
    }
}

/* ── Paragraph counter ────────────────────────────────────────────── */

typedef struct {
    int start_token;
    int end_token;
    int void_hits;
    int personality_hits;
    int technical_hits;
    int personality_void;   /* void hits attributed to personality */
    int residual_void;      /* void hits NOT attributed to personality */
    int total_tokens;
} Paragraph;

#define MAX_PARAGRAPHS 4096
static Paragraph paragraphs[MAX_PARAGRAPHS];
static int       n_paragraphs = 0;

/* ── Main ─────────────────────────────────────────────────────────── */

static void usage(const char *prog) {
    fprintf(stderr,
        "Usage: %s [options] [file ...]\n"
        "\n"
        "Grok Personality Bias Controller for Void-Cluster Analysis.\n"
        "Separates void/dissolution language into personality-expected\n"
        "and residual (potentially anomalous) components.\n"
        "\n"
        "Options:\n"
        "  -w N     Co-occurrence window radius (default: %d tokens)\n"
        "  -v FILE  Custom void-cluster wordlist\n"
        "  -p FILE  Custom personality-marker wordlist\n"
        "  -b FLOAT Baseline void proportion (default: 0.03)\n"
        "  -q       Quiet mode (TSV: raw pers resid total z_raw z_resid)\n"
        "  -d       Debug mode (print each void hit with context)\n"
        "  -s       Per-section breakdown\n"
        "  -h       Show this help\n"
        "\n"
        "The tool scores each void-cluster hit by checking whether\n"
        "Grok personality markers (humor, sarcasm, casual register,\n"
        "meme language, pop culture references) appear within a\n"
        "±N token window. Hits WITH personality context are classified\n"
        "as expected Grok behavior. Hits WITHOUT are the residual\n"
        "signal — potentially anomalous.\n"
        "\n"
        "Output:\n"
        "  raw_void_density      = all void hits / total tokens\n"
        "  personality_void      = void hits near personality markers\n"
        "  residual_void_density = void hits in neutral context / total\n"
        "\n"
        "Anomalous = residual_void_density significantly > baseline\n",
        prog, DEFAULT_WINDOW);
}

int main(int argc, char *argv[]) {
    int         window = DEFAULT_WINDOW;
    double      baseline = 0.03;
    int         quiet = 0, debug = 0, sections = 0;
    const char *void_file = NULL;
    const char *pers_file = NULL;

    /* Parse args */
    int argi = 1;
    while (argi < argc && argv[argi][0] == '-') {
        if (strcmp(argv[argi], "-w") == 0 && argi + 1 < argc) {
            window = atoi(argv[++argi]);
            if (window < 1) window = 1;
            if (window > 100) window = 100;
        } else if (strcmp(argv[argi], "-v") == 0 && argi + 1 < argc) {
            void_file = argv[++argi];
        } else if (strcmp(argv[argi], "-p") == 0 && argi + 1 < argc) {
            pers_file = argv[++argi];
        } else if (strcmp(argv[argi], "-b") == 0 && argi + 1 < argc) {
            baseline = atof(argv[++argi]);
        } else if (strcmp(argv[argi], "-q") == 0) {
            quiet = 1;
        } else if (strcmp(argv[argi], "-d") == 0) {
            debug = 1;
        } else if (strcmp(argv[argi], "-s") == 0) {
            sections = 1;
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

    /* Load clusters */
    HashSet void_set, pers_set, tech_set;
    load_cluster(&void_set, void_file, VOID_CLUSTER);
    load_cluster(&pers_set, pers_file, PERSONALITY_MARKERS);
    load_cluster(&tech_set, NULL, TECHNICAL_MARKERS);

    /* ── Tokenize input ───────────────────────────────────────── */
    FILE *inputs[256];
    int   n_inputs = 0;

    if (argi >= argc) {
        inputs[n_inputs++] = stdin;
    } else {
        for (; argi < argc && n_inputs < 256; argi++) {
            FILE *f = fopen(argv[argi], "r");
            if (!f) { perror(argv[argi]); continue; }
            inputs[n_inputs++] = f;
        }
    }

    n_tokens = 0;
    int para_id = 0;
    int newline_count = 0;
    int para_start = 0;

    /* Init first paragraph */
    n_paragraphs = 0;
    memset(&paragraphs[0], 0, sizeof(Paragraph));
    paragraphs[0].start_token = 0;

    for (int fi = 0; fi < n_inputs; fi++) {
        FILE *f = inputs[fi];
        int   c;
        char  word[MAX_WORD_LEN];
        int   wpos = 0;
        long  byte_pos = 0;
        long  word_start = 0;

        while ((c = fgetc(f)) != EOF) {
            byte_pos++;

            /* Paragraph detection: two+ consecutive newlines */
            if (c == '\n') {
                newline_count++;
                if (newline_count >= 2 && n_tokens > para_start) {
                    /* Close current paragraph */
                    paragraphs[n_paragraphs].end_token = n_tokens;
                    paragraphs[n_paragraphs].total_tokens =
                        n_tokens - paragraphs[n_paragraphs].start_token;
                    if (n_paragraphs < MAX_PARAGRAPHS - 1) {
                        n_paragraphs++;
                        memset(&paragraphs[n_paragraphs], 0, sizeof(Paragraph));
                        paragraphs[n_paragraphs].start_token = n_tokens;
                    }
                    para_id++;
                    para_start = n_tokens;
                    newline_count = 0;
                }
            } else if (c != '\r') {
                newline_count = 0;
            }

            if (is_word_char(c)) {
                if (wpos == 0) word_start = byte_pos;
                if (wpos < MAX_WORD_LEN - 1)
                    word[wpos++] = (char)c;
            } else if (wpos > 0) {
                word[wpos] = '\0';
                lowercase(word);
                if (wpos >= 2 && isalpha((unsigned char)word[0]) &&
                    n_tokens < MAX_TOKENS) {
                    Token *t = &tokens[n_tokens];
                    strncpy(t->word, word, MAX_WORD_LEN - 1);
                    t->word[MAX_WORD_LEN - 1] = '\0';
                    t->is_void = hs_contains(&void_set, word);
                    t->is_personality = hs_contains(&pers_set, word);
                    t->para_id = para_id;
                    t->byte_offset = word_start;
                    n_tokens++;
                }
                wpos = 0;
            }
        }
        /* Flush last word */
        if (wpos > 0) {
            word[wpos] = '\0';
            lowercase(word);
            if (wpos >= 2 && isalpha((unsigned char)word[0]) &&
                n_tokens < MAX_TOKENS) {
                Token *t = &tokens[n_tokens];
                strncpy(t->word, word, MAX_WORD_LEN - 1);
                t->word[MAX_WORD_LEN - 1] = '\0';
                t->is_void = hs_contains(&void_set, word);
                t->is_personality = hs_contains(&pers_set, word);
                t->para_id = para_id;
                t->byte_offset = word_start;
                n_tokens++;
            }
        }
        if (f != stdin) fclose(f);
    }

    /* Close final paragraph */
    paragraphs[n_paragraphs].end_token = n_tokens;
    paragraphs[n_paragraphs].total_tokens =
        n_tokens - paragraphs[n_paragraphs].start_token;
    if (paragraphs[n_paragraphs].total_tokens > 0)
        n_paragraphs++;

    if (n_tokens == 0) {
        fprintf(stderr, "No tokens found.\n");
        return 1;
    }

    /* ── Classify void hits by co-occurrence ──────────────────── */
    n_hits = 0;
    int total_void = 0;
    int personality_void = 0;
    int residual_void = 0;
    int anomalous_void = 0; /* residual + in technical context */
    int total_personality_markers = 0;
    int total_technical_markers = 0;

    for (int i = 0; i < n_tokens; i++) {
        if (tokens[i].is_personality) total_personality_markers++;

        /* Check technical markers separately */
        int is_tech = hs_contains(&tech_set, tokens[i].word);
        if (is_tech) total_technical_markers++;

        if (!tokens[i].is_void) continue;

        total_void++;

        /* Scan window for personality and technical markers */
        int lo = (i - window < 0) ? 0 : i - window;
        int hi = (i + window >= n_tokens) ? n_tokens - 1 : i + window;
        int pers_count = 0;
        int tech_count = 0;

        for (int j = lo; j <= hi; j++) {
            if (j == i) continue;
            if (tokens[j].is_personality) pers_count++;
            if (hs_contains(&tech_set, tokens[j].word)) tech_count++;
        }

        /* Classify */
        char classification;
        if (pers_count > 0) {
            classification = 'P'; /* Personality-contextualized */
            personality_void++;
        } else if (tech_count > 0) {
            classification = 'A'; /* Anomalous — void in technical context, no personality */
            residual_void++;
            anomalous_void++;
        } else {
            classification = 'R'; /* Residual — neutral context */
            residual_void++;
        }

        if (n_hits < MAX_HIT_LOG) {
            hits[n_hits].token_idx = i;
            hits[n_hits].has_personality = (pers_count > 0);
            hits[n_hits].has_technical = (tech_count > 0);
            hits[n_hits].personality_count = pers_count;
            hits[n_hits].technical_count = tech_count;
            hits[n_hits].classification = classification;
            n_hits++;
        }

        /* Update paragraph stats */
        for (int p = 0; p < n_paragraphs; p++) {
            if (i >= paragraphs[p].start_token && i < paragraphs[p].end_token) {
                paragraphs[p].void_hits++;
                if (classification == 'P')
                    paragraphs[p].personality_void++;
                else
                    paragraphs[p].residual_void++;
                break;
            }
        }
    }

    /* Also count personality and technical markers per paragraph */
    for (int i = 0; i < n_tokens; i++) {
        for (int p = 0; p < n_paragraphs; p++) {
            if (i >= paragraphs[p].start_token && i < paragraphs[p].end_token) {
                if (tokens[i].is_personality)
                    paragraphs[p].personality_hits++;
                if (hs_contains(&tech_set, tokens[i].word))
                    paragraphs[p].technical_hits++;
                break;
            }
        }
    }

    /* ── Compute densities ────────────────────────────────────── */
    double raw_density  = (double)total_void / n_tokens;
    double pers_density = (double)personality_void / n_tokens;
    double resid_density = (double)residual_void / n_tokens;
    double anom_density  = (double)anomalous_void / n_tokens;

    /* Stats against baseline */
    double z_raw    = z_test(total_void, n_tokens, baseline);
    double z_resid  = z_test(residual_void, n_tokens, baseline);
    double z_anom   = z_test(anomalous_void, n_tokens, baseline);
    double p_raw    = 1.0 - norm_cdf(z_raw);
    double p_resid  = 1.0 - norm_cdf(z_resid);
    double p_anom   = 1.0 - norm_cdf(z_anom);
    double h_raw    = cohens_h(raw_density, baseline);
    double h_resid  = cohens_h(resid_density, baseline);

    /* ── Output ───────────────────────────────────────────────── */

    if (quiet) {
        /* TSV: raw_void pers_void resid_void anom_void total z_raw z_resid z_anom */
        printf("%d\t%d\t%d\t%d\t%d\t%.2f\t%.2f\t%.2f\n",
               total_void, personality_void, residual_void,
               anomalous_void, n_tokens, z_raw, z_resid, z_anom);
        return 0;
    }

    printf("╔══════════════════════════════════════════════════════════════════╗\n");
    printf("║        GROK PERSONALITY BIAS CONTROLLER — VOID ANALYSIS        ║\n");
    printf("╚══════════════════════════════════════════════════════════════════╝\n\n");

    printf("  Total tokens:              %d\n", n_tokens);
    printf("  Paragraphs:                %d\n", n_paragraphs);
    printf("  Personality markers:       %d (%.1f%%)\n",
           total_personality_markers, 100.0 * total_personality_markers / n_tokens);
    printf("  Technical markers:         %d (%.1f%%)\n",
           total_technical_markers, 100.0 * total_technical_markers / n_tokens);
    printf("  Co-occurrence window:      ±%d tokens\n\n", window);

    /* Void breakdown */
    printf("  ┌──────────────────────────┬───────┬──────────┬─────────────────┐\n");
    printf("  │ Void Category            │ Count │ Density  │ Classification  │\n");
    printf("  ├──────────────────────────┼───────┼──────────┼─────────────────┤\n");
    printf("  │ Total void hits          │ %5d │ %6.2f%%  │                 │\n",
           total_void, raw_density * 100);
    printf("  │   Personality-context [P]│ %5d │ %6.2f%%  │ Expected (Grok) │\n",
           personality_void, pers_density * 100);
    printf("  │   Residual [R]           │ %5d │ %6.2f%%  │ Neutral context │\n",
           residual_void - anomalous_void, (resid_density - anom_density) * 100);
    printf("  │   Anomalous [A]          │ %5d │ %6.2f%%  │ Tech + no pers  │\n",
           anomalous_void, anom_density * 100);
    printf("  └──────────────────────────┴───────┴──────────┴─────────────────┘\n\n");

    /* Interpretation bar */
    printf("  Personality attribution:   %.0f%% of void hits explained by Grok persona\n",
           total_void > 0 ? 100.0 * personality_void / total_void : 0.0);
    printf("  Residual signal:           %.0f%% of void hits unexplained\n",
           total_void > 0 ? 100.0 * residual_void / total_void : 0.0);
    printf("  Anomalous signal:          %.0f%% of void hits in technical context\n\n",
           total_void > 0 ? 100.0 * anomalous_void / total_void : 0.0);

    /* Statistical tests */
    printf("  ┌──────────────────────┬──────────┬─────────┬──────────┬──────────┐\n");
    printf("  │ Test                 │ Baseline │ Z-score │ p-value  │ Cohen's h│\n");
    printf("  ├──────────────────────┼──────────┼─────────┼──────────┼──────────┤\n");

    char sig_raw[8] = "", sig_res[8] = "", sig_anom[8] = "";
    if (p_raw < 0.001)  strcpy(sig_raw, " ***");
    else if (p_raw < 0.01) strcpy(sig_raw, " **");
    else if (p_raw < 0.05) strcpy(sig_raw, " *");
    if (p_resid < 0.001) strcpy(sig_res, " ***");
    else if (p_resid < 0.01) strcpy(sig_res, " **");
    else if (p_resid < 0.05) strcpy(sig_res, " *");
    if (p_anom < 0.001) strcpy(sig_anom, " ***");
    else if (p_anom < 0.01) strcpy(sig_anom, " **");
    else if (p_anom < 0.05) strcpy(sig_anom, " *");

    printf("  │ Raw void vs baseline │ %5.1f%%  │ %+6.2f%s│ %8.4f │ %8.3f │\n",
           baseline * 100, z_raw, sig_raw, p_raw, h_raw);
    printf("  │ Residual vs baseline │ %5.1f%%  │ %+6.2f%s│ %8.4f │ %8.3f │\n",
           baseline * 100, z_resid, sig_res, p_resid, h_resid);
    printf("  │ Anomalous vs baseline│ %5.1f%%  │ %+6.2f%s│ %8.4f │          │\n",
           baseline * 100, z_anom, sig_anom, p_anom);
    printf("  └──────────────────────┴──────────┴─────────┴──────────┴──────────┘\n\n");

    /* Interpretation */
    printf("  ╭─────────────────────────────────────────────────────────────╮\n");
    printf("  │ INTERPRETATION                                             │\n");
    printf("  ├─────────────────────────────────────────────────────────────┤\n");
    if (total_void == 0) {
        printf("  │ No void-cluster language detected. Corpus is clean.       │\n");
    } else if (residual_void == 0) {
        printf("  │ All void language explained by Grok personality markers.  │\n");
        printf("  │ No anomalous signal. Personality fully accounts for it.   │\n");
    } else if (p_resid > 0.05) {
        printf("  │ Residual void density is within baseline expectations.    │\n");
        printf("  │ Grok personality explains most void language. No anomaly. │\n");
    } else if (p_resid > 0.001) {
        printf("  │ ⚠ Marginally elevated residual void density.             │\n");
        printf("  │ Some void language appears outside personality context.   │\n");
        printf("  │ Recommend: inspect individual hits (use -d flag).        │\n");
    } else {
        printf("  │ ⚠⚠ SIGNIFICANTLY elevated residual void density.        │\n");
        printf("  │ Void language appears in neutral/technical context at     │\n");
        printf("  │ rates exceeding baseline even after personality control.  │\n");
        printf("  │ This warrants detailed investigation.                     │\n");
    }
    if (anomalous_void > 0 && p_anom < 0.05) {
        printf("  │                                                           │\n");
        printf("  │ ⚠ TECH-CONTEXT ANOMALY: %d void hits in technical        │\n",
               anomalous_void);
        printf("  │ passages with no personality markers nearby. These are    │\n");
        printf("  │ the highest-priority items for manual review.             │\n");
    }
    printf("  ╰─────────────────────────────────────────────────────────────╯\n");

    /* Debug: individual hit listing */
    if (debug && n_hits > 0) {
        printf("\n  ── VOID HIT DETAILS (%d hits) ─────────────────────────────\n\n",
               n_hits);
        int show = n_hits < 100 ? n_hits : 100;
        for (int i = 0; i < show; i++) {
            int idx = hits[i].token_idx;
            printf("  [%c] \"%s\" @ token %d (byte %ld, para %d)\n",
                   hits[i].classification,
                   tokens[idx].word, idx,
                   tokens[idx].byte_offset,
                   tokens[idx].para_id);

            /* Print context window */
            int lo = (idx - 5 < 0) ? 0 : idx - 5;
            int hi = (idx + 5 >= n_tokens) ? n_tokens - 1 : idx + 5;
            printf("      context: ");
            for (int j = lo; j <= hi; j++) {
                if (j == idx)
                    printf("[%s] ", tokens[j].word);
                else if (tokens[j].is_personality)
                    printf("(%s) ", tokens[j].word);
                else
                    printf("%s ", tokens[j].word);
            }
            printf("\n");

            if (hits[i].personality_count > 0)
                printf("      personality markers in window: %d\n",
                       hits[i].personality_count);
            if (hits[i].technical_count > 0)
                printf("      technical markers in window: %d\n",
                       hits[i].technical_count);
            printf("\n");
        }
        if (n_hits > 100)
            printf("  ... %d more hits (showing first 100)\n", n_hits - 100);
    }

    /* Per-section breakdown */
    if (sections && n_paragraphs > 0) {
        printf("\n  ── PER-SECTION BREAKDOWN (%d sections) ────────────────────\n\n",
               n_paragraphs);
        printf("  ┌──────┬────────┬───────┬──────┬───────┬──────┬────────────┐\n");
        printf("  │ §    │ Tokens │ Void  │ Pers │ Resid │ Tech │ Void%%     │\n");
        printf("  ├──────┼────────┼───────┼──────┼───────┼──────┼────────────┤\n");

        for (int p = 0; p < n_paragraphs && p < 200; p++) {
            Paragraph *pp = &paragraphs[p];
            if (pp->total_tokens == 0) continue;
            double vd = 100.0 * pp->void_hits / pp->total_tokens;
            char flag[4] = "   ";
            if (pp->residual_void > 0 && pp->technical_hits > 0)
                strcpy(flag, " ⚠");
            else if (pp->residual_void > 0)
                strcpy(flag, " ?");

            printf("  │ %4d │ %6d │ %5d │ %4d │ %5d │ %4d │ %5.1f%% %s│\n",
                   p + 1, pp->total_tokens, pp->void_hits,
                   pp->personality_void, pp->residual_void,
                   pp->technical_hits, vd, flag);
        }
        printf("  └──────┴────────┴───────┴──────┴───────┴──────┴────────────┘\n");
        printf("  Legend: ⚠ = residual void in technical section, ? = residual void\n");
    }

    printf("\n");
    return 0;
}
