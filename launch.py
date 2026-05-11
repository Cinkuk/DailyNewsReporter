#!/usr/bin/env python3
"""Daily Report: personal information assistant — main entry point.

Pipeline:
  1. Load API key and enabled topics
  2. Fetch RSS feeds, parse items
  3. Filter by latest_point (dedup), save raw items + latest_point to disk
  4. LLM batch topic classification — drop irrelevant items
  5. LLM summarization — generate Chinese summary per item
  6. Generate HTML report and save to archive
"""

import json
import os
import sys
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from llm import load_api_key, call_llm, call_llm_batch, BATCH_SIZE
from prompts import (
    load_topics,
    BATCH_FILTER_SYSTEM_PROMPT,
    build_batch_filter_user_prompt,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT_TEMPLATE,
)
from feed_fetcher import (
    load_feeds,
    fetch_all_feeds,
    filter_by_latest_point,
    save_raw_items,
    load_latest_point,
    save_latest_point,
    update_latest_point,
)
from report_generator import generate_html, save_report

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))


def step1_load_config():
    """Load API key, feeds, topics, and latest_point."""
    print('[1/6] Loading configuration...')

    api_key_path = os.path.join(PROJECT_ROOT, 'API_KEYS.txt')
    api_key = load_api_key(api_key_path)
    if not api_key:
        print('  ERROR: API key not found. Check API_KEYS.txt')
        sys.exit(1)

    feeds_path = os.path.join(PROJECT_ROOT, 'data', 'feeds.txt')
    feeds = load_feeds(feeds_path)
    print(f'  Loaded {len(feeds)} feeds')

    topics_path = os.path.join(PROJECT_ROOT, 'topics.txt')
    topics = load_topics(topics_path)
    print(f'  Loaded {len(topics)} enabled topics')

    latest_point_path = os.path.join(PROJECT_ROOT, 'data', 'latest_point')
    latest_point = load_latest_point(latest_point_path)
    print(f'  Loaded latest_point for {len(latest_point)} feeds')

    return api_key, feeds, topics, latest_point


def step2_fetch_feeds(feeds):
    """Fetch all RSS feeds and parse items. Failed feeds are skipped."""
    print('[2/6] Fetching feeds...')
    items = fetch_all_feeds(feeds)
    print(f'  Fetched {len(items)} items total')
    return items


def step3_filter_dedup(items, latest_point):
    """Filter by latest_point, save raw items + latest_point to disk."""
    print('[3/6] Filtering by latest_point...')
    new_items = filter_by_latest_point(items, latest_point)
    print(f'  New items: {len(new_items)} (dropped {len(items) - len(new_items)} duplicates)')

    if not new_items:
        print('  No new items. Exiting.')
        sys.exit(0)

    date_str = datetime.now().strftime('%Y-%m-%d-%H')
    raw_archive = os.path.join(PROJECT_ROOT, 'data', 'raw_archive')
    saved_path = save_raw_items(new_items, date_str, raw_archive)
    print(f'  Saved raw items to {saved_path}')

    # Update and persist latest_point immediately after fetch + dedup
    latest_point = update_latest_point(new_items, latest_point)
    latest_point_path = os.path.join(PROJECT_ROOT, 'data', 'latest_point')
    save_latest_point(latest_point, latest_point_path)
    print(f'  Latest_point saved ({len(latest_point)} feeds)')

    return new_items, latest_point


def step4_filter_topics_batch(items, topics, api_key):
    """Use LLM to classify items by topic in batches; drop irrelevant ones."""
    print('[4/6] Classifying by topic via LLM (batch mode)...')
    relevant = []
    total = len(items)

    for batch_start in range(0, total, BATCH_SIZE):
        batch = items[batch_start:batch_start + BATCH_SIZE]
        batch_end = min(batch_start + BATCH_SIZE, total)

        user_prompt = build_batch_filter_user_prompt(topics, batch)
        try:
            results, usage = call_llm_batch(
                api_key, BATCH_FILTER_SYSTEM_PROMPT, user_prompt
            )
            # Build index lookup from results
            topic_map = {}
            for r in results:
                idx = r.get('index', -1)
                matched = r.get('topics', [])
                if isinstance(idx, int) and matched:
                    topic_map[idx] = matched[0]  # primary topic

            for i, item in enumerate(batch):
                global_idx = batch_start + i
                if i in topic_map:
                    item['topic'] = topic_map[i]
                    relevant.append(item)

        except (json.JSONDecodeError, RuntimeError) as e:
            print(f'  WARN: Batch [{batch_start}:{batch_end}] failed: {e}')

        print(f'  Progress: {batch_end}/{total} | relevant: {len(relevant)}')

    print(f'  Relevant items: {len(relevant)} (dropped {total - len(relevant)})')
    return relevant


def step5_summarize(items, api_key):
    """Use LLM to generate Chinese summary for each relevant item."""
    print('[5/6] Generating summaries via LLM...')
    total = len(items)

    for i, item in enumerate(items):
        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
            title=item['title'],
            content=item['content'][:2000],
        )
        try:
            content, usage = call_llm(api_key, SUMMARY_SYSTEM_PROMPT, user_prompt)
            result = json.loads(content)
            item['summary'] = result.get('summary', content)
        except (json.JSONDecodeError, RuntimeError) as e:
            print(f'  WARN: LLM summary failed for "{item["title"][:40]}": {e}')
            item['summary'] = item['content'][:300]

        if (i + 1) % 10 == 0 or i == total - 1:
            print(f'  Progress: {i + 1}/{total}')

    return items


def step6_generate_report(items):
    """Generate HTML report and save."""
    print('[6/6] Generating report...')
    date_str = datetime.now().strftime('%Y-%m-%d')
    html_content = generate_html(items, date_str)
    report_archive = os.path.join(PROJECT_ROOT, 'data', 'report_archive')
    path = save_report(html_content, date_str, report_archive)
    print(f'  Report saved to {path}')
    return path


def main():
    print('=' * 60)
    print('  Daily Report Generator')
    print('=' * 60)

    # Step 1: Load configuration
    api_key, feeds, topics, latest_point = step1_load_config()

    # Step 2: Fetch feeds (failed feeds auto-skipped)
    items = step2_fetch_feeds(feeds)

    # Step 3: Dedup + save raw items + persist latest_point immediately
    new_items, latest_point = step3_filter_dedup(items, latest_point)

    # Step 4: LLM batch topic classification
    relevant = step4_filter_topics_batch(new_items, topics, api_key)

    # Step 5: LLM summarization
    summarized = step5_summarize(relevant, api_key)

    # Step 6: Generate report
    report_path = step6_generate_report(summarized)

    print()
    print(f'Done. Report: {report_path}')


if __name__ == '__main__':
    main()
