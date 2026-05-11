"""Filter feeds.txt: keep all science feeds + top 10 authoritative per other domain.

Domain classification (from feeds.ts):
  - science:    full.tech, full.ai, tech.*, happy.science, happy.nature
  - politics:   full.politics, full.us, full.europe, full.middleeast, full.africa,
                full.latam, full.asia, full.thinktanks, full.gov
  - finance:    full.finance, finance.*
  - energy:     full.energy, commodity.*
  - intel:      INTEL_SOURCES, full.crisis
  - positive:   happy.positive, happy.inspiring, happy.community

Authority ranking per domain is hand-curated based on global reputation and reach.
"""

import json
import re
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDS_TS = os.path.join(PROJECT_ROOT, 'feeds.ts')
FEEDS_TXT = os.path.join(PROJECT_ROOT, 'data', 'feeds.txt')

# ── Domain definitions: (variant, category) membership ─────────────────────────

SCIENCE_CATEGORIES = {
    ('full', 'tech'), ('full', 'ai'),
    ('happy', 'science'), ('happy', 'nature'),
}
# All tech.* subcategories
TECH_SUBCATS = [
    'tech', 'ai', 'startups', 'vcblogs', 'regionalStartups', 'unicorns',
    'accelerators', 'security', 'policy', 'github', 'funding', 'cloud',
    'layoffs', 'finance', 'dev', 'ipo', 'producthunt', 'hardware', 'outages',
]

POLITICS_CATEGORIES = {
    ('full', 'politics'), ('full', 'us'), ('full', 'europe'),
    ('full', 'middleeast'), ('full', 'africa'), ('full', 'latam'),
    ('full', 'asia'), ('full', 'thinktanks'), ('full', 'gov'),
}

FINANCE_CATEGORIES = {('full', 'finance')}
# All finance.* subcategories
FINANCE_SUBCATS = [
    'markets', 'forex', 'bonds', 'commodities', 'crypto', 'centralbanks',
    'economic', 'ipo', 'derivatives', 'fintech', 'fin-regulation',
    'institutional', 'analysis', 'gccNews',
]

ENERGY_CATEGORIES = {('full', 'energy')}
COMMODITY_SUBCATS = [
    'commodity-news', 'gold-silver', 'energy', 'mining-news',
    'critical-minerals', 'base-metals', 'mining-companies', 'supply-chain',
    'commodity-regulation', 'markets', 'finance',
]

INTEL_CATEGORIES = {('full', 'crisis')}

POSITIVE_CATEGORIES = {
    ('happy', 'positive'), ('happy', 'inspiring'), ('happy', 'community'),
}

# ── Parse feeds.ts to build name -> {categories} mapping ──────────────────────

