"""LLM prompt templates for news filtering and summarization."""

import json
from feed_parser import InfoItem


FILTER_SYSTEM_PROMPT = """You are a news classifier. Your task is to determine whether a news item is relevant to any of the given topic categories.

Rules:
1. Read the news title and content carefully.
2. If the news is relevant to one or more of the available topics, output the matching topic name(s).
3. If the news is NOT relevant to ANY topic, output an empty list.
4. Only use exact topic names from the provided list. Do not invent new categories.
5. Be inclusive: if a news item has even partial relevance to a topic, include it.
6. Response must be valid JSON only, no other text."""


def build_filter_user_prompt(topics: list[str], title: str, content: str) -> str:
    """Build user prompt for topic filtering (single item)."""
    return f"""Available topics:
{json.dumps(topics, ensure_ascii=False)}

News title: {title}

News content:
{content[:2000]}

Output format: {{"topics": ["TopicA", "TopicB"]}} or {{"topics": []}} if none match."""


# ── Batch classification prompts ──────────────────────────────────────────────

BATCH_FILTER_SYSTEM_PROMPT = """You are a news classifier. You will receive multiple news items at once. For EACH item, determine whether it is relevant to any of the given topic categories.

Rules:
1. Process every item independently.
2. If an item is relevant to one or more of the available topics, record the matching topic name(s).
3. If an item is NOT relevant to ANY topic, record an empty list for that item.
4. Only use exact topic names from the provided list. Do not invent new categories.
5. Be inclusive: if a news item has even partial relevance to a topic, include it.
6. Response must be valid JSON only, no other text."""


def build_batch_filter_user_prompt(topics: list[str], items: list[InfoItem]) -> str:
    """Build user prompt for batch topic filtering with multiple items."""
    if not items:
        return f"""Available topics:
{json.dumps(topics, ensure_ascii=False)}

No items to classify. Output: {{"results": []}}"""

    items_text = ''
    for i, item in enumerate(items):
        items_text += f'''
---
Item {i}:
Title: {item.title_}
Content: {item.content_[:1500]}
'''

    return f"""Available topics:
{json.dumps(topics, ensure_ascii=False)}

Classify each of the following {len(items)} news items:
{items_text}

Output format:
{{"results": [{{"index": 0, "topics": ["TopicA"]}}, {{"index": 1, "topics": []}}, ...]}}
Return exactly {len(items)} entries in the results array, one per item."""


# ── Summary prompts ────────────────────────────────────────────────────────────

SUMMARY_SYSTEM_PROMPT = """You are a professional news editor. Your task is to write a concise, accurate news summary in Chinese.

Rules:
1. Summarize the key facts: who, what, when, where, why.
2. Keep the summary under 300 Chinese characters (approximately 300 words).
3. Be objective and factual. Do not add opinions or commentary.
4. Preserve important numbers, dates, and names.
5. If the original content is not in Chinese, translate key terms appropriately but keep the summary in Chinese.
6. Response must be valid JSON only, no other text."""


SUMMARY_USER_PROMPT_TEMPLATE = """Summarize the following news item in Chinese (under 300 characters).

Title: {title}

Content:
{content}

Output format: {{"summary": "你的中文摘要..."}}"""
