"""Filter feeds.txt with 3 rules:

1. Keep ALL tech/science feeds
2. Delete ALL region-specific feeds
3. From the rest, keep top 10 most globally representative news outlets
"""

import json
import re
import os

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FEEDS_TS = os.path.join(PROJECT_ROOT, 'feeds.ts')
FEEDS_TXT = os.path.join(PROJECT_ROOT, 'data', 'feeds.txt')

# ── Category definitions from feeds.ts ────────────────────────────────────────

# Tech/science: keep ALL
SCIENCE_VARIANT_CATS = {
    ('full', 'tech'), ('full', 'ai'),
    ('happy', 'science'), ('happy', 'nature'),
}
# All tech.* subcategories are science
TECH_VARIANT = 'tech'

# Regional: delete ALL (feeds focused on one region)
REGIONAL_CATS = {
    ('full', 'us'), ('full', 'europe'), ('full', 'middleeast'),
    ('full', 'africa'), ('full', 'latam'), ('full', 'asia'),
    ('finance', 'gccNews'), ('tech', 'regionalStartups'),
}

# ── Parse feeds.ts → {name: {(variant, category)}} ──────────────────────────

def parse_feeds_ts(filepath: str) -> dict[str, set]:
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    name_to_cats: dict[str, set] = {}
    current_variant = None
    current_category = None
    entry_re = re.compile(r"name:\s*'([^']+)'")

    for line in content.split('\n'):
        line = line.strip()

        # Stop before INTEL_SOURCES to avoid category leakage
        if 'INTEL_SOURCES' in line:
            current_variant = None
            current_category = None
            continue

        # Variant: e.g. "full: {" or "tech: {"
        vm = re.match(r"(\w+)\s*:\s*\{", line)
        if vm:
            v = vm.group(1)
            if v in ('full', 'tech', 'finance', 'commodity', 'happy'):
                current_variant = v
            continue

        # Category: e.g. "politics: [" or "'fin-regulation': ["
        cm = re.match(r"['\"]?([\w-]+)['\"]?\s*:\s*\[", line)
        if cm and current_variant in ('full', 'tech', 'finance', 'commodity', 'happy'):
            current_category = cm.group(1)
            continue

        # Feed entry
        em = entry_re.search(line)
        if em and current_variant and current_category:
            name = em.group(1)
            if name not in name_to_cats:
                name_to_cats[name] = set()
            name_to_cats[name].add((current_variant, current_category))

    # INTEL_SOURCES
    in_intel = False
    for line in content.split('\n'):
        line = line.strip()
        if 'INTEL_SOURCES' in line:
            in_intel = True
            continue
        if in_intel and line == '];':
            break
        if in_intel:
            em = entry_re.search(line)
            if em:
                name = em.group(1)
                if name not in name_to_cats:
                    name_to_cats[name] = set()
                name_to_cats[name].add(('intel', 'defense'))

    return name_to_cats


def classify(name_to_cats: dict[str, set]) -> tuple[set, set, set]:
    """Return (science_names, regional_names, global_names)."""
    science = set()
    regional = set()
    global_ = set()

    for name, cats in name_to_cats.items():
        is_regional = False
        is_science = False

        for v, c in cats:
            if (v, c) in REGIONAL_CATS:
                is_regional = True
            if (v, c) in SCIENCE_VARIANT_CATS or (v == TECH_VARIANT and c != 'regionalStartups'):
                is_science = True

        if is_regional:
            regional.add(name)
        elif is_science:
            science.add(name)
        else:
            global_.add(name)

    return science, regional, global_


# ── Top 10 globally representative news outlets ──────────────────────────────

# Ranked by global reach, authority, and breadth of coverage
GLOBAL_TOP10 = [
    'BBC World',
    'Guardian World',
    'UN News',
    'Financial Times',
    'White House',          # US government, global policy impact
    'Federal Reserve',      # global financial system
    'WHO',                  # global health authority
    'Foreign Affairs',      # premier IR journal
    'Foreign Policy',       # global policy analysis
    'CNBC',                 # global business news
]


def main():
    name_to_cats = parse_feeds_ts(FEEDS_TS)
    print(f'Parsed {len(name_to_cats)} unique names from feeds.ts')

    # Classify all feeds in feeds.ts
    science_names, regional_names, global_names = classify(name_to_cats)
    print(f'Science/Tech: {len(science_names)} feeds')
    print(f'Regional:     {len(regional_names)} feeds')
    print(f'Global other: {len(global_names)} feeds')

    # Load current feeds.txt
    with open(FEEDS_TXT, 'r', encoding='utf-8') as f:
        current_feeds = json.load(f)
    print(f'\nCurrent feeds.txt: {len(current_feeds)} feeds')

    # Apply rules
    result = {}
    kept_science = []
    kept_global = []
    dropped_regional = []
    dropped_global = []

    for name, url in current_feeds.items():
        if name in science_names:
            result[name] = url
            kept_science.append(name)
        elif name in regional_names:
            dropped_regional.append(name)
        elif name in global_names:
            if name in GLOBAL_TOP10:
                result[name] = url
                kept_global.append(name)
            else:
                dropped_global.append(name)
        else:
            # Not found in feeds.ts — keep (shouldn't happen)
            result[name] = url

    print(f'\n=== Results ===')
    print(f'Kept (science/tech): {len(kept_science)}')
    print(f'Kept (global top 10): {len(kept_global)}')
    print(f'Dropped (regional):   {len(dropped_regional)}')
    print(f'Dropped (global other): {len(dropped_global)}')
    print(f'Total kept: {len(result)}')

    print(f'\n--- Kept global top 10 ---')
    for n in kept_global:
        print(f'  {n}')

    print(f'\n--- Dropped regional ---')
    for n in sorted(dropped_regional):
        print(f'  {n}')

    print(f'\n--- Dropped global other ---')
    for n in sorted(dropped_global):
        print(f'  {n}')

    # Write
    with open(FEEDS_TXT, 'w', encoding='utf-8') as f:
        json.dump(result, f, ensure_ascii=False, indent=2)
    print(f'\nWritten {len(result)} feeds to {FEEDS_TXT}')


if __name__ == '__main__':
    main()
