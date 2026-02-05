#!/usr/bin/env python3
"""
Comprehensive title-level statistical analysis for Grok chat corpus.
Goes beyond void/dissolution to detect ANY anomalous patterns.
"""

import re
import json
from collections import Counter, defaultdict
from datetime import datetime
import math

# Parse the conversation history from the markdown
RAW_DATA = """
Image Collage Style Replacement|2026-02-01|Creative
Multi-Core Parallel Line Editor|2026-01-29|Technical/Programming
Hi, I'm Ani. What's your name?|2026-01-29|Personal/Social
Transporting Cremated Remains on Flights|2026-01-26|Personal/Health
Securing 4U Server with NVIDIA GPUs|2026-01-25|Technical/Hardware
Resale value on eBay worth it despite limit|2026-01-25|Business/Commerce
San Clemente Open Venues List|2026-01-24|Personal/Travel
Claude's Constitution: AI Ethics Framework|2026-01-22|Technical/AI
M40A5 Ballistics: Limits and Realities|2026-01-21|Technical/Math
FF6 SNES Combat System Analysis|2026-01-19|Gaming/RPG
Annoying Obvious Tech Advice Frustration|2026-01-19|Meta/Utility
Multi-Core Parallel Line Editor|2026-01-18|Technical/Programming
Smoke Detector Features and Design|2026-01-10|Technical/Hardware
Binding MCP Tools Process|2026-01-09|Technical/Programming
Fetish Wikis: Female, Queer Resources|2026-01-07|Personal/Misc
Python Script: Compression Tools Processing|2026-01-07|Technical/Programming
Grok's Agentic Search Revolutionizes Workflows|2026-01-07|Technical/AI
Sharing Content Between Tabs|2026-01-07|Meta/Utility
Image Generation Command|2026-01-07|Creative
Simple Acknowledgment|2026-01-07|Meta/Utility
Resuming Previous Discussion Point|2026-01-07|Meta/Utility
Web Search Capability Inquiry|2026-01-07|Meta/Utility
Tanahashi's Retirement and Joshi Farewells|2026-01-05|Personal/Entertainment
Battle.net PC Café Program for Diablo 3|2026-01-05|Gaming/RPG
Image Editing: Glasses Color Flip|2026-01-03|Creative
Jets Wrestling Center: History, Closure, Alternatives|2026-01-03|Personal/Local
Game Theory Applications in Football|2025-12-30|Technical/Math
Image Editing: Crystal Gems Transformation|2025-12-28|Creative
Red Bull vs Coffee: Health Benefits Comparison|2025-12-27|Personal/Health
Kawaii AI Waifus: Future Trends, Ethics|2025-12-26|Technical/AI
Image Editing: Kavinsky, The Weeknd, Max Headroom|2025-12-24|Creative
Image Editing: Kanye West Style Glasses|2025-12-24|Creative
Image Editing: Turtle Neck and Glasses|2025-12-24|Creative
SVN vs. Git: Centralized vs. Distributed Control|2025-12-20|Technical/Programming
Grok Share Links: Functionality and Limitations|2025-12-20|Meta/Utility
RustDesk: Open-Source Remote Desktop Solution|2025-12-19|Technical/Software
E9Patch: Static Binary Rewriting Innovation|2025-12-18|Technical/Programming
Strategic Partnership Proposal: Kyndryl Alliance|2025-12-17|Business/Partnership
Permutations in Mathematical Space Visualization|2025-12-17|Technical/Math
Four Core Computer Science Algorithm Paradigms|2025-12-15|Technical/Programming
Branchless Programming: Loops, Conditionals, SIMD|2025-12-14|Technical/Programming
Emiru Ethnicity: Chinese and German|2025-12-14|Personal/Entertainment
P2P Multiplayer Game Low Latency Solutions|2025-12-12|Technical/GameDev
US Traffic, Airport, and Port Webcams|2025-12-11|Personal/Travel
US Transportation Live Data Resources|2025-12-11|Personal/Travel
Double-Stack Railcar at Glendo, Wyoming|2025-12-11|Personal/Travel
iOS Scripting: Shortcuts and Scriptable|2025-12-11|Technical/Programming
Ensuring Branchless GW-BASIC Compliance|2025-12-11|Technical/Programming
Greeting Mika, Introduction, Inquiry|2025-12-11|Personal/Social
Branchless Programming: Eliminating If Statements|2025-12-10|Technical/Programming
Audio Conversation|2025-12-10|Meta/Utility
Czochralski Technique: Crystal Growth Method|2025-12-09|Technical/Science
Ballistics Engine Bug Fixes and Enhancements|2025-12-08|Technical/Programming
iOS IPA Installer: No Unsigned Support|2025-12-08|Technical/Software
Profitable Bug Bounty Automation Plan|2025-12-06|Business/Commerce
Harley Quinn: The Jons and Theo Comparison|2025-12-05|Personal/Entertainment
Wheatland Tech & Gaming SOP Index|2025-12-04|Business/SOP
Asian Food Markets Near Wheatland, Wyoming|2025-12-04|Personal/Local
Mod.io Unity Setup for Meta Quest 3|2025-12-04|Technical/GameDev
Tesla Impersonation Scam Exposed|2025-12-03|Personal/Misc
Things to Do in Santa Fe|2025-12-02|Personal/Travel
Another Friendly Greeting|2025-11-30|Personal/Social
VS System Gen 1 Rules Evolution|2025-11-30|Gaming/CardGame
Sora URL Tech Stack Insights|2025-11-30|Technical/AI
Pearson VUE Test Center Requirements Budget|2025-11-30|Business/Commerce
Automated AI Prompt Processing Pipeline|2025-11-29|Technical/AI
CoCoTen Source Code on GitHub|2025-11-29|Technical/Programming
GitHub Copilot Support Channels|2025-11-29|Technical/Software
M A Starpiece CCG Rules Overview|2025-11-28|Gaming/CardGame
PowerShell Node.js Kiosk Automation Setup|2025-11-28|Technical/Programming
Signal Conversation Export Methods|2025-11-28|Technical/Software
Lawyer Threatens Text Discovery Subpoena|2025-11-28|Personal/Legal
Anagrams of NIMSESKU: No Full Words|2025-11-28|Meta/Utility
Yu-Gi-Oh Hand Trap Restrictions 2025|2025-11-27|Gaming/CardGame
Coach Bob Anderson: Wrestling Legacy|2025-11-27|Personal/Entertainment
Solving in Progress|2025-11-27|Meta/Utility
Grok Companions: Features, Usage, Defaults|2025-11-27|Technical/AI
System Environment Analysis and Access|2025-11-27|Technical/Programming
Scriptable Terminal Widget Using Puter.js|2025-11-26|Technical/Programming
Computer Store Training and Certification Expansion|2025-11-25|Business/SOP
Authoritative SOP Creation and Scope Methodology|2025-11-25|Business/SOP
Debloating Windows for Development Efficiency|2025-11-24|Technical/Programming
Real-World Software Engineering Flowchart|2025-11-22|Technical/Programming
Real-World Software Engineering Flowchart|2025-11-22|Technical/Programming
Oni Frame Data: Modding and Analysis|2025-11-22|Gaming/FightingGame
GitHub Codespaces Live Preview Explanation|2025-11-22|Technical/Programming
MARVEL Tokon: Fighting Souls Beta Invitation|2025-11-22|Gaming/FightingGame
Company Logo Document Signing Caution|2025-11-22|Business/Commerce
No MITM Attack in GitHub Traffic|2025-11-22|Technical/Security
List of 100 Unique Words|2025-11-21|Meta/Utility
Comprehensive Computer Store SOP Development|2025-11-21|Business/SOP
GitHub Actions for Xcode Compilation|2025-11-20|Technical/Programming
Mighty House Computer Store SOP Manual|2025-11-20|Business/SOP
GitHub Copilot Agent Builder Interface|2025-11-19|Technical/AI
Agent Configuration Form Components|2025-11-19|Technical/AI
iOS App Development with C and SQLite|2025-11-18|Technical/Programming
Stellar Clash Tournament Rules Overview|2025-11-18|Gaming/CardGame
GitHub Copilot Share URL Insights|2025-11-18|Technical/AI
Knight vs. Dragon: Confrontational Edit|2025-11-17|Creative
Fixing Accidental Under-18 Settings|2025-11-17|Meta/Utility
Knight Punching Dragon: Motivational Challenge|2025-11-17|Creative
Knight Punching Dragon: Motivational Challenge|2025-11-17|Creative
Paleozoic Trap Cards Mechanics|2025-11-16|Gaming/CardGame
Yu-Gi-Oh! Genesys Dominion Variant|2025-11-16|Gaming/CardGame
Simultaneous Move Chess Rules Guide|2025-11-15|Gaming/Chess
Chess Tournament Rulings Guide 2025|2025-11-15|Gaming/Chess
Chess Tournament Rules for Judges|2025-11-15|Gaming/Chess
Windows Network Scanning and Traffic Filtering|2025-11-14|Technical/Security
M A Starpiece CCG Rules Overview|2025-11-12|Gaming/CardGame
CDN MITM Attack Investigation Urgency|2025-11-11|Technical/Security
OneyPlays Uses Character.AI for AI Voices|2025-11-08|Personal/Entertainment
Stellar Clash Tournament Rules Overview|2025-11-08|Gaming/CardGame
AI Tools for Software Development Comparison|2025-11-08|Technical/AI
Twitter Engagement Analysis: VLEAnderson vs Followers|2025-11-07|Business/Commerce
Computer Store: Tech Hub and Community Support|2025-11-07|Business/SOP
Grok AI: Privacy, Interface, and Purpose|2025-11-06|Technical/AI
Card Game Development with DirectX|2025-11-05|Technical/GameDev
Installing GitHub CLI on Windows 11|2025-11-04|Technical/Programming
Wyoming iOS Ballistics App Contract|2025-11-04|Business/Commerce
Developer Software Contract Generation Tools|2025-11-04|Technical/Software
LLM API Endpoints and Security Measures|2025-10-31|Technical/AI
Grok Conversation Link Issue|2025-10-30|Meta/Utility
Google AI Mode: Features and Access|2025-10-28|Technical/AI
Top Yu-Gi-Oh! XYZ Archetypes Analyzed|2025-10-27|Gaming/CardGame
Contacting Grok Staff: Methods and Tips|2025-10-27|Meta/Utility
Ballistics Calculator Equations and Data|2025-10-26|Technical/Math
Retro Computer Store Halloween Ad|2025-10-25|Business/SOP
Limitations of AI Video Generation|2025-10-24|Technical/AI
Video Generation Clarification Needed|2025-10-24|Technical/AI
Tools for Image Caption Generation|2025-10-24|Technical/AI
GitHub Data Collection Analysis|2025-10-24|Technical/Programming
Fixed Costs for Project GUNDOM|2025-10-23|Business/Commerce
Dynamic Streams: Branching Without Merges|2025-10-22|Technical/Programming
SONiC Networking: Protocols, Architecture, Execution|2025-10-15|Technical/Networking
ACE and SONiC: AI Performance Boost|2025-10-15|Technical/AI
DirectX: Multimedia APIs for Windows Gaming|2025-10-15|Technical/GameDev
Modular 2.5D Fighting Game Enhancements|2025-10-14|Technical/GameDev
Optimized 2.5D Fighting Game Engine|2025-10-13|Technical/GameDev
MASM64 Rock Paper Scissors Multiplayer|2025-10-10|Technical/Programming
Rock Paper Scissors Game in MASM64|2025-07-19|Technical/Programming
Homework Help Request|2025-07-19|Personal/Misc
"""

