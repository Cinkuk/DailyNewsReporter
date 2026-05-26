import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from feed_collect import Collector

feeds = {
  "MIT Tech Review": "https://www.technologyreview.com/feed/",
  "ArXiv AI": "https://arxiv.org/list/cs.AI/new?skip=0&show=100",
  "南方周末": "https://rsshub.rssforever.com/infzm/2",
  "The Verge AI": "https://www.theverge.com/rss/ai-artificial-intelligence/index.xml",
}

latest_point = {
    "MIT Tech Review": "2026-05-26 00:00:00",
    "ArXiv AI": "2026-05-26 12:12:12",
    "The Verge AI": "2026-05-26 12:12:12",
    }

def test_collector():
    collector = Collector(feeds, latest_point)
    items = collector.collect()
    for item in items:
        print("="*50)
        print(item.item()["url"])
        print(item.item()["date"])
        print(item.item()["title"])
        print(item.item()["content"][:200])
        print()

if __name__ == "__main__":
    test_collector()
