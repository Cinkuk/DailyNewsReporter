import pytest
import requests
from lxml import (html, etree)

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from feed_parser import InfoItem, request_url, CustomRSSParser, arXivParser

urls = {
"MIT Tech Review": "https://www.technologyreview.com/feed/",
"VentureBeat": "https://venturebeat.com/feed/",
"The New Stack": "https://thenewstack.io/feed/",
"Singularity Hub": "https://singularityhub.com/feed/",
"Human Progress": "https://humanprogress.org/feed/",
"Nature News": "https://feeds.nature.com/nature/rss/current",
"联合早报": "https://plink.anyfeeder.com/zaobao/realtime/china",
"南方周末": "https://rsshub.rssforever.com/infzm/2"
}


def test_custom_rss_parser():
    for name, url in urls.items():
        print("=" * 60)
        print(f"[feed] {name}")
        print("=" * 60)
        
        response = request_url(url)
        if response[1] != 200:
            break
        parser = CustomRSSParser(response[0])
        results = parser.parse()

        for entry in results:
            entry = entry.item()
            print(entry["title"])
            print(entry["url"])
            print(entry["date"])
            print(entry["content"])
            break
        
        print()

def test_arxiv_parser():
    name, url = ("ArXiv AI", "https://arxiv.org/list/cs.AI/new?skip=0&show=100")

    print("=" * 60)
    print(f"[feed] {name}")
    print("=" * 60)
    
    response = request_url(url)
    if response[1] != 200:
        print(f"wrong status code: {response[1]}")
        return
    parser = arXivParser(response[0])
    results = parser.parse()

    for entry in results:
        entry = entry.item()
        print(entry["title"])
        print(entry["url"])
        print(entry["date"])
        print(entry["content"])
        break
    
    print()


if __name__ == "__main__":
    # test_custom_rss_parser()
    test_arxiv_parser()