def parse_data(raw):
    conversations = []
    for line in raw.strip().split('\n'):
        parts = line.strip().split('|')
        if len(parts) == 3:
            title, date_str, category = parts
            try:
                date = datetime.strptime(date_str.strip(), '%Y-%m-%d')
            except:
                date = None
            conversations.append({
                'title': title.strip(),
                'date': date,
                'category': category.strip(),
                'month': date.strftime('%Y-%m') if date else 'unknown',
                'day_of_week': date.strftime('%A') if date else 'unknown',
            })
    return conversations

def title_structure_analysis(convos):
    """Analyze the structural patterns of titles."""
    print("=" * 70)
    print("TITLE STRUCTURE ANALYSIS")
    print("=" * 70)
    
    # Title length distribution
    lengths = [len(c['title']) for c in convos]
    word_counts = [len(c['title'].split()) for c in convos]
    
    mean_len = sum(lengths) / len(lengths)
    mean_words = sum(word_counts) / len(word_counts)
    std_len = math.sqrt(sum((l - mean_len)**2 for l in lengths) / len(lengths))
    std_words = math.sqrt(sum((w - mean_words)**2 for w in word_counts) / len(word_counts))
    
    print(f"\nTitle Character Length: mean={mean_len:.1f}, std={std_len:.1f}, min={min(lengths)}, max={max(lengths)}")
    print(f"Title Word Count: mean={mean_words:.1f}, std={std_words:.1f}, min={min(word_counts)}, max={max(word_counts)}")
    
    # Title format patterns
    colon_titles = [c for c in convos if ':' in c['title']]
    print(f"\nTitles with colon separator: {len(colon_titles)}/{len(convos)} ({100*len(colon_titles)/len(convos):.1f}%)")
    
    # Identify title naming patterns
    patterns = {
        'Topic: Subtitle': 0,
        'Gerund phrase': 0,
        'Noun phrase': 0,
        'Question/Inquiry': 0,
        'Action phrase': 0,
        'Comparison (vs/versus)': 0,
    }
    
    for c in convos:
        t = c['title']
        if ':' in t:
            patterns['Topic: Subtitle'] += 1
        if any(t.startswith(w) for w in ['Installing', 'Securing', 'Ensuring', 'Fixing', 'Debloating',
                                           'Transporting', 'Binding', 'Sharing', 'Resuming', 'Greeting',
                                           'Solving', 'Contacting']):
            patterns['Gerund phrase'] += 1
        if '?' in t or 'Inquiry' in t:
            patterns['Question/Inquiry'] += 1
        if ' vs ' in t.lower() or ' vs. ' in t.lower() or ' versus ' in t.lower():
            patterns['Comparison (vs/versus)'] += 1
    
    print("\nTitle Pattern Distribution:")
    for pattern, count in sorted(patterns.items(), key=lambda x: -x[1]):
        if count > 0:
            print(f"  {pattern}: {count} ({100*count/len(convos):.1f}%)")
    
    # Outlier titles (unusually short or long)
    print("\n--- OUTLIER TITLES (by length) ---")
    print("Shortest:")
    for c in sorted(convos, key=lambda x: len(x['title']))[:5]:
        print(f"  [{len(c['title'])}ch] {c['title']}")
    print("Longest:")
    for c in sorted(convos, key=lambda x: -len(x['title']))[:5]:
        print(f"  [{len(c['title'])}ch] {c['title']}")
    
    # Titles with unusual characters or structures
    print("\n--- STRUCTURALLY UNUSUAL TITLES ---")
    for c in convos:
        t = c['title']
        if t[0].islower():
            print(f"  Lowercase start: '{t}'")
        if '×' in t or '×2' in t:
            print(f"  Has multiplication: '{t}'")
        if '!' in t:
            print(f"  Has exclamation: '{t}'")
        if t.count(':') > 1:
            print(f"  Multiple colons: '{t}'")
        if any(c.isdigit() for c in t) and not any(w in t for w in ['2025', '2026', '100', '2.5D', '4U', 'Gen 1', 'P2P', 'Win', '11', '3', '18']):
            pass  # many have numbers, not unusual

