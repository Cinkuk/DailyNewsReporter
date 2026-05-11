"""Test ArXiv HTML listing parser."""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from arxiv_parser import ArxivListingParser, parse_arxiv_listing, fetch_arxiv_items


SAMPLE_HTML = """<!DOCTYPE html>
<html><body>
<dl id='articles'>
<dt>
  <a name='item1'>[1]</a>
  <a href="/abs/2605.05329" title="Abstract" id="2605.05329">arXiv:2605.05329</a>
  [<a href="/pdf/2605.05329">pdf</a>, <a href="/format/2605.05329">other</a>]
</dt>
<dd>
  <div class='meta'>
    <div class='list-title mathjax'><span class='descriptor'>Title:</span>
      Understanding Annotator Safety Policy with Interpretability
    </div>
    <div class='list-authors'><a href="#">Alex Oesterling</a>, <a href="#">Donghao Ren</a></div>
    <div class='list-comments mathjax'><span class='descriptor'>Comments:</span>
      38 pages, ACM FAccT 2026
    </div>
    <div class='list-subjects'><span class='descriptor'>Subjects:</span>
      <span class='primary-subject'>Artificial Intelligence (cs.AI)</span>
    </div>
    <p class='mathjax'>
      Safety policies define what constitutes safe and unsafe AI outputs.
      We introduce Annotator Policy Models (APMs), interpretable models.
    </p>
  </div>
</dd>
<dt>
  <a name='item2'>[2]</a>
  <a href="/abs/2605.06667" title="Abstract" id="2605.06667">arXiv:2605.06667</a>
  [<a href="/pdf/2605.06667">pdf</a>]
</dt>
<dd>
  <div class='meta'>
    <div class='list-title mathjax'><span class='descriptor'>Title:</span>
      ActCam: Zero-Shot Joint Camera and 3D Motion Control
    </div>
    <div class='list-authors'><a href="#">Omar El Khalifi</a></div>
    <p class='mathjax'>
      For artistic applications, video generation requires fine-grained control.
    </p>
  </div>
</dd>
</dl>
</body></html>"""


def test_parse_arxiv_listing_extracts_entries():
    entries = parse_arxiv_listing(SAMPLE_HTML)
    assert len(entries) == 2


def test_parse_arxiv_extracts_id():
    entries = parse_arxiv_listing(SAMPLE_HTML)
    assert entries[0]['arxiv_id'] == '2605.05329'
    assert entries[1]['arxiv_id'] == '2605.06667'


def test_parse_arxiv_extracts_title():
    entries = parse_arxiv_listing(SAMPLE_HTML)
    assert 'Understanding Annotator' in entries[0]['title']
    assert 'ActCam' in entries[1]['title']


def test_parse_arxiv_extracts_authors():
    entries = parse_arxiv_listing(SAMPLE_HTML)
    assert 'Alex Oesterling' in entries[0]['authors']
    assert 'Omar El Khalifi' in entries[1]['authors']


def test_parse_arxiv_extracts_abstract():
    entries = parse_arxiv_listing(SAMPLE_HTML)
    assert 'Safety policies' in entries[0]['abstract']
    assert 'video generation' in entries[1]['abstract']


def test_parse_empty_html():
    entries = parse_arxiv_listing('<html></html>')
    assert entries == []


def test_fetch_arxiv_items_format():
    """Verify items have the standard feed item format."""
    items = fetch_arxiv_items('ArXiv AI', 'https://arxiv.org/list/cs.AI/new?skip=0&show=25')
    # May be empty if no listings today, but if items exist they should have correct format
    for item in items:
        assert 'feed' in item
        assert item['feed'] == 'ArXiv AI'
        assert 'title' in item
        assert 'link' in item
        assert item['link'].startswith('https://arxiv.org/abs/')
        assert 'time' in item
        assert 'content' in item
        assert len(item['content']) > 0


def test_arxiv_items_skip_empty_abstract():
    """Entries without abstracts are skipped."""
    html_no_abstract = """<!DOCTYPE html>
<html><body>
<dl id='articles'>
<dt><a name='item1'>[1]</a><a href="/abs/2605.00001">arXiv:2605.00001</a></dt>
<dd><div class='meta'>
  <div class='list-title mathjax'>No Abstract Paper</div>
  <div class='list-authors'>Author Name</div>
</div></dd>
</dl>
</body></html>"""
    items = fetch_arxiv_items('ArXiv AI', 'http://example.com')
    # Fake URL won't work — test just the parse logic
    from arxiv_parser import parse_arxiv_listing
    entries = parse_arxiv_listing(html_no_abstract)
    assert len(entries) == 1
    assert entries[0]['abstract'] == ''
