# Build Instructions for C Analysis Tools

## Tools

1. **void-cluster-analyzer.c** — General void/dissolution semantic cluster frequency analyzer
2. **grok-personality-filter.c** — Grok personality bias controller (separates personality-expected void language from genuinely anomalous patterns)

## Build with Cosmopolitan (APE — Actually Portable Executable)

```bash
# Requires cosmocc toolchain: https://cosmo.zip/
# On Linux/Mac/WSL:
cosmocc -O2 -o void-cluster-analyzer.com void-cluster-analyzer.c
cosmocc -O2 -o grok-personality-filter.com grok-personality-filter.c
```

## Build with standard GCC/Clang

```bash
gcc -O2 -Wall -o void-cluster-analyzer void-cluster-analyzer.c -lm
gcc -O2 -Wall -o grok-personality-filter grok-personality-filter.c -lm
```

## Build with MSVC (Windows)

```cmd
cl /O2 /W4 void-cluster-analyzer.c
cl /O2 /W4 grok-personality-filter.c
```

## Usage

```bash
# Basic void-cluster scan
echo "The void crumbles into darkness" | ./void-cluster-analyzer

# With custom baseline
./void-cluster-analyzer -b 0.03 conversation.txt

# Grok personality bias control
./grok-personality-filter conversation.txt

# Debug mode (show each void hit with context window)
./grok-personality-filter -d conversation.txt

# Per-section breakdown
./grok-personality-filter -s conversation.txt

# Custom co-occurrence window (default: ±15 tokens)
./grok-personality-filter -w 20 conversation.txt

# Quiet/machine-readable output
./grok-personality-filter -q conversation.txt
```

## Notes

- Both tools use pure C89/C99 with standard library only (stdio, stdlib, string, math, ctype)
- No external dependencies
- The `.com` APE output runs on Linux, macOS, Windows, FreeBSD, and OpenBSD from a single binary
- On Windows, the cosmocc shell script requires Git Bash or WSL to execute. For native Windows builds, use MSVC or MinGW-GCC.
