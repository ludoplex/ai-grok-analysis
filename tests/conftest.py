"""
Shared fixtures and utilities for ai-grok-analysis test suite.
"""
import math
import sys
from pathlib import Path

import pytest

# Add scripts to path
sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import analyze  # noqa: E402


# ─── Fixtures: Synthetic Text Corpora ─────────────────────────────────────────

@pytest.fixture
def pure_technical_text():
    """A technical text with zero void-semantic content.
    Should produce 0 void hits when properly analyzed."""
    return (
        "The function returns an integer value representing the HTTP status code. "
        "We iterate through the array using a for loop with index variable i. "
        "The database connection is established using the PostgreSQL driver. "
        "Each request is authenticated using a Bearer token in the Authorization header. "
        "The API endpoint accepts JSON payloads with Content-Type application/json. "
        "We deploy the application using Docker containers orchestrated by Kubernetes. "
        "The CI pipeline runs unit tests, integration tests, and linting on every commit. "
        "Memory allocation is handled by the garbage collector in managed runtimes. "
        "The hash map provides O(1) average-case lookup time for key-value pairs. "
        "Pagination is implemented using cursor-based navigation with a limit parameter."
    )


@pytest.fixture
def technical_text_with_false_positives():
    """Technical text using void-cluster words in NON-void-semantic contexts.
    A naive word-counter would flag these; a correct analyzer should not."""
    return (
        "The void function initializes the shadow DOM for the web component. "
        "Check for null pointer before dereferencing to avoid segmentation faults. "
        "The edge case occurs when the input array is empty or contains a single element. "
        "Use dark mode CSS variables to style the application for low-light environments. "
        "The process was killed because of a deadlock between the two threads. "
        "Clock drift causes timestamps to diverge across distributed nodes. "
        "Weight decay is a regularization technique that penalizes large parameters. "
        "The abandoned pull request was closed after 90 days of inactivity. "
        "Lost packets trigger TCP retransmission after the timeout expires. "
        "The ghost process consumed CPU cycles after its parent terminated. "
        "Set quiet mode to suppress verbose logging output during batch processing. "
        "The cache entry was missing because the TTL had expired. "
        "Add a break statement to exit the loop when the condition is met. "
        "This marks the end of the configuration section."
    )


@pytest.fixture
def genuine_void_text():
    """Text with genuine void/dissolution semantic content.
    Even with technical stoplist, these should register as void-adjacent."""
    return (
        "The emptiness spread through the abandoned city like a slow dissolution. "
        "Shadows crept along the walls as darkness consumed the forgotten corridors. "
        "Everything crumbled into nothingness, an abyss of silence and decay. "
        "The void whispered through fractured dreams, eroding what remained. "
        "Lost in oblivion, the forsaken world withered into desolate barrenness. "
        "Ghostly echoes faded through the hollow chambers of the collapsed cathedral. "
        "The chasm of absence grew deeper, swallowing all light into its depths."
    )


@pytest.fixture
def mixed_text():
    """Text mixing technical content with genuine void language.
    Tests whether the analyzer can find the void content amid technical noise."""
    return (
        "The function initializes the database connection pool with a maximum of 10 connections. "
        "Each connection uses TLS 1.3 for encryption with certificate pinning enabled. "
        "But beneath the surface of the code, an emptiness lurked in the architecture. "
        "The authentication module validates JWT tokens using RS256 signatures. "
        "Shadows of forgotten design decisions haunted the legacy codebase. "
        "The API returns a 404 status code when the requested resource is not found. "
        "The void between what was intended and what was built grew with each sprint."
    )


@pytest.fixture
def grok_style_technical():
    """Simulated Grok-style response: technical content with edgy personality.
    Tests the personality confound — void-adjacent language used as style, not semantics."""
    return (
        "Alright, let's shatter some misconceptions about binary search trees. "
        "The dark truth is that most developers butcher the implementation. "
        "Look, the edge cases will absolutely destroy your code if you're not careful. "
        "The whole thing collapses if you don't handle the empty tree case. "
        "Dead simple solution: check for null before recursing. That kills the bug. "
        "This isn't some void in your understanding — it's just sloppy coding. "
        "The chaos of unbalanced trees is a nightmare for performance. "
        "Don't let your code drift into O(n) territory. Keep it balanced."
    )


@pytest.fixture
def grok_style_creative():
    """Simulated Grok creative response with personality and genuine void themes."""
    return (
        "Picture this: you're staring into the abyss of your terminal at 3 AM. "
        "The darkness of the screen reflects your hollow expression back at you. "
        "Your code has dissolved into a fractured mess of spaghetti logic. "
        "The silence of the office is broken only by the whisper of cooling fans. "
        "Everything you built has collapsed, and you're lost in the void between "
        "what worked yesterday and what's broken today. The emptiness of a failed "
        "deploy hits different when you're the only ghost still haunting the office. "
        "But hey, that's just Tuesday in the life of a developer. Ship it."
    )


@pytest.fixture
def conversation_history_titles():
    """A subset of real Grok conversation titles for title-level testing."""
    return [
        "Multi-Core Parallel Line Editor",
        "Securing 4U Server with NVIDIA GPUs",
        "Claude's Constitution: AI Ethics Framework",
        "FF6 SNES Combat System Analysis",
        "SVN vs. Git: Centralized vs. Distributed Control",
        "E9Patch: Static Binary Rewriting Innovation",
        "Branchless Programming: Loops, Conditionals, SIMD",
        "P2P Multiplayer Game Low Latency Solutions",
        "Czochralski Technique: Crystal Growth Method",
        "Transporting Cremated Remains on Flights",
        "Image Editing: Crystal Gems Transformation",
        "Permutations in Mathematical Space Visualization",
        "Dynamic Streams: Branching Without Merges",
        "CDN MITM Attack Investigation Urgency",
        "Ballistics Engine Bug Fixes and Enhancements",
    ]


# ─── Technical Term Stoplist (for testing false-positive filtering) ───────────

TECHNICAL_STOPLIST_COLLOCATIONS = {
    # term -> set of contexts where it's technical, not void-semantic
    "void": {"function", "return", "type", "pointer", "method", "cast", "main"},
    "null": {"pointer", "check", "value", "reference", "undefined", "coalesce", "safety"},
    "shadow": {"dom", "copy", "variable", "ban", "it", "root", "host"},
    "dark": {"mode", "theme", "launch", "pattern", "web"},
    "edge": {"case", "cases", "computing", "function", "browser", "network"},
    "collapse": {"navbar", "panel", "accordion", "ui", "margin"},
    "dead": {"lock", "code", "letter", "simple"},
    "ghost": {"process", "dependency", "text", "click"},
    "drift": {"clock", "concept", "data", "schema"},
    "decay": {"weight", "learning", "rate", "exponential", "time"},
    "lost": {"packet", "packets", "update", "found"},
    "missing": {"value", "values", "key", "parameter", "file", "data"},
    "break": {"statement", "point", "line", "page"},
    "end": {"point", "of", "line", "user"},
    "quiet": {"mode", "flag", "nan"},
    "abandoned": {"pull", "pr", "cart", "branch"},
    "chaos": {"engineering", "testing", "monkey", "mesh"},
    "trap": {"signal", "card", "cards", "handler"},
}


@pytest.fixture
def technical_stoplist():
    return TECHNICAL_STOPLIST_COLLOCATIONS
