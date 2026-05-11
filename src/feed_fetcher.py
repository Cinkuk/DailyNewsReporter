"""RSS feed fetcher: fetch, parse, and filter feed items."""

import json
import os
import re
import sys
from datetime import datetime

import feedparser


def load_feeds(filepath: str) -> dict:
    """Load feeds from JSON file. Returns {name: url}."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def create_item(feed_name: str, title: str, link: str,
                published: str, content: str) -> dict:
    """Create a standardized feed item dict."""
    time_str = _normalize_time(published)
    return {
        'feed': feed_name,
        'title': title or '',
        'link': link or '',
        'time': time_str,
        'content': _clean_content(content),
    }


def _normalize_time(published: str) -> str:
    """Parse various time formats into YYYY-MM-DD HH:MM."""
    if not published:
        return datetime.now().strftime('%Y-%m-%d %H:%M')
    try:
        from email.utils import parsedate_to_datetime
        dt = parsedate_to_datetime(published)
        return dt.strftime('%Y-%m-%d %H:%M')
    except (ValueError, TypeError):
        return published


def _clean_content(content: str) -> str:
    """Strip HTML tags from content for cleaner text."""
    if not content:
        return ''
    clean = re.sub(r'<[^>]+>', '', content)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean


def _has_full_content(entry) -> bool:
    """Return True if entry has full-text content (Atom content field)."""
    content = entry.get('content')
    return bool(content and isinstance(content, list) and len(content) > 0)


def _extract_content(entry) -> str:
    """Extract the best available content from a feedparser entry.

    Prefers full-text content over summary. Handles both Atom (content list)
    and RSS (summary string) formats.
    """
    # Atom format: content is a list of dicts with 'value' key
    content = entry.get('content')
    if content and isinstance(content, list) and len(content) > 0:
        return content[0].get('value', '')

    # RSS format: summary / description
    summary = entry.get('summary', '')
    if summary:
        return summary

    # Fallback: try description, then title
    return entry.get('description', entry.get('title', ''))


def parse_feed_items(feed_name: str, feed_url: str) -> list[dict]:
    """Fetch and parse a single RSS/Atom feed. Returns list of item dicts.

    Routes ArXiv listing URLs to the specialized HTML parser.
    """
    # ArXiv listing page: use specialized HTML parser
    if 'arxiv.org/list/' in feed_url:
        from arxiv_parser import fetch_arxiv_items
        return fetch_arxiv_items(feed_name, feed_url)

    try:
        parsed = feedparser.parse(feed_url)
    except Exception as e:
        print(f'  WARN: Failed to fetch [{feed_name}]: {e}', file=sys.stderr)
        return []

    # Check for feed-level errors (e.g. HTTP errors, invalid XML)
    if parsed.bozo and not parsed.entries:
        bozo_msg = str(getattr(parsed, 'bozo_exception', 'unknown error'))
        print(f'  WARN: Feed parse error [{feed_name}]: {bozo_msg}', file=sys.stderr)
        return []

    items = []
    for entry in parsed.entries:
        has_full = _has_full_content(entry)
        content = _extract_content(entry)
        # Summary-only feeds: clear title, keep summary as content
        title = entry.get('title', '') if has_full else ''
        item = create_item(
            feed_name=feed_name,
            title=title,
            link=entry.get('link', ''),
            published=entry.get('published', ''),
            content=content,
        )
        items.append(item)
    return items


def fetch_all_feeds(feeds: dict) -> list[dict]:
    """Fetch all feeds and return combined list of items. Skip failed feeds."""
    all_items = []
    total = len(feeds)
    success = 0
    failed = 0

    for i, (name, url) in enumerate(feeds.items()):
        items = parse_feed_items(name, url)
        if items:
            all_items.extend(items)
            success += 1
        else:
            failed += 1

        if (i + 1) % 20 == 0 or i == total - 1:
            print(f'  Progress: {i + 1}/{total} feeds | {len(all_items)} items | {failed} failed')

    return all_items


def load_latest_point(filepath: str) -> dict:
    """Load latest_point JSON. Returns {feed_name: 'YYYY-MM-DD HH:MM'}."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_latest_point(data: dict, filepath: str) -> None:
    """Save latest_point as JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def filter_by_latest_point(items: list[dict], latest_point: dict) -> list[dict]:
    """Keep only items whose time is strictly later than the recorded latest_point for their feed."""
    filtered = []
    for item in items:
        feed = item['feed']
        item_time = item['time']
        last_time = latest_point.get(feed, '')
        if not last_time or item_time > last_time:
            filtered.append(item)
    return filtered


def save_raw_items(items: list[dict], date_str: str, archive_dir: str) -> str:
    """Save raw items to archive_dir/<date_str>.json. Returns the file path."""
    os.makedirs(archive_dir, exist_ok=True)
    filepath = os.path.join(archive_dir, f'{date_str}.json')
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(items, f, ensure_ascii=False, indent=2)
    return filepath


def update_latest_point(items: list[dict], latest_point: dict) -> dict:
    """Update latest_point dict with the newest time from each feed in items."""
    for item in items:
        feed = item['feed']
        item_time = item['time']
        if item_time > latest_point.get(feed, ''):
            latest_point[feed] = item_time
    return latest_point
