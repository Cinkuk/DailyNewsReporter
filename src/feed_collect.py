"""
collect and filter parsed results:
1. append feed name 
2. map content to category 
3. generate summary 
4. provide external interface to get formatted data
"""

from feed_parser import InfoItem
from feed_router import router
from feed_requests import request_url

from logger import Category as C, Logger

from typing import List
from datetime import datetime
import json

class Collector():
    """
    feeds: item's format: feed_name: url.
        like: "arXiv": "arxiv.org/..."
    latest_point: item's format: feed_name: time_string
    record the latest published date of eath feed
        time_string: "%Y-%m-%d %H:%M:%S"
        like: "arXiv": "2026-02-18 00:12:02"
    """
    def __init__(self, feeds: dict, latest_point: dict):
        self.feeds_ = feeds
        self.latest_point_ = latest_point
        self.router_ = router()
        self.available_feeds = self.router_.feeds

        self.logger_ = Logger("Collector")
    

    """
    receive a feed, including its name and url
    return parsed results, each item in a InfoItem
    """
    def parse(self, feed: str, url: str) -> List[InfoItem]:
        items = []
        
        if not feed in self.available_feeds:
            return items
        
        response, status_code = request_url(url)
        if status_code != 200:
            return items
        parser = self.router_.route(feed)(response)
        items = parser.parse()
        return items
    

    """
    filter items via time. drop all items published before
    latest_point strictly.
    @param List[InfoItem]
    @return List[InfoItem]
    """
    def filter_time(self, items: List[InfoItem], latest_point: str):
        kept_items = []
        fmt = "%Y-%m-%d %H:%M:%S"

        if latest_point == "":
            latest_point = "1970-01-01 00:00:00"
        latest_point = datetime.strptime(latest_point, fmt)
        new_latest_point = latest_point
        for item in items:
            time_str = item.date_
            # empty published time
            if time_str == "":
                continue
            time = datetime.strptime(time_str, fmt)
            if time > latest_point:
                kept_items.append(item)
                if time > new_latest_point:
                    new_latest_point = time
        
        new_latest_point = datetime.strftime(new_latest_point, fmt)
        
        # log
        self.logger_.log(C.INFO, 
                        f"keep {len(kept_items)} items, discard {len(items) - len(kept_items)} items")

        return kept_items, new_latest_point


    """
    after initialize instance, 
    call this function to collect all new items
    @return new items: List[InfoItem]
    """
    def collect(self) -> List[dict]:
        # log 
        self.logger_.log(C.INFO, 
                         f"fetch feeds: {json.dumps(list(self.feeds_.keys()), ensure_ascii=False)}")

        filtered_items = []
        for feed_name, url in self.feeds_.items():
            # log
            self.logger_.log(C.INFO, 
                         f"fetch form {feed_name}")
            
            items = self.parse(feed_name, url)

            # handle latest_time not exists
            if not feed_name in self.latest_point_.keys():
                latest_time = ""
            else: latest_time = self.latest_point_[feed_name]

            kept_items, new_latest_time = self.filter_time(items, latest_time)

            for item in kept_items:
                item.SetFeed(feed_name)

            filtered_items.extend(kept_items)
            self.latest_point_[feed_name] = new_latest_time
        
        return filtered_items
    

    """return latest points"""
    def GetLatestPoint(self):
        return self.latest_point_