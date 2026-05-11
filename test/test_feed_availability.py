"""Check availability of each feed in feeds.txt.

Reports: HTTP status, parse result, item count, content quality.
"""

import json
import os
import sys
import time
import urllib.request
import ssl

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

import feedparser


def check_feed(name: str, url: str, timeout: int = 20) -> dict:
    """Check a single feed. Returns dict with status info."""
    result = {
        'name': name,
        'url': url,
        'status': 'unknown',
        'http_status': None,
        'entries': 0,
        'has_content': 0,
        'has_summary_only': 0,
        'error': None,
    }

    try:
        # feedparser can take a URL directly
        parsed = feedparser.parse(url)
    except Exception as e:
        result['status'] = 'exception'
        result['error'] = str(e)[:200]
        return result

    # Check for bozo (parse error)
    if parsed.bozo:
        bozo_msg = str(getattr(parsed, 'bozo_exception', 'unknown'))
        # HTTP status from feedparser
        status_code = getattr(parsed, 'status', None)
        result['http_status'] = status_code
        if status_code and status_code >= 400:
            result['status'] = f'http_{status_code}'
            result['error'] = bozo_msg[:200]
            return result
        elif not parsed.entries:
            result['status'] = 'parse_error_no_entries'
            result['error'] = bozo_msg[:200]
            return result

    result['http_status'] = getattr(parsed, 'status', 200)
    result['entries'] = len(parsed.entries)

    if result['entries'] == 0:
        result['status'] = 'empty'
        return result

    # Analyze content quality
    has_content = 0
    has_summary_only = 0
    for entry in parsed.entries:
        content = entry.get('content')
        summary = entry.get('summary')
        if content and isinstance(content, list) and len(content) > 0:
            has_content += 1
        elif summary:
            has_summary_only += 1

    result['has_content'] = has_content
    result['has_summary_only'] = has_summary_only

    if has_content > 0:
        result['status'] = 'ok_full'
    else:
        result['status'] = 'ok_summary_only'

    return result


def main():
    feeds_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'feeds.txt'
    )
    with open(feeds_path, 'r', encoding='utf-8') as f:
        feeds = json.load(f)

    total = len(feeds)
    results = []
    ok_full = []
    ok_summary = []
    failed = []

    print(f'Checking {total} feeds...\n')

    for i, (name, url) in enumerate(feeds.items()):
        print(f'[{i+1:3d}/{total}] {name[:50]}...', end=' ', flush=True)
        r = check_feed(name, url)
        results.append(r)

        if r['status'].startswith('ok'):
            print(f'{r["status"]} ({r["entries"]} items)')
            if r['status'] == 'ok_full':
                ok_full.append(r)
            else:
                ok_summary.append(r)
        else:
            err = r.get('error') or ''
            print(f'FAIL: {r["status"]} — {err[:80]}')
            failed.append(r)

        time.sleep(0.3)  # Be polite to servers

    # Summary
    print(f'\n{"="*60}')
    print(f'SUMMARY')
    print(f'{"="*60}')
    print(f'Total:          {total}')
    print(f'OK (full text): {len(ok_full)}')
    print(f'OK (summary):   {len(ok_summary)}')
    print(f'Failed:         {len(failed)}')

    if failed:
        print(f'\n--- Failed feeds ---')
        for r in failed:
            print(f'  [{r["status"]}] {r["name"]}')
            print(f'    URL: {r["url"]}')
            print(f'    Error: {r["error"]}')

    if ok_summary:
        print(f'\n--- Summary-only feeds ---')
        for r in ok_summary:
            print(f'  {r["name"]} ({r["entries"]} items)')

    # Save detailed report
    report_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'temp', 'feed_check_report.json'
    )
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\nDetailed report saved to {report_path}')


if __name__ == '__main__':
    main()
