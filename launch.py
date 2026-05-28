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
from typing import Literal, List

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from logger import Category as C, Logger
from utils import (
    load_topics,
    load_feeds,
    load_latest_point,
    save_latest_point,
    save_items,
)
from feed_parser import InfoItem
from feed_collect import Collector
from llm import load_api_key, call_llm, call_llm_batch, BATCH_SIZE
from prompts import (
    BATCH_FILTER_SYSTEM_PROMPT,
    build_batch_filter_user_prompt,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT_TEMPLATE,
)

from report_generator import generate_html, save_report

PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))

kLogger = Logger("main")
kLogger_LLM = Logger("LLM")
kLogger_ERROR = Logger("ERRPR")

def lprint(category: Literal[C.INFO, C.WARN, C.ERR], msg: str, llm: bool =False):
    if llm:
        kLogger_LLM.log(category, msg)
    else:
        kLogger.log(category, msg)


# reset global exception handler
def SetGlobalExceptionHook(exception_type, exception_value, exception_traceback):
    def eprint(msg: str):
        kLogger_ERROR.log(C.ERR, msg)

    def hook(type, value, traceback):
        eprint(f"Unexpected error: [Type]: {type.__name__}; [Infomation]: {value}")
        eprint("Error detail: ")
        while traceback.tb_next:
            tb = traceback.tb_next
            traceback = tb

            filename = tb.tb_frame.f_code.co_filename
            lineno = tb.tb_lineno
            eprint(f"[file]: {filename}, [line]: {lineno}")
        eprint(f"[error]: {str(value)}")
    
    hook(exception_type, exception_value, exception_traceback)
sys.excepthook = SetGlobalExceptionHook


def step1_load_config():
    """Load API key, feeds, topics, and latest_point."""
    lprint(C.INFO, '[1/5] Loading configuration...')

    api_key_path = os.path.join(PROJECT_ROOT, 'API_KEYS.txt')
    api_key = load_api_key(api_key_path)
    if not api_key:
        lprint(C.ERR, 'ERROR: API key not found. Check API_KEYS.txt')
        sys.exit(1)

    feeds_path = os.path.join(PROJECT_ROOT, 'data', 'feeds.txt')
    feeds = load_feeds(feeds_path)
    lprint(C.INFO, f'Loaded {len(feeds)} feeds')

    topics_path = os.path.join(PROJECT_ROOT, 'topics.txt')
    topics = load_topics(topics_path)
    lprint(C.INFO, f'Loaded {len(topics)} enabled topics')

    latest_point_path = os.path.join(PROJECT_ROOT, 'data', 'latest_point')
    latest_point = load_latest_point(latest_point_path)
    lprint(C.INFO, f'Loaded latest_point for {len(latest_point)} feeds')

    return api_key, feeds, topics, latest_point


def step2_collect_and_filter_items(feeds, latest_points):
    """
    collect new items from feeds and return their new latest points
    @return filtered_items: List[InfoItem], 
            new_latest_points: dict{feed_name, time_str}
    """
    lprint(C.INFO, '[2/5] Collecting new items...')

    new_item_collector = Collector(feeds, latest_points)
    filtered_items = new_item_collector.collect()
    new_latest_points = new_item_collector.GetLatestPoint()

    return filtered_items, new_latest_points


def step3_filter_topics_batch(items: List[InfoItem], topics, api_key):
    """Use LLM to classify items by topic in batches; drop irrelevant ones."""
    lprint(C.INFO, '[3/5] Classifying by topic via LLM (batch mode)...')
    relevant = []
    total = len(items)
    topics_value = []
    topics_status = dict()
    for topic, status in topics:
        topics_value.append(topic)
        topics_status[topic] = status

    for batch_start in range(0, total, BATCH_SIZE):
        batch = items[batch_start:batch_start + BATCH_SIZE]
        batch_end = min(batch_start + BATCH_SIZE, total)

        user_prompt = build_batch_filter_user_prompt(topics_value, batch)
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
                    item.SetCategory(topic_map[i])
                    if topics_status[topic_map[i]] == "ON":
                        relevant.append(item)
                else: item.SetCategory("others") # irrelevant

        except (json.JSONDecodeError, RuntimeError) as e:
            lprint(C.ERR, f'WARN: Batch [{batch_start}:{batch_end}] failed: {e}', llm=True)

        lprint(C.INFO, f'Progress: {batch_end}/{total} | relevant: {len(relevant)}', llm=True)

    lprint(C.INFO, f'Relevant items: {len(relevant)} (discard {total - len(relevant)})')
    return relevant


def step4_summarize(items: List[InfoItem], api_key):
    """Use LLM to generate Chinese summary for each relevant item."""
    lprint(C.INFO, '[4/5] Generating summaries via LLM...')
    total = len(items)

    for i, item in enumerate(items):
        user_prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
            title=item.title_,
            content=item.content_[:2000],
        )
        try:
            content, usage = call_llm(api_key, SUMMARY_SYSTEM_PROMPT, user_prompt)
            result = json.loads(content)
            item.SetSummary(result.get('summary', content))
        except (json.JSONDecodeError, RuntimeError) as e:
            lprint(C.WARN, f'WARN: LLM summary failed for "{item.title_[:40]}": {e}', llm=True)
            item.SetSummary(item.content_)

        if (i + 1) % 10 == 0 or i == total - 1:
            lprint(C.INFO, f'Progress: {i + 1}/{total}', llm=True)

    return items


def step6_generate_report(items):
    """Generate HTML report and save."""
    lprint(C.INFO, '[5/5] Generating report...')
    date_str = datetime.now().strftime('%Y-%m-%d-%H-%M')
    items[:] = [entry.item() for entry in items] # replace InfoItem with dict
    html_content = generate_html(items, date_str)
    report_archive = os.path.join(PROJECT_ROOT, 'data', 'report_archive')
    path = save_report(html_content, date_str, report_archive)
    lprint(C.INFO, f'Report saved to {path}')
    return path


def main():
    lprint(C.INFO, 'Daily Report Generator Start')

    # Step 1: Load configuration
    api_key, feeds, topics, latest_point = step1_load_config()

    # Step 2: Fetch feeds and discard outdated items
    new_items, new_latest_point = step2_collect_and_filter_items(
        feeds, 
        latest_point)

    # save new latest points
    latest_point_path = os.path.join(PROJECT_ROOT, 'data', 'latest_point')
    save_latest_point(new_latest_point, latest_point_path)
    lprint(C.INFO, f'Saved latest_point to {latest_point_path}')

    # Step 3: LLM batch topic classification
    relevant = step3_filter_topics_batch(new_items, topics, api_key)

    # Step 4: LLM summarization
    summarized = step4_summarize(relevant, api_key)

    # Step 5: save summarized data
    date_str = datetime.now().strftime('%Y-%m-%d-%H-%M')
    raw_archive = os.path.join(PROJECT_ROOT, 'data', 'raw_archive')
    saved_path = save_items(new_items, date_str, raw_archive)
    lprint(C.INFO, f'Saved raw items to {saved_path}')

    # Step 6: Generate report
    report_path = step6_generate_report(summarized)

    lprint(C.INFO, f'Done. Report: {report_path}')


if __name__ == '__main__':
    main()