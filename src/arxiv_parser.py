"""Specialized parser for ArXiv listing page (HTML).

URL pattern: https://arxiv.org/list/cs.AI/new?skip=0&show=100
Parses <dt>/<dd> pairs to extract paper title, authors, abstract, and ID.
"""

import re
import urllib.request
from datetime import datetime
from html.parser import HTMLParser


class ArxivListingParser(HTMLParser):
    """Parse ArXiv listing HTML into structured paper entries."""

    def __init__(self):
        super().__init__()
        self.entries: list[dict] = []
        self._current: dict | None = None
        self._in_dt = False
        self._in_dd = False
        self._in_title = False
        self._in_authors = False
        self._in_abstract = False
        self._text_buf: list[str] = []
        self._title_text: list[str] = []
        self._authors_text: list[str] = []
        self._abstract_text: list[str] = []
        self._arxiv_id = ''
        self._last_tag: str = ''

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        self._last_tag = tag

        if tag == 'dt':
            self._in_dt = True
            self._arxiv_id = ''
        elif tag == 'dd':
            self._in_dd = True
            self._in_title = False
            self._in_authors = False
            self._in_abstract = False
            self._title_text = []
            self._authors_text = []
            self._abstract_text = []
        elif self._in_dd:
            cls = attrs_dict.get('class', '')
            if tag == 'div' and 'list-title' in cls:
                self._in_title = True
            elif tag == 'div' and 'list-authors' in cls:
                self._in_authors = True
            elif tag == 'p' and 'mathjax' in cls:
                self._in_abstract = True

        # Capture arXiv ID from <a href="/abs/XXXX.XXXXX">
        if self._in_dt and tag == 'a':
            href = attrs_dict.get('href', '')
            m = re.match(r'/abs/(\d+\.\d+)', href)
            if m:
                self._arxiv_id = m.group(1)

    def handle_endtag(self, tag):
        if tag == 'dt':
            self._in_dt = False
        elif tag == 'dd':
            self._in_dd = False
            # Finalize current entry
            if self._arxiv_id:
                title = ' '.join(self._title_text).strip()
                authors = ' '.join(self._authors_text).strip()
                abstract = ' '.join(self._abstract_text).strip()
                self.entries.append({
                    'arxiv_id': self._arxiv_id,
                    'title': title,
                    'authors': authors,
                    'abstract': abstract,
                })
            self._arxiv_id = ''
        elif self._in_dd:
            if tag == 'div' and self._in_title:
                self._in_title = False
            elif tag == 'div' and self._in_authors:
                self._in_authors = False
            elif tag == 'p' and self._in_abstract:
                self._in_abstract = False

    def handle_data(self, data):
        if self._in_title:
            text = data.strip()
            if text and text != 'Title:':
                self._title_text.append(text)
        elif self._in_authors:
            text = data.strip()
            if text and text != 'Authors:':
                self._authors_text.append(text)
        elif self._in_abstract:
            text = data.strip()
            if text:
                self._abstract_text.append(text)


def parse_arxiv_listing(html: str) -> list[dict]:
    """Parse ArXiv listing HTML, return list of paper entry dicts."""
    parser = ArxivListingParser()
    parser.feed(html)
    return parser.entries


def fetch_arxiv_items(feed_name: str, url: str) -> list[dict]:
    """Fetch ArXiv listing page and parse into standard feed items.

    Returns items with: feed, title, link, time, content
    content is the abstract; link points to the abs page.
    """
    try:
        req = urllib.request.Request(url, headers={'User-Agent': 'DailyReport/1.0'})
        with urllib.request.urlopen(req, timeout=30) as resp:
            html = resp.read().decode('utf-8', errors='replace')
    except Exception as e:
        print(f'  WARN: ArXiv fetch failed: {e}')
        return []

    entries = parse_arxiv_listing(html)
    if not entries:
        return []

    # Extract listing date from HTML
    date_match = re.search(
        r'Show\w+ new listings? for\s+([\w\s,]+ \d{4})', html
    )
    listing_date = date_match.group(1) if date_match else datetime.now().strftime('%Y-%m-%d')

    items = []
    for e in entries:
        content = e['abstract']
        if not content:
            continue
        item = {
            'feed': feed_name,
            'title': e['title'],
            'link': f'https://arxiv.org/abs/{e["arxiv_id"]}',
            'time': listing_date,
            'content': content,
        }
        items.append(item)

    return items
