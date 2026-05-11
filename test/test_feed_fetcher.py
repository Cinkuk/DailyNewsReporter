"""Test RSS feed fetcher module."""

import json
import os
import sys
from unittest.mock import patch, MagicMock
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from feed_fetcher import (
    load_feeds,
    parse_feed_items,
    filter_by_latest_point,
    save_raw_items,
    load_latest_point,
    save_latest_point,
    create_item,
    fetch_all_feeds,
    _has_full_content,
)


def test_load_feeds():
    feeds_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'feeds.txt')
    feeds = load_feeds(feeds_path)
    assert isinstance(feeds, dict)
    assert len(feeds) > 0
    for name, url in feeds.items():
        assert isinstance(name, str)
        assert isinstance(url, str)
        assert url.startswith('http')


def test_create_item():
    item = create_item(
        feed_name='BBC World',
        title='Test News Title',
        link='https://example.com/news/1',
        published='Mon, 10 May 2026 12:00:00 GMT',
        content='This is the news content.'
    )
    assert item['feed'] == 'BBC World'
    assert item['title'] == 'Test News Title'
    assert item['link'] == 'https://example.com/news/1'
    assert 'content' in item
    assert 'time' in item


def test_has_full_content_true():
    """Atom-style content field means full text."""
    entry = {'content': [{'value': 'Full article text'}]}
    assert _has_full_content(entry) is True


def test_has_full_content_false_for_summary_only():
    """Summary-only entries have no 'content' field."""
    entry = {'summary': 'Just a summary'}
    assert _has_full_content(entry) is False


def test_has_full_content_empty_list():
    """Empty content list is not full content."""
    entry = {'content': []}
    assert _has_full_content(entry) is False


def test_parse_feed_items_prefers_full_content():
    """Full content: keep title, use full content."""
    with patch('feedparser.parse') as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[
                {
                    'title': 'News Item',
                    'link': 'https://example.com/1',
                    'published': 'Mon, 10 May 2026 10:00:00 GMT',
                    'summary': 'Short summary',
                    'content': [{'value': 'Full article content here'}],
                },
            ]
        )
        items = parse_feed_items('Test Feed', 'https://example.com/rss')
        assert len(items) == 1
        assert 'Full article content here' in items[0]['content']
        assert items[0]['title'] == 'News Item'  # title preserved


def test_parse_feed_items_summary_only_clears_title():
    """Summary-only: clear title, summary becomes content."""
    with patch('feedparser.parse') as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[
                {
                    'title': 'Some Clickbait Title',
                    'link': 'https://example.com/1',
                    'published': 'Mon, 10 May 2026 10:00:00 GMT',
                    'summary': 'Actual informative summary text',
                },
            ]
        )
        items = parse_feed_items('Test Feed', 'https://example.com/rss')
        assert len(items) == 1
        assert items[0]['title'] == ''  # title cleared
        assert items[0]['content'] == 'Actual informative summary text'


def test_parse_feed_items_with_mock():
    """Test that RSS XML is correctly parsed into items."""
    with patch('feedparser.parse') as mock_parse:
        mock_parse.return_value = MagicMock(
            entries=[
                {
                    'title': 'News Item 1',
                    'link': 'https://example.com/1',
                    'published': 'Mon, 10 May 2026 10:00:00 GMT',
                    'summary': 'Content of news item 1',
                },
                {
                    'title': 'News Item 2',
                    'link': 'https://example.com/2',
                    'published': 'Mon, 10 May 2026 11:00:00 GMT',
                    'summary': 'Content of news item 2',
                },
            ]
        )
        items = parse_feed_items('Test Feed', 'https://example.com/rss')
        assert len(items) == 2
        assert items[0]['feed'] == 'Test Feed'
        assert items[0]['title'] == ''  # summary-only clears title
        assert items[1]['title'] == ''


def test_fetch_all_feeds_skips_failed():
    """fetch_all_feeds should skip failed feeds and continue with others."""
    feeds = {
        'Good Feed': 'https://example.com/good.rss',
        'Bad Feed': 'https://example.com/bad.rss',
        'Another Good': 'https://example.com/another.rss',
    }

    def mock_parse(url):
        if 'bad' in url:
            raise Exception('Connection refused')
        if 'another' in url:
            return MagicMock(entries=[
                {'title': 'Item 2', 'link': 'https://x.com/2',
                 'published': 'Mon, 10 May 2026 10:00:00 GMT',
                 'content': [{'value': 'Full Content 2'}]},
            ])
        return MagicMock(entries=[
            {'title': 'Item 1', 'link': 'https://x.com/1',
             'published': 'Mon, 10 May 2026 10:00:00 GMT',
             'content': [{'value': 'Full Content 1'}]},
        ])

    with patch('feedparser.parse', side_effect=mock_parse):
        items = fetch_all_feeds(feeds)
        assert len(items) == 2
        titles = {item['title'] for item in items}
        assert titles == {'Item 1', 'Item 2'}


def test_filter_by_latest_point_keeps_newer():
    items = [
        {
            'feed': 'BBC',
            'title': 'Old News',
            'link': 'https://example.com/old',
            'time': '2026-05-10 08:00',
            'content': 'Old content',
        },
        {
            'feed': 'BBC',
            'title': 'New News',
            'link': 'https://example.com/new',
            'time': '2026-05-10 12:00',
            'content': 'New content',
        },
    ]

    latest = {'BBC': '2026-05-10 10:00'}
    filtered = filter_by_latest_point(items, latest)
    assert len(filtered) == 1
    assert filtered[0]['title'] == 'New News'


def test_filter_by_latest_point_no_latest_keeps_all():
    items = [
        {'feed': 'BBC', 'time': '2026-05-10 08:00'},
        {'feed': 'BBC', 'time': '2026-05-10 09:00'},
    ]
    filtered = filter_by_latest_point(items, {})
    assert len(filtered) == 2


def test_filter_by_latest_point_new_feed_keeps_all():
    """If a feed has no latest_point entry, keep all its items."""
    items = [
        {'feed': 'CNN', 'time': '2026-05-10 08:00'},
    ]
    latest = {'BBC': '2026-05-10 10:00'}
    filtered = filter_by_latest_point(items, latest)
    assert len(filtered) == 1


def test_save_and_load_latest_point():
    test_path = os.path.join(os.path.dirname(__file__), '..', 'data', 'temp', 'test_latest_point.json')
    current = {'BBC': '2026-05-10 12:00', 'CNN': '2026-05-10 11:00'}
    save_latest_point(current, test_path)

    loaded = load_latest_point(test_path)
    assert loaded == current

    # Clean up
    os.remove(test_path)


def test_save_raw_items():
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'temp')
    items = [
        {
            'feed': 'BBC',
            'title': '',
            'link': 'https://example.com',
            'time': '2026-05-10 12:00',
            'content': 'Summary as content',
        }
    ]
    saved_path = save_raw_items(items, '2026-05-10-12', test_dir)
    assert os.path.exists(saved_path)

    with open(saved_path, 'r') as f:
        loaded = json.load(f)
    assert len(loaded) == 1
    assert loaded[0]['feed'] == 'BBC'
    assert loaded[0]['title'] == ''
    assert loaded[0]['content'] == 'Summary as content'

    # Clean up
    os.remove(saved_path)
