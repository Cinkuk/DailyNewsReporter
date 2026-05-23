"""Check availability of each feed in feeds.txt with feedparser

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

# target key 
kTarget = [
        "title",
        "link",
        "summary",
        "author",
        "published_parsed"
    ]

# result file
file = open("feed_availability_result.md", mode="w+", encoding="utf8")

"""
check availability of specific key in specific feed
"""
def TryToGetItem(parsed: feedparser.util.FeedParserDict, name: str) -> bool:
    entry0 = parsed.entries[0]
    keys = entry0.keys()

    def character(key: bool)  -> str:
        if key: return "√"
        else: return "×"
    
    if name in keys: 
        found = True
        content = ""
        detail = ""
        if entry0[name]: 
            empty = False
            content = entry0[name]
            if isinstance(content, str):
                detail = f"len: {len(content)}"
            else:
                detail = time.strftime("%Y-%m-%d %H:%M:%S", content)
        else: 
            empty = True
        print(f"[Key] {name}, [found]: {character(found)}, [empty]: {character(empty)}, {detail}")
        if content:
            print(content[:70])
        return (found and (not empty))
    else: 
        found = False
        print(f"[Key] {name}, [found]: {character(found)}")
        return found


"""
check availability of specific entry
@return True: feed is available
@return False: feed is not available
"""
def test_feed(name: str, url: str) -> bool:
    print(f"[Feed] {name}")
    try:
        feed = feedparser.parse(url)
        key_availability = dict()
        for key in kTarget:
            avai = TryToGetItem(feed, key)
            key_availability[key] = "[x]" if avai else "[ ]"
        print()
        
        # write file
        line = f"| {name} |"
        for key in kTarget:
            line += f" {key_availability[key]} |"
        line += " [ ] |\n"
        file.write(line)

        return True
    except Exception as e:
        print(f"In parsing, type: {type(e).__name__}, detail: {e}")
        print()
        file.write(f"| {name } | [ ] | [ ] | [ ] | [ ] | [ ] |\n")
        return False


def main():
    feeds_path = os.path.join(
        os.path.dirname(__file__), '..', 'data', 'feeds.txt'
    )
    with open(feeds_path, 'r', encoding='utf-8') as f:
        feeds = json.load(f)

    # initial result file
    head = "| feed name | title | link | content | author | date | custom content format|\n"
    format = "|:---:|:---:|:---:|:---:|:---:|:---:|:---:|\n"
    file.write(head)
    file.write(format)
    
    total = len(feeds)
    ok = 0
    failed = 0

    for name, url in feeds.items():
        status = test_feed(name, url)
        if status: ok += 1
        else: failed += 1    

    # Summary
    print(f'\n{"="*60}')
    print(f'SUMMARY')
    print(f'{"="*60}')
    print(f'Total:          {total}')
    print(f'OK:             {ok}')
    print(f'Failed:         {failed}')

    file.close()

if __name__ == '__main__':
    main()
