"""Test HTML report generator."""

import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from report_generator import generate_html, group_by_topic


def test_group_by_topic():
    items = [
        {'topic': 'Tech/AI', 'title': 'AI Breakthrough', 'summary': 'Summary 1', 'feed': 'The Verge', 'link': 'https://example.com/1', 'time': '2026-05-10 10:00'},
        {'topic': 'Tech/AI', 'title': 'New Model Released', 'summary': 'Summary 2', 'feed': 'Ars Technica', 'link': 'https://example.com/2', 'time': '2026-05-10 11:00'},
        {'topic': 'Finance/Markets', 'title': 'Market Rally', 'summary': 'Summary 3', 'feed': 'CNBC', 'link': 'https://example.com/3', 'time': '2026-05-10 12:00'},
    ]
    grouped = group_by_topic(items)
    assert len(grouped) == 2
    assert len(grouped['Tech/AI']) == 2
    assert len(grouped['Finance/Markets']) == 1


def test_generate_html_structure():
    items = [
        {
            'topic': 'Tech/AI',
            'title': 'Test News & Article',
            'summary': '这是一个测试摘要。',
            'feed': 'Test Feed',
            'link': 'https://example.com/test',
            'time': '2026-05-10 12:00',
        }
    ]
    html = generate_html(items, '2026-05-10')

    assert '<!DOCTYPE html>' in html
    assert '<html' in html
    assert 'Daily Report' in html
    assert '2026-05-10' in html
    assert 'Tech/AI' in html
    assert 'Test News &amp; Article' in html  # HTML escaped
    assert 'Test Feed' in html
    assert 'https://example.com/test' in html


def test_generate_html_escapes_special_chars():
    items = [
        {
            'topic': 'Tech/AI',
            'title': 'X < Y & Z > W',
            'summary': 'Summary with "quotes" & ampersand',
            'feed': 'Feed',
            'link': 'https://example.com',
            'time': '2026-05-10 12:00',
        }
    ]
    html = generate_html(items, '2026-05-10')
    assert 'X &lt; Y &amp; Z &gt; W' in html
    assert '&quot;quotes&quot; &amp; ampersand' in html


def test_generate_html_empty_items():
    html = generate_html([], '2026-05-10')
    assert '<!DOCTYPE html>' in html
    assert 'No news items' in html


def test_generate_html_multiple_topics_ordered():
    items = [
        {'topic': 'Finance/Markets', 'title': 'F2', 'summary': 'S', 'feed': 'F', 'link': 'https://x.com', 'time': '2026-05-10 10:00'},
        {'topic': 'Tech/AI', 'title': 'T1', 'summary': 'S', 'feed': 'F', 'link': 'https://x.com', 'time': '2026-05-10 10:00'},
        {'topic': 'Tech/AI', 'title': 'T2', 'summary': 'S', 'feed': 'F', 'link': 'https://x.com', 'time': '2026-05-10 11:00'},
    ]
    html = generate_html(items, '2026-05-10')

    # Topics should appear in order
    assert html.index('Finance/Markets') < html.index('Tech/AI')


def test_save_report():
    """Test that report is saved to correct path."""
    test_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'temp')
    os.makedirs(test_dir, exist_ok=True)

    html_content = '<html><body>Test Report</body></html>'
    from report_generator import save_report
    path = save_report(html_content, '2026-05-10', test_dir)

    assert os.path.exists(path)
    assert path.endswith('2026-05-10.html')

    with open(path, 'r') as f:
        assert f.read() == html_content

    os.remove(path)
