import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))
from feed_parser import InfoItem


def load_topics(topics_path: str) -> list[(str, str)]:
    """Load enabled topics from topics.txt. Returns list of topic names with ON status."""
    topics = []
    with open(topics_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            if ':' in line:
                name, status = line.split(':', 1)
                topics.append((name.strip(), status.strip()))
    return topics


def load_feeds(filepath: str) -> dict:
    """Load feeds from JSON file. Returns {name: url}."""
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)
    

def load_latest_point(filepath: str) -> dict:
    """Load latest_point JSON. Returns {feed_name: 'YYYY-MM-DD HH:MM'}."""
    if not os.path.exists(filepath):
        return {}
    with open(filepath, 'r', encoding='utf-8') as f:
        return json.load(f)


def save_latest_point(data: dict, filepath: str) -> None:
    """Save latest_point as JSON."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def save_items(items: list[InfoItem], date_str: str, archive_dir: str) -> str:
    """Save raw items to archive_dir/<date_str>.json. Returns the file path."""
    os.makedirs(archive_dir, exist_ok=True)
    filepath = os.path.join(archive_dir, f'{date_str}.json')
    items_dict = []
    for item in items:
        items_dict.append(item.item())
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(items_dict, f, ensure_ascii=False, indent=2)
    return filepath