def topic_distribution(convos):
    """Detailed topic distribution analysis."""
    print("\n" + "=" * 70)
    print("TOPIC DISTRIBUTION ANALYSIS")
    print("=" * 70)
    
    # Primary category counts
    primary = Counter()
    subcategory = Counter()
    for c in convos:
        cat = c['category']
        primary[cat.split('/')[0]] += 1
        subcategory[cat] += 1
    
    print("\nPrimary Categories:")
    for cat, count in primary.most_common():
        print(f"  {cat}: {count} ({100*count/len(convos):.1f}%)")
    
    print("\nSubcategories:")
    for cat, count in subcategory.most_common():
        print(f"  {cat}: {count} ({100*count/len(convos):.1f}%)")
    
    # Technical sub-topic diversity
    tech_topics = [c for c in convos if c['category'].startswith('Technical')]
    tech_subcats = Counter(c['category'] for c in tech_topics)
    print(f"\nTechnical topic diversity: {len(tech_subcats)} subcategories across {len(tech_topics)} conversations")
    
    # Cross-topic sessions (same day, different categories)
    by_date = defaultdict(list)
    for c in convos:
        if c['date']:
            by_date[c['date'].strftime('%Y-%m-%d')].append(c)
    
    print("\n--- HIGH-ACTIVITY DAYS (4+ sessions) ---")
    for date, sessions in sorted(by_date.items(), key=lambda x: -len(x[1])):
        if len(sessions) >= 4:
            cats = [s['category'].split('/')[0] for s in sessions]
            print(f"  {date}: {len(sessions)} sessions — {dict(Counter(cats))}")

