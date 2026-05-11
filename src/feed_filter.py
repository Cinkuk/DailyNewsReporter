"""Parse feeds.ts and filter to keep only direct RSS/XML feeds."""

import json
import re
import os


def is_direct_feed(url: str) -> bool:
    """Return True if url is a direct RSS/XML feed, not a Google News search."""
    return 'news.google.com' not in url


def parse_feeds_ts(filepath: str) -> list[dict]:
    """Parse feeds.ts and extract feed entries with name, url, and optional lang."""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()

    entries: list[dict] = []

    # Match feed entries: { name: '...', url: '...' OR url: gn('...'), lang?: '...' }
    pattern = re.compile(
        r"\{\s*"
        r"name:\s*'([^']+)'"
        r"\s*,\s*"
        r"url:\s*(?:gn\(('[^']*')\)|'([^']+)')"
        r"(?:\s*,\s*"
        r"lang:\s*'([^']+)'"
        r")?\s*"
        r"\}"
    )

    for m in pattern.finditer(content):
        name = m.group(1)
        gn_url = m.group(2)
        direct_url = m.group(3)
        lang = m.group(4)

        url = direct_url if direct_url else f"https://news.google.com/rss/search?q={gn_url}&hl=en-US&gl=US&ceid=US:en"

        entry = {'name': name, 'url': url}
        if lang:
            entry['lang'] = lang
        entries.append(entry)

    return entries


def filter_feeds(entries: list[dict]) -> list[dict]:
    """Keep only entries with direct RSS/XML URLs."""
    return [e for e in entries if is_direct_feed(e['url'])]


def save_feeds(entries: list[dict], filepath: str) -> None:
    """Save filtered feeds as JSON mapping name -> url.

    First occurrence of a name wins (preserves the more general URL
    when the same feed appears in multiple categories).
    """
    output = {}
    for e in entries:
        if e['name'] not in output:
            output[e['name']] = e['url']
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(output, f, ensure_ascii=False, indent=2)


def main():
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    feeds_ts_path = os.path.join(project_root, 'feeds.ts')
    output_path = os.path.join(project_root, 'data', 'feeds.txt')

    entries = parse_feeds_ts(feeds_ts_path)
    filtered = filter_feeds(entries)
    save_feeds(filtered, output_path)

    print(f"Total feeds parsed: {len(entries)}")
    print(f"Direct feeds kept: {len(filtered)}")
    print(f"Google News feeds dropped: {len(entries) - len(filtered)}")
    print(f"Saved to: {output_path}")


if __name__ == '__main__':
    main()
