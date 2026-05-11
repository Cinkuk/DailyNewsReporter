"""Test feed filtering: keep only direct RSS/XML feeds, drop Google News gn() URLs."""

import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from feed_filter import parse_feeds_ts, is_direct_feed, filter_feeds


def test_is_direct_feed_keeps_rss_xml():
    assert is_direct_feed("https://feeds.bbci.co.uk/news/world/rss.xml") is True
    assert is_direct_feed("https://rss.dw.com/xml/rss-en-all") is True
    assert is_direct_feed("https://www.theguardian.com/world/rss") is True


def test_is_direct_feed_keeps_feed_paths():
    assert is_direct_feed("https://www.france24.com/en/rss") is True
    assert is_direct_feed("https://techcrunch.com/feed/") is True
    assert is_direct_feed("https://foreignpolicy.com/feed/") is True


def test_is_direct_feed_rejects_google_news():
    assert is_direct_feed(
        "https://news.google.com/rss/search?q=site%3Aapnews.com+when%3A1d&hl=en-US&gl=US&ceid=US:en"
    ) is False
    assert is_direct_feed(
        "https://news.google.com/rss/search?q=tech+layoffs+when%3A7d&hl=en-US&gl=US&ceid=US:en"
    ) is False


def test_is_direct_feed_rejects_gn_generated_urls():
    # Any URL containing news.google.com/rss/search should be rejected
    assert is_direct_feed(
        "https://news.google.com/rss/search?q=(OpenAI+OR+Anthropic+OR+Google+AI)&hl=en-US"
    ) is False


def test_parse_feeds_ts_extracts_entries():
    feeds_path = os.path.join(os.path.dirname(__file__), '..', 'feeds.ts')
    entries = parse_feeds_ts(feeds_path)
    assert len(entries) > 0
    for entry in entries:
        assert 'name' in entry
        assert 'url' in entry
        # lang is optional
        assert isinstance(entry['name'], str)
        assert isinstance(entry['url'], str)


def test_filter_feeds_keeps_only_direct():
    feeds_path = os.path.join(os.path.dirname(__file__), '..', 'feeds.ts')
    entries = parse_feeds_ts(feeds_path)
    filtered = filter_feeds(entries)
    for entry in filtered:
        assert is_direct_feed(entry['url']), f"Should be direct: {entry['name']} -> {entry['url']}"


def test_filter_feeds_drops_all_google_news():
    feeds_path = os.path.join(os.path.dirname(__file__), '..', 'feeds.ts')
    entries = parse_feeds_ts(feeds_path)
    filtered = filter_feeds(entries)
    for entry in filtered:
        assert 'news.google.com' not in entry['url'], \
            f"Should not contain Google News: {entry['name']} -> {entry['url']}"


def test_output_format():
    """Verify output can be serialized as JSON name->url mapping."""
    feeds_path = os.path.join(os.path.dirname(__file__), '..', 'feeds.ts')
    entries = parse_feeds_ts(feeds_path)
    filtered = filter_feeds(entries)
    output = {e['name']: e['url'] for e in filtered}
    serialized = json.dumps(output, ensure_ascii=False, indent=2)
    assert len(serialized) > 0
    parsed = json.loads(serialized)
    assert isinstance(parsed, dict)
    for name, url in parsed.items():
        assert isinstance(name, str)
        assert isinstance(url, str)
        assert 'news.google.com' not in url