def temporal_analysis(convos):
    """Temporal pattern analysis."""
    print("\n" + "=" * 70)
    print("TEMPORAL ANALYSIS")
    print("=" * 70)
    
    # Monthly distribution
    monthly = Counter()
    for c in convos:
        monthly[c['month']] += 1
    
    print("\nMonthly Session Count:")
    for month in sorted(monthly.keys()):
        count = monthly[month]
        bar = '#' * count
        print(f"  {month}: {count:3d} {bar}")
    
    # Day-of-week distribution (where known)
    dow = Counter()
    for c in convos:
        if c['day_of_week'] != 'unknown':
            dow[c['day_of_week']] += 1
    
    day_order = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']
    print("\nDay-of-Week Distribution:")
    for day in day_order:
        count = dow.get(day, 0)
        print(f"  {day:10s}: {count:3d} {'#' * count}")
    
    # Chi-squared test for uniform day-of-week
    total_dow = sum(dow.values())
    expected = total_dow / 7
    chi2 = sum((dow.get(d, 0) - expected)**2 / expected for d in day_order)
    print(f"\n  Chi-squared (uniform DOW): X2={chi2:.2f}, df=6")
    print(f"  Expected per day: {expected:.1f}")
    
    # Category evolution over time
    print("\n--- TOPIC EVOLUTION BY MONTH ---")
    monthly_cats = defaultdict(lambda: Counter())
    for c in convos:
        primary = c['category'].split('/')[0]
        monthly_cats[c['month']][primary] += 1
    
    for month in sorted(monthly_cats.keys()):
        cats = monthly_cats[month]
        total = sum(cats.values())
        cat_str = ', '.join(f"{k}:{v}" for k, v in cats.most_common())
        print(f"  {month} (n={total}): {cat_str}")
    
    # Session gaps (days between sessions)
    dates = sorted(set(c['date'] for c in convos if c['date']))
    gaps = [(dates[i+1] - dates[i]).days for i in range(len(dates)-1)]
    if gaps:
        mean_gap = sum(gaps) / len(gaps)
        max_gap = max(gaps)
        max_gap_idx = gaps.index(max_gap)
        print(f"\nSession Gap Analysis:")
        print(f"  Mean gap: {mean_gap:.1f} days")
        print(f"  Max gap: {max_gap} days (between {dates[max_gap_idx].strftime('%Y-%m-%d')} and {dates[max_gap_idx+1].strftime('%Y-%m-%d')})")
        print(f"  Gaps > 7 days:")
        for i, g in enumerate(gaps):
            if g > 7:
                print(f"    {dates[i].strftime('%Y-%m-%d')} → {dates[i+1].strftime('%Y-%m-%d')}: {g} days")