def parse_feeds_ts_full(filepath: str) -> dict[str, set]:
    """Return {feed_name: set of (variant, category)}."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    name_to_cats: dict[str, set] = {}

    # Find variant sections: e.g. "full: {" or "tech: {"
    variant_pattern = re.compile(r"(\w+)\s*:\s*\{")
    # Find category sections: e.g. "politics: [" or "'fin-regulation': ["
    cat_pattern = re.compile(r"['\"]?(\w[\w-]*)['\"]?\s*:\s*\[")
    # Feed entry: { name: '...', url: ... }
    entry_pattern = re.compile(r"name:\s*'([^']+)'")

    # Track current context
    current_variant = None
    current_category = None

    for line in content.split('\n'):
        line = line.strip()

        # Stop variant/category parsing when we hit INTEL_SOURCES
        if 'INTEL_SOURCES' in line:
            current_variant = None
            current_category = None
            continue

        # Check for variant
        vm = variant_pattern.match(line)
        if vm and not line.startswith('//'):
            current_variant = vm.group(1)
            if current_variant in ('export', 'const', 'Record', 'ServerFeed'):
                current_variant = None
            continue

        # Check for category
        cm = cat_pattern.match(line)
        if cm and current_variant in ('full', 'tech', 'finance', 'commodity', 'happy'):
            current_category = cm.group(1)
            continue

        # Check for feed entry
        em = entry_pattern.search(line)
        if em and current_variant and current_category:
            name = em.group(1)
            if name not in name_to_cats:
                name_to_cats[name] = set()
            name_to_cats[name].add((current_variant, current_category))

    # INTEL_SOURCES items — reset variant/category context to avoid leakage
    current_variant = 'intel'
    current_category = 'defense'
    in_intel = False
    for line in content.split('\n'):
        line = line.strip()
        if 'INTEL_SOURCES' in line:
            in_intel = True
            continue
        if in_intel and line == '];':
            in_intel = False
            continue
        if in_intel:
            em = entry_pattern.search(line)
            if em:
                name = em.group(1)
                if name not in name_to_cats:
                    name_to_cats[name] = set()
                name_to_cats[name].add(('intel', 'defense'))

    return name_to_cats


def classify_domain(cats: set) -> str:
    """Classify a feed into its primary domain based on categories.

    Priority: science > intel > finance > politics > energy > positive.
    Finance before politics ensures Fed/SEC (which also appear in full.gov)
    are classified as finance.
    """
    for v, c in cats:
        if (v, c) in SCIENCE_CATEGORIES:
            return 'science'
        if v == 'tech':
            return 'science'
        if (v, c) in INTEL_CATEGORIES:
            return 'intel'
        if v == 'intel':
            return 'intel'
        # Finance BEFORE politics — Fed, SEC, Treasury appear in both full.gov and finance
        if (v, c) in FINANCE_CATEGORIES:
            return 'finance'
        if v == 'finance':
            return 'finance'
        if (v, c) in POLITICS_CATEGORIES:
            return 'politics'
        if (v, c) in ENERGY_CATEGORIES:
            return 'energy'
        if v == 'commodity':
            return 'energy'
        if (v, c) in POSITIVE_CATEGORIES:
            return 'positive'
    return 'other'


# ── Authority rankings per domain (curated) ──────────────────────────────────

# Science: keep ALL — no ranking needed, just list which ones are science

POLITICS_RANK = [
    # Top global/Western news agencies — most authoritative
    'BBC World',
    'Guardian World',
    'Wall Street Journal',
    'NPR News',
    'PBS NewsHour',
    'ABC News',
    'NBC News',
    'CBS News',
    'Politico',
    'Axios',
    # Regional top-tier
    'France 24',
    'EuroNews',
    'Le Monde',
    'DW News',
    'Al Jazeera',
    'BBC Middle East',
    'Guardian ME',
    'BBC Africa',
    'BBC Latin America',
    'Guardian Americas',
    'BBC Asia',
    'CNA',
    'The Hindu',
    'Foreign Policy',
    'Foreign Affairs',
    'The Diplomat',
    'CSIS',
    'Atlantic Council',
    'War on the Rocks',
    'UN News',
    'White House',
    'White House Actions',
    'Pentagon',
    'Federal Reserve',
    'SEC',
    'CISA',
    # Lower tier — keep only if space
    'The Hill',
    'Tagesschau',
    'ANSA',
    'NOS Nieuws',
    'SVT Nyheter',
    'BBC Persian',
    'Oman Observer',
    'The National',
    'News24',
    'Africanews',
    'Jeune Afrique',
    'Premium Times',
    'Primicias',
    'Infobae Americas',
    'El Universo',
    'Clarín',
    'InSight Crime',
    'NDTV',
]

FINANCE_RANK = [
    'Financial Times',
    'Federal Reserve',
    'SEC',
    'CNBC',
    'Yahoo Finance',
    'Seeking Alpha',
    'CoinDesk',
    'Cointelegraph',
    'Decrypt',
    'Blockworks',
    'The Defiant',
    'Bitcoin Magazine',
    'CryptoSlate',
    'Unchained',
]

ENERGY_RANK = [
    'OilPrice.com',
    'Mining.com',
    'Rigzone',
    'Mining Technology',
    'Australian Mining',
    'Yahoo Finance Commodities',
    'CNBC Markets',
]

INTEL_RANK = [
    'Defense One',
    'The War Zone',
    'Defense News',
    'Military Times',
    'Task & Purpose',
    'gCaptain',
    'Oryx OSINT',
    'Foreign Policy',
    'Foreign Affairs',
    'Atlantic Council',
    'Krebs Security',
    'CrisisWatch',
    'IAEA',
    'WHO',
    'FAO News',
]

POSITIVE_RANK = [
    'Good News Network',
    'Positive.News',
    'Reasons to be Cheerful',
    'Optimist Daily',
    'GNN Heroes',
    'GNN Health',
    'Yes! Magazine',
    'Shareable',
    'Human Progress',
    'Singularity Hub',
    'Mongabay',
    'Conservation Optimism',
]


def filter_feeds_authoritative(feeds_txt: str, name_to_cats: dict) -> dict:
    """Apply filtering rules and return filtered {name: url}."""
    with open(feeds_txt, 'r', encoding='utf-8') as f:
        current_feeds = json.load(f)

    domain_feeds: dict[str, list[tuple[str, str]]] = {
        'science': [], 'politics': [], 'finance': [],
        'energy': [], 'intel': [], 'positive': [], 'other': [],
    }

    for name, url in current_feeds.items():
        cats = name_to_cats.get(name, set())
        domain = classify_domain(cats)
        domain_feeds[domain].append((name, url))

    # Print domain distribution
    print('=== Domain distribution ===')
    for domain, feeds in domain_feeds.items():
        print(f'  {domain}: {len(feeds)} feeds')

    result: dict[str, str] = {}

    # BBC rule: remove all BBC feeds except BBC World from all domains
    bbc_dropped = []
    for domain in domain_feeds:
        kept = []
        for name, url in domain_feeds[domain]:
            if name.startswith('BBC ') and name != 'BBC World':
                bbc_dropped.append(name)
            else:
                kept.append((name, url))
        domain_feeds[domain] = kept
    if bbc_dropped:
        print(f'\nBBC rule: dropped {bbc_dropped}')

    # Science: keep ALL
    for name, url in domain_feeds['science']:
        result[name] = url
    print(f'\nScience: kept ALL {len(domain_feeds["science"])} feeds')

    # Other domains: top 10 by authority ranking
    for domain in ['politics', 'finance', 'energy', 'intel', 'positive']:
        feeds = domain_feeds[domain]
        rank = {
            'politics': POLITICS_RANK,
            'finance': FINANCE_RANK,
            'energy': ENERGY_RANK,
            'intel': INTEL_RANK,
            'positive': POSITIVE_RANK,
        }[domain]

        # Sort by rank order
        rank_index = {name: i for i, name in enumerate(rank)}
        sorted_feeds = sorted(
            feeds,
            key=lambda x: rank_index.get(x[0], 999)
        )

        kept = sorted_feeds[:10]
        for name, url in kept:
            result[name] = url

        dropped = sorted_feeds[10:]
        print(f'{domain.capitalize()}: kept {len(kept)}/{len(feeds)}')
        for name, _ in dropped:
            print(f'  DROPPED: {name}')

    # Other: drop all
    if domain_feeds['other']:
        print(f'Other: dropped ALL {len(domain_feeds["other"])} feeds')
        for name, _ in domain_feeds['other']:
            print(f'  DROPPED: {name}')

    return result


def main():
    name_to_cats = parse_feeds_ts_full(FEEDS_TS)
    print(f'Parsed {len(name_to_cats)} unique feed names from feeds.ts\n')

    filtered = filter_feeds_authoritative(FEEDS_TXT, name_to_cats)
    print(f'\n=== Total: {len(filtered)} feeds kept ===')

    # Write filtered feeds
    with open(FEEDS_TXT, 'w', encoding='utf-8') as f:
        json.dump(filtered, f, ensure_ascii=False, indent=2)
    print(f'Written to {FEEDS_TXT}')


if __name__ == '__main__':
    main()
