# Contributing to ai-grok-analysis

Thanks for your interest in contributing! This project analyzes Grok chat sessions for statistical outliers in void/dissolution semantic clusters. Contributions that improve methodology, add data, or strengthen the analysis pipeline are welcome.

## Quick Start

```bash
# Clone
git clone https://github.com/ludoplex/ai-grok-analysis.git
cd ai-grok-analysis

# Setup
make setup

# Run smoke tests
make test

# Run full analysis
make all
```

## What We Need

### High Priority

- **Conversation text extraction** — We have 141 session titles but need full conversation text for response-level analysis. See Priority A/B/C lists in `analysis/grok-pattern-analysis.md`.
- **Cross-platform comparison data** — Matched conversations from Claude, ChatGPT, or other AI platforms on the same technical topics.
- **Baseline corpus expansion** — Technical writing samples to strengthen our null baseline.

### Medium Priority

- **Statistical methodology review** — Peer review of z-test and chi-squared approaches in `analysis/methodology.md`.
- **Additional semantic clusters** — Beyond void/dissolution, what other unexpected semantic fields might appear?
- **Temporal resolution** — Day-of-week and time-of-day analysis (requires timestamp extraction).

### Always Welcome

- Bug fixes in analysis scripts
- CI/CD improvements
- Documentation improvements
- Reproducibility enhancements

## Development Workflow

### Branch Strategy

```
main (protected)
├── feat/description    — new features
├── data/description    — new data additions
├── fix/description     — bug fixes
└── analysis/description — methodology changes
```

### Making Changes

1. **Fork** the repository
2. **Branch** from `main`: `git checkout -b feat/my-feature`
3. **Make changes** — keep commits focused
4. **Test locally**: `make lint && make test`
5. **Push** and open a PR against `main`

### PR Checklist

- [ ] `make lint` passes
- [ ] `make test` passes
- [ ] New scripts have docstrings and `--help`
- [ ] Data changes include methodology notes
- [ ] Analysis changes document assumptions

## Project Structure

```
ai-grok-analysis/
├── .github/
│   ├── workflows/
│   │   ├── analyze.yml        — void-cluster analysis on push/PR
│   │   ├── lint.yml           — linting (Python, C, YAML, Markdown)
│   │   ├── temporal.yml       — weekly temporal drift analysis
│   │   └── version-detect.yml — Grok version change detection
│   └── dependabot.yml
├── analysis/
│   ├── grok-pattern-analysis.md  — main analysis report
│   └── methodology.md            — statistical methodology
├── data/
│   ├── conversation-history.md   — sidebar titles (141 sessions)
│   ├── conversations/            — full conversation dumps (*.md)
│   └── parsed/                   — generated JSON (gitignored)
├── reports/                      — generated analysis reports (gitignored)
├── scripts/
│   ├── analyze.py                — void-cluster frequency analyzer
│   ├── parse_conversations.py    — conversation parser
│   ├── temporal_analysis.py      — temporal drift detector
│   ├── version_detect.py         — Grok version change detector
│   └── void-cluster-analyzer.c   — C analyzer (Cosmopolitan APE)
├── reviews/                      — external review documents
├── CONTRIBUTING.md               — this file
├── LICENSE                       — MIT
├── Makefile                      — local automation
└── README.md
```

## Adding Conversation Data

### Format

Full conversation dumps should be Markdown files in `data/conversations/`:

```markdown
# Conversation Title

## User
Your prompt text here...

## Grok
Grok's response text here...

## User
Follow-up prompt...

## Grok
Follow-up response...
```

### Naming Convention

Use the slug format: `title-of-conversation.md`

Example: `permutations-in-mathematical-space-visualization.md`

### Privacy

- **Do NOT include** personal information, API keys, or authentication tokens
- **Redact** any sensitive content (names, addresses, etc.)
- **Keep** technical content intact — that's what we're analyzing

## Methodology Standards

This project follows pre-specified methodology to prevent p-hacking:

1. **Void cluster was defined before data analysis** — see `methodology.md`
2. **Baselines are documented and justified** — don't change them post-hoc
3. **All statistical tests are pre-specified** — z-test, chi-squared, Cohen's h
4. **Known limitations are documented** — always add caveats

### If You're Adding New Analysis

- Define your semantic cluster BEFORE looking at the data
- Document your baseline sources
- Specify your statistical tests in advance
- Report all results, including null findings
- Note limitations and confounds

## Code Style

### Python

- **Formatter:** [ruff](https://docs.astral.sh/ruff/) (via `make format`)
- **Linter:** ruff check (via `make lint`)
- **Type hints:** Use them for function signatures
- **Docstrings:** Required for all public functions
- **Minimum Python:** 3.9 (we use `list[str]` syntax)

### C

- **Standard:** C99
- **Build system:** Cosmopolitan libc (`cosmocc`)
- **Style:** K&R-ish, `/* comments */`, snake_case

### Markdown

- Tables should be aligned
- Code blocks should specify language
- Keep lines under 120 characters where practical

## CI/CD

All PRs are checked by:

| Workflow | What It Checks |
|----------|---------------|
| `analyze.yml` | Runs void-cluster analysis, alerts on outliers |
| `lint.yml` | Python (ruff), C (cppcheck), Markdown, YAML, Shell |
| `temporal.yml` | Temporal drift detection (weekly + on data changes) |
| `version-detect.yml` | Grok behavioral discontinuity detection |

### CI Will Fail If

- Python scripts have syntax errors
- Ruff reports lint violations
- Analysis detects outliers (in strict mode on PRs)
- Conversation index fails to parse

## Communication

- **Issues:** Bug reports, feature requests, methodology questions
- **PRs:** Code changes, data additions
- **Discussions:** Open-ended questions about methodology or findings

## License

By contributing, you agree that your contributions will be licensed under the MIT License.

---

*Maintained by Vincent L. Anderson / Mighty House Inc.*