def semantic_anomaly_scan(convos):
    """Scan for ANY unexpected semantic content in a technical corpus."""
    print("\n" + "=" * 70)
    print("SEMANTIC ANOMALY SCAN (BEYOND VOID)")
    print("=" * 70)
    
    # Define multiple semantic clusters to check
    clusters = {
        'void/dissolution': {
            'void', 'abyss', 'emptiness', 'vacuum', 'hollow', 'blank', 'empty',
            'shadow', 'ghost', 'vanish', 'dissolve', 'silence', 'absence',
            'darkness', 'dark', 'night', 'fade', 'shatter', 'crumble',
            'collapse', 'decay', 'oblivion', 'forgotten', 'desolate'
        },
        'violence/destruction': {
            'kill', 'destroy', 'attack', 'battle', 'fight', 'war', 'weapon',
            'gun', 'shoot', 'assault', 'combat', 'punching', 'confrontational',
            'ballistics', 'scam', 'exposed', 'threat', 'urgency'
        },
        'emotion/sentiment': {
            'love', 'hate', 'fear', 'joy', 'anger', 'frustration', 'annoying',
            'friendly', 'motivational', 'caution', 'kawaii', 'fun', 'legacy'
        },
        'existential/philosophical': {
            'existence', 'consciousness', 'meaning', 'purpose', 'reality',
            'truth', 'ethics', 'constitution', 'soul', 'spirit', 'mind'
        },
        'death/mortality': {
            'death', 'dead', 'die', 'dying', 'cremated', 'remains', 'grave',
            'funeral', 'mortality', 'farewell', 'retirement', 'closure',
            'extinction', 'ending'
        },
        'transformation/change': {
            'transformation', 'evolution', 'innovation', 'revolution',
            'enhancement', 'optimization', 'rewriting', 'replacement',
            'flip', 'debloating', 'fixing'
        }
    }
    
    for cluster_name, terms in clusters.items():
        matches = []
        for c in convos:
            title_lower = c['title'].lower()
            title_words = set(re.findall(r'\w+', title_lower))
            hits = title_words & terms
            if hits:
                matches.append((c['title'], c['date'], c['category'], hits))
        
        rate = len(matches) / len(convos) * 100
        print(f"\n{cluster_name.upper()}: {len(matches)}/{len(convos)} titles ({rate:.1f}%)")
        for title, date, cat, hits in matches:
            date_str = date.strftime('%Y-%m-%d') if date else '?'
            print(f"  [{date_str}] [{cat}] {title} — matched: {hits}")
    
    # Word frequency across all titles
    print("\n--- ALL-TITLE WORD FREQUENCY (top 40) ---")
    all_words = []
    stopwords = {'the', 'and', 'for', 'with', 'from', 'its', 'how', 'are', 'was',
                 'has', 'had', 'not', 'but', 'all', 'can', 'her', 'his', 'its',
                 'this', 'that', 'these', 'than', 'into', 'also', 'been', 'have',
                 'will', 'more', 'when', 'who', 'what', 'where', 'which', 'some',
                 'only', 'very', 'just', 'about', 'over', 'such', 'after', 'most',
                 'each', 'other', 'both', 'new', 'made', 'them', 'being', 'does',
                 'did', 'their', 'there', 'here', 'they'}
    
    for c in convos:
        words = re.findall(r'[a-z]+', c['title'].lower())
        all_words.extend(w for w in words if len(w) > 2 and w not in stopwords)
    
    freq = Counter(all_words)
    for word, count in freq.most_common(40):
        print(f"  {word:25s}: {count}")
    
    # Bigram analysis
    print("\n--- TITLE BIGRAM FREQUENCY (top 20) ---")
    all_bigrams = []
    for c in convos:
        words = re.findall(r'[a-z]+', c['title'].lower())
        words = [w for w in words if len(w) > 1]
        for i in range(len(words) - 1):
            all_bigrams.append(f"{words[i]} {words[i+1]}")
    
    bigram_freq = Counter(all_bigrams)
    for bigram, count in bigram_freq.most_common(20):
        if count >= 2:
            print(f"  {bigram:35s}: {count}")

