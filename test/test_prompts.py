"""Test prompt templates and topic loading."""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from prompts import (
    load_topics,
    FILTER_SYSTEM_PROMPT,
    build_filter_user_prompt,
    BATCH_FILTER_SYSTEM_PROMPT,
    build_batch_filter_user_prompt,
    SUMMARY_SYSTEM_PROMPT,
    SUMMARY_USER_PROMPT_TEMPLATE,
)


def test_load_topics_only_enabled():
    topics_path = os.path.join(os.path.dirname(__file__), '..', 'topics.txt')
    topics = load_topics(topics_path)
    assert len(topics) > 0
    for t in topics:
        assert 'OFF' not in t
        assert isinstance(t, str)


def test_filter_user_prompt_contains_topics_and_content():
    topics = ['Tech/AI', 'Finance/Markets']
    prompt = build_filter_user_prompt(topics, 'Test Title', 'Test Content')
    assert 'Tech/AI' in prompt
    assert 'Finance/Markets' in prompt
    assert 'Test Title' in prompt
    assert 'Test Content' in prompt
    assert '"topics"' in prompt


def test_filter_user_prompt_truncates_long_content():
    topics = ['Tech/AI']
    long_content = 'x' * 3000
    prompt = build_filter_user_prompt(topics, 'Title', long_content)
    assert len(long_content) > 2000
    assert 'x' * 2000 in prompt


def test_batch_filter_prompt_structure():
    topics = ['Tech/AI', 'Finance/Markets']
    items = [
        {'title': 'Item 1', 'content': 'Content 1'},
        {'title': 'Item 2', 'content': 'Content 2'},
    ]
    prompt = build_batch_filter_user_prompt(topics, items)
    assert 'Tech/AI' in prompt
    assert 'Finance/Markets' in prompt
    assert 'Item 0' in prompt
    assert 'Item 1' in prompt
    assert 'Content 1' in prompt
    assert 'Content 2' in prompt
    assert '"results"' in prompt
    assert '"index"' in prompt


def test_batch_filter_prompt_with_empty_items():
    topics = ['Tech/AI']
    prompt = build_batch_filter_user_prompt(topics, [])
    assert 'Tech/AI' in prompt
    assert 'No items' in prompt


def test_batch_system_prompt_exists():
    assert len(BATCH_FILTER_SYSTEM_PROMPT) > 0
    assert 'multiple' in BATCH_FILTER_SYSTEM_PROMPT.lower()


def test_summary_prompt_template_format():
    prompt = SUMMARY_USER_PROMPT_TEMPLATE.format(
        title='Test Title',
        content='Test Content'
    )
    assert 'Test Title' in prompt
    assert 'Test Content' in prompt
    assert 'summary' in prompt


def test_filter_system_prompt_exists():
    assert len(FILTER_SYSTEM_PROMPT) > 0
    assert 'news classifier' in FILTER_SYSTEM_PROMPT.lower()


def test_summary_system_prompt_exists():
    assert len(SUMMARY_SYSTEM_PROMPT) > 0
    assert 'news editor' in SUMMARY_SYSTEM_PROMPT.lower()