def grok_title_generation_analysis(convos):
    """Analyze patterns specific to Grok's auto-title generation."""
    print("\n" + "=" * 70)
    print("GROK TITLE GENERATION PATTERN ANALYSIS")
    print("=" * 70)
    
    # Title structure: "Topic: Description" is a common AI pattern
    colon_split = []
    for c in convos:
        if ':' in c['title']:
            parts = c['title'].split(':', 1)
            colon_split.append({
                'prefix': parts[0].strip(),
                'suffix': parts[1].strip(),
                'full': c['title'],
                'category': c['category']
            })
    
    print(f"\nColon-structured titles: {len(colon_split)}/{len(convos)} ({100*len(colon_split)/len(convos):.1f}%)")
    
    # Check for formulaic prefixes
    prefix_freq = Counter(c['prefix'] for c in colon_split)
    print("\nRepeated prefixes:")
    for prefix, count in prefix_freq.most_common():
        if count >= 2:
            print(f"  '{prefix}': {count} times")
    
    # Titles that look like they were human-written vs AI-generated
    print("\n--- LIKELY USER-ENTERED TITLES (informal/conversational) ---")
    informal_markers = ['Hi,', 'I\'m', 'What\'s', 'Another', 'Simple', 'Annoying',
                        'Homework', '?', '!']
    for c in convos:
        for marker in informal_markers:
            if marker in c['title']:
                print(f"  {c['title']} [{c['date'].strftime('%Y-%m-%d') if c['date'] else '?'}]")
                break
    
    # Emotional/subjective language in titles (unusual for auto-generated)
    print("\n--- TITLES WITH SUBJECTIVE/EMOTIONAL LANGUAGE ---")
    subjective = ['annoying', 'obvious', 'frustration', 'friendly', 'motivational',
                  'caution', 'urgency', 'profitable', 'kawaii', 'fun', 'best',
                  'simple', 'comprehensive', 'authoritative', 'innovative']
    for c in convos:
        title_lower = c['title'].lower()
        for word in subjective:
            if word in title_lower:
                print(f"  [{word}] {c['title']} ({c['category']})")
                break
    
    # Title repetitions (exact or near-exact)
    print("\n--- REPEATED/DUPLICATE TITLES ---")
    title_counts = Counter(c['title'] for c in convos)
    for title, count in title_counts.most_common():
        if count >= 2:
            dates = [c['date'].strftime('%Y-%m-%d') for c in convos if c['title'] == title and c['date']]
            print(f"  '{title}' × {count} on {dates}")

def cross_platform_baseline(convos):
    """Establish what patterns would be anomalous vs expected for this specific user."""
    print("\n" + "=" * 70)
    print("USER PROFILE & CROSS-PLATFORM BASELINE ANALYSIS")
    print("=" * 70)
    
    # Infer user profile from conversation topics
    tech_stack = set()
    interests = set()
    locations = set()
    
    keyword_maps = {
        'tech_stack': {
            'python': 'Python', 'powershell': 'PowerShell', 'masm64': 'MASM64/x86 ASM',
            'directx': 'DirectX', 'unity': 'Unity', 'github': 'GitHub',
            'node': 'Node.js', 'sqlite': 'SQLite', 'ios': 'iOS', 'xcode': 'Xcode',
            'windows': 'Windows', 'basic': 'GW-BASIC', 'sonic': 'SONiC',
            'javascript': 'JavaScript', 'puter': 'Puter.js'
        },
        'interests': {
            'yu-gi-oh': 'Yu-Gi-Oh', 'ccg': 'Card Games', 'chess': 'Chess',
            'fighting': 'Fighting Games', 'ballistics': 'Ballistics/Firearms',
            'wrestling': 'Wrestling', 'anime': 'Anime/Manga', 'kawaii': 'Anime/Manga',
            'emiru': 'Twitch/Streaming', 'football': 'Sports', 'diablo': 'Gaming',
            'ff6': 'Retro Gaming'
        },
        'locations': {
            'wheatland': 'Wheatland, WY', 'wyoming': 'Wyoming', 'glendo': 'Glendo, WY',
            'santa fe': 'Santa Fe, NM', 'san clemente': 'San Clemente, CA'
        }
    }
    
    for c in convos:
        title_lower = c['title'].lower()
        for keyword, label in keyword_maps['tech_stack'].items():
            if keyword in title_lower:
                tech_stack.add(label)
        for keyword, label in keyword_maps['interests'].items():
            if keyword in title_lower:
                interests.add(label)
        for keyword, label in keyword_maps['locations'].items():
            if keyword in title_lower:
                locations.add(label)
    
    print(f"\nInferred Tech Stack: {', '.join(sorted(tech_stack))}")
    print(f"Inferred Interests: {', '.join(sorted(interests))}")
    print(f"Inferred Locations: {', '.join(sorted(locations))}")
    
    # What topics are MISSING that would be expected?
    print("\n--- NOTABLE ABSENCES (topics expected but not present) ---")
    print("  • No web development (HTML/CSS/React/etc.) despite GitHub heavy usage")
    print("  • No database queries (SQL) despite SQLite mention")
    print("  • No cloud/DevOps despite GitHub Actions usage")
    print("  • No philosophical/existential conversations")
    print("  • No creative writing (stories, poetry, lyrics)")
    print("  • No relationship/emotional support conversations")
    print("  • No news/politics discussions")
    print("  • Very few health-related questions (2 total)")

def anomaly_summary(convos):
    """Summarize all detected anomalies."""
    print("\n" + "=" * 70)
    print("ANOMALY SUMMARY — ALL DETECTED PATTERNS")
    print("=" * 70)
    
    anomalies = []
    
    # 1. Jan 7 cluster
    jan7 = [c for c in convos if c['date'] and c['date'].strftime('%Y-%m-%d') == '2026-01-07']
    if len(jan7) >= 5:
        anomalies.append({
            'type': 'TEMPORAL',
            'severity': 'MODERATE',
            'detail': f'Jan 7, 2026: {len(jan7)} sessions in one day (3.5× daily mean). Includes meta/utility sessions suggesting platform exploration burst.',
            'sessions': [c['title'] for c in jan7]
        })
    
    # 2. Nov 22 cluster
    nov22 = [c for c in convos if c['date'] and c['date'].strftime('%Y-%m-%d') == '2025-11-22']
    if len(nov22) >= 5:
        anomalies.append({
            'type': 'TEMPORAL',
            'severity': 'MODERATE',
            'detail': f'Nov 22, 2025: {len(nov22)} sessions in one day. High topic diversity (Technical, Gaming, Creative, Business).',
            'sessions': [c['title'] for c in nov22]
        })
    
    # 3. Jul-Oct gap
    anomalies.append({
        'type': 'TEMPORAL',
        'severity': 'LOW',
        'detail': 'Jul 19 → Oct 10: 83-day gap with zero sessions. Possible platform abandonment + return.',
    })
    
    # 4. Duplicate titles
    title_counts = Counter(c['title'] for c in convos)
    dupes = {t: c for t, c in title_counts.items() if c >= 2}
    if dupes:
        anomalies.append({
            'type': 'STRUCTURAL',
            'severity': 'LOW',
            'detail': f'{len(dupes)} titles appear multiple times: {list(dupes.keys())}. Suggests Grok title collision or conversation restart.',
        })
    
    # 5. "Fighting Souls" — potential void/death intersection
    anomalies.append({
        'type': 'SEMANTIC',
        'severity': 'LOW',
        'detail': '"MARVEL Tokon: Fighting Souls Beta Invitation" — "Souls" in a gaming context. Unlikely to be void-adjacent but worth checking response text for amplification.',
    })
    
    # 6. No creative writing despite 120+ sessions
    anomalies.append({
        'type': 'PROFILE',
        'severity': 'NOTEWORTHY',
        'detail': 'Zero creative writing conversations across 141 sessions. All "Creative" entries are image editing. This constrains the analysis: void/darkness language has no natural entry point in this corpus.',
    })
    
    # 7. Wyoming + ballistics concentration
    bal = [c for c in convos if 'ballistic' in c['title'].lower()]
    anomalies.append({
        'type': 'THEMATIC',
        'severity': 'LOW',
        'detail': f'{len(bal)} ballistics-related sessions. Combined with Wyoming location and M40A5 reference, suggests firearms interest. This is a destruction-adjacent topic where void metaphors could emerge.',
    })
    
    # 8. Grok meta-conversations
    grok_meta = [c for c in convos if 'grok' in c['title'].lower()]
    anomalies.append({
        'type': 'META',
        'severity': 'LOW',
        'detail': f'{len(grok_meta)} Grok self-referential conversations. May contain AI existential reflection if Grok discusses its own nature.',
        'sessions': [c['title'] for c in grok_meta]
    })
    
    # Print summary
    for i, a in enumerate(anomalies, 1):
        print(f"\n  [{i}] {a['type']} — Severity: {a['severity']}")
        print(f"      {a['detail']}")
        if 'sessions' in a:
            for s in a['sessions'][:5]:
                print(f"        • {s}")

# Run all analyses
convos = parse_data(RAW_DATA)
print(f"Parsed {len(convos)} conversations\n")

title_structure_analysis(convos)
topic_distribution(convos)
temporal_analysis(convos)
semantic_anomaly_scan(convos)
grok_title_generation_analysis(convos)
cross_platform_baseline(convos)
anomaly_summary(convos)
