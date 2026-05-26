"""
implements of feed parsers. 
These parsers receive data from web collected by fetcher, 
and return formated data.

return data's format:
[{
    url: str,
    title: str,
    date: str("%YY-%mm-%DD %HH:%MM%SS"),
    content: str
}, ...]
"""

from feed_requests import request_url

from logger import Category as C, Logger

import feedparser
from lxml import (html, etree)
import re
from datetime import datetime, timezone, timedelta

from typing import List
from time import strftime

# data structure
class InfoItem():
    def __init__(self, url: str, title: str, date: str, content: str) -> None:
        self.url_ = url
        self.title_ = title
        self.date_ = date
        self.content_ = content
        self.category_ = ""
        self.summary_ = ""
    
    def item(self) -> dict:
        return {
            "url": self.url_,
            "title": self.title_,
            "date": self.date_,
            "content": self.content_,
            "category": self.category_,
            "summary": self.summary_,
            } 

    def SetCategory(self, content: str):
        if isinstance(content, str):
            self.category_ = content
    
    def SetSummary(self, content: str):
        if isinstance(content, str):
            self.summary_ = content

"""
parser base 
@param: feedparser.util.FeedParserDict (return from feedparser.parse(url))
@return: list[InfoItem]

Using Base Parser: 
BBC World
Guardian World
Ars Technica
The Verge AI
CNBC
Financial Times
UN News
WHO
TechCrunch Layoffs
Crunchbase News
a16z Blog
Stratechery
YC Blog
Krebs Security
Politico Tech
CNBC Tech
Product Hunt
SemiAnalysis
ScienceDaily
Mongabay
"""
class BaseParser():
    def __init__(self, parse):
        self.parse_ = parse
        # empty parse result or 
        if (not hasattr(self.parse_, "entries")) or \
            len(self.parse_.entries) == 0:
            self.parse_ = [] # adapt to following procedure 
        self.logger_ = Logger("Parser 'BaseParser'")
    
    def parse(self) -> List[InfoItem]:
        items = []
        for entry in self.parse_:
            keys = entry.keys()
            if "title" in keys: title = entry["title"]
            else: title = ""
            if "link" in keys: link = entry["link"]
            else: link = ""
            if "summary" in keys: content = entry["summary"]
            else: content = ""
            if "published_parsed" in keys: date = strftime("%Y-%m-%d %H:%M:%S", entry["published_parsed"])
            else: date = ""

            item = InfoItem(url=link, title=title, date=date, content=content)
            items.append(item.item())
        
        # log
        self.logger_.log(C.INFO, 
                        f"fetch {len(items)} items")
        
        return items


"""
Custom RSS parser
@param: requests.models.Response (return from requests.get(url)
@return: list[InfoItem]

Using Custom Parser: 
MIT Tech Review
VentureBeat
The New Stack
Singularity Hub
Human Progress
联合早报
南方周末
"""
class CustomRSSParser():
    def __init__(self, html_response):
        self.html_ = html_response
        self.logger_ = Logger("Parser 'CustomRSSParser'")

    def parse(self) -> List[InfoItem]:
        items = []
        # invalid html response
        if not hasattr(self.html_, "text") or \
            not hasattr(self.html_, "status_code") or \
            self.html_.status_code != 200:
            return items
        # parse valid response
        # <item></item> item 
        # <title></title> title
        # <link></link> link
        # <pubDate></pubDate> date (e.g. Sat, 23 May 2026 10:00:00 GMT)
        # <p></p> in content:encode or <description></description>
        ns = {'content': 'http://purl.org/rss/1.0/modules/content/',
          'dc': 'http://purl.org/dc/elements/1.1/'}

        tree = html.fromstring(self.html_.text.encode("utf-8"), parser=etree.XMLParser(recover=True))
        html_items = tree.xpath("//item")
        for item in html_items:
            # 提取每个子元素的内容（文本）
            # 如果元素不存在，则设为空字符串
            title_el = item.find('title')
            title = title_el.text.strip() if title_el is not None else ''
            
            link_el = item.find('link')
            link = link_el.text.strip() if link_el is not None else ''
            
            pubdate_el = item.find('pubDate')
            pub_date = pubdate_el.text.strip() if pubdate_el is not None else ''
            if pub_date:
                date = self.format_time(pub_date)

            # 提取所有 <p> 标签的内容
            # 常见来源：<content:encoded> 或 <description>
            paragraphs = []
            
            # 尝试从 content:encoded 获取（处理命名空间）
            content_encoded = item.find('content:encoded', ns)
            if content_encoded is None:
                # 尝试 local-name 方式
                content_encoded = item.xpath('./*[local-name()="encoded" and namespace-uri()="http://purl.org/rss/1.0/modules/content/"]')
                content_encoded = content_encoded[0] if content_encoded else None
            
            if content_encoded is not None and content_encoded.text:
                # CDATA 内的 HTML 内容，先反转义（如果必要）然后解析为 HTML 片段
                html_content = content_encoded.text
                # 有时内容被转义，例如 &lt; 等，但 CDATA 内应该是未转义的原始 HTML
                # 我们直接解析
                fragment = etree.HTML(html_content)
                # 提取所有 <p> 标签
                p_els = fragment.xpath('//p')
                for p in p_els:
                    # 获取 <p> 内的纯文本，保留换行等
                    p_text = etree.tostring(p, method='text', encoding='unicode').strip()
                    if p_text:
                        paragraphs.append(p_text)
            
            # 如果 content:encoded 没有找到或没有内容，尝试从 description 提取
            if not paragraphs:
                desc_el = item.find('description')
                if desc_el is not None and desc_el.text:
                    html_content = desc_el.text
                    fragment = etree.HTML(html_content)
                    p_els = fragment.xpath('//p')
                    for p in p_els:
                        p_text = etree.tostring(p, method='text', encoding='unicode').strip()
                        if p_text:
                            paragraphs.append(p_text)
            content = "\n\n".join(paragraphs)

            item = InfoItem(url=link, title=title, date=date, content=content)
            items.append(item)
        
        # log
        self.logger_.log(C.INFO, 
                        f"fetch {len(items)} items")
    
        return items
    

    """
    convert timezone to UTC+8 and fotmat to %YY-%mm-%DD %HH:%MM:%SS
    @param time_str: str
    @return str
    """
    def format_time(self, time_str: str) -> str:
        if time_str.startswith(('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')):
            time_str = time_str.split(', ', 1)[1]

        if time_str.endswith("GMT"):
            dt = datetime.strptime(time_str, "%d %b %Y %H:%M:%S GMT")
            dt = dt.replace(tzinfo=timezone.utc)
        elif "+" in time_str or "-" in time_str:
            dt = datetime.strptime(time_str, "%d %b %Y %H:%M:%S %z")
        else:
            try:
                parts = map(str, list(time_str.split(" ")))[:4]
                time_str = " ".join(parts)
                dt = datetime.strptime(time_str, "%d %b %Y %H:%M:%S")
            except:
                dt = ""

        # timezone -> UTC+8
        zone = timezone(timedelta(hours=8))
        if dt:
            utc8_time = dt.astimezone(zone).strftime("%Y-%m-%d %H:%M:%S")
        else:
            utc8_time = "" 
        
        return utc8_time


"""
parser for arXiv AI page
@param: requests.models.Response (return from requests.get(url)
@return: list[InfoItem]
"""
class arXivParser():
    def __init__(self, response):
        self.response_ = response
        self.logger_ = Logger("Parser 'arXivParser'")
    
    def parse(self) -> List[InfoItem]:
        tree = html.fromstring(self.response_.text)

        # 1. Extract date from <h3> starting with "Showing new listings for"
        # Use xpath to find the h3 element with text starting with that phrase
        h3_nodes = tree.xpath("//h3[starts-with(text(), 'Showing new listings for')]")
        if h3_nodes:
            date_text = h3_nodes[0].text_content().strip()
            # Remove prefix
            date_part = date_text.replace('Showing new listings for', '').strip()
            # Parse date (e.g. "Friday, 22 May 2026")
            # Use datetime.strptime with English locale (assumes system supports it)
            parsed_date = datetime.strptime(date_part, '%A, %d %B %Y')
            formatted_date = parsed_date.strftime('%Y-%m-%d 00:00:00')
        else: formatted_date = ""

        # 2. Process each <dt> and its following <dd>
        items = []
        dt_elements = tree.xpath("//dt")
        for dt in dt_elements:
            # Find the next <dd> sibling (immediately following)
            dd_list = dt.xpath("following-sibling::dd[1]")
            if not dd_list:
                continue
            dd = dd_list[0]

            # Extract URL from <a> with title="Abstract" inside <dt>
            abstract_link = dt.xpath(".//a[@title='Abstract']/@href")
            if not abstract_link:
                continue
            relative_url = abstract_link[0]
            full_url = f"https://arxiv.org{relative_url}"

            # Extract title from <div class='list-title mathjax'>
            title_div = dd.xpath(".//div[@class='list-title mathjax']")
            if title_div:
                raw_title = title_div[0].text_content().strip()
                # Remove the "Title:" prefix (including any span content)
                title = re.sub(r'^Title:\s*', '', raw_title).strip()
            else:
                title = ''

            # Extract content from <p class='mathjax'>
            content_p = dd.xpath(".//p[@class='mathjax']")
            content = content_p[0].text_content().strip() if content_p else ''

            item = InfoItem(url=full_url, title=title, date=formatted_date, content=content)
            items.append(item)
        
        # log
        self.logger_.log(C.INFO, 
                        f"fetch {len(items)} items")

        return items
    

"""
parser for Nature News
@param: requests.models.Response (return from requests.get(url)
@return: list[InfoItem]
"""
class NatureNewsParser():
    def __init__(self, response):
        self.response_ = response
        self.logger_ = Logger("Parser 'NatureNewsParser'")
    
    """
    get all item in rss page,
    and parse url, title, date.
    @param requests.models.Response (return from requests.get(url)
    @return: list[{
                    "url": url,
                    "title": title,
                    "date": formatted_date
                }]
    """
    @staticmethod
    def get_items_metadata(html_content):
        tree = etree.fromstring(html_content.text.encode("utf-8"), parser=etree.XMLParser(recover=True))

        # 提取所有 <item> 元素（忽略命名空间前缀）
        items = tree.xpath("//*[local-name()='item']")

        result = []
        for item in items:
            # 1. 提取 URL：来自 rdf:about 属性（忽略命名空间）
            url_attr = item.xpath("@*[local-name()='about']")
            url = url_attr[0] if url_attr else ''

            # 2. 提取 title：来自 <title> 元素（忽略命名空间）
            title_elem = item.xpath(".//*[local-name()='title']")
            title = title_elem[0].text if title_elem else ''
            # 如果 title 为 None（如空标签），转为空字符串
            title = title or ''

            # 3. 提取日期：来自 <dc:date> 元素（忽略命名空间）
            date_elem = item.xpath(".//*[local-name()='date']")
            date_str = date_elem[0].text if date_elem else ''
            # 格式化日期
            formatted_date = ''
            if date_str and len(date_str) >= 10:
                formatted_date = f"{date_str[:10]} 00:00:00"

            result.append({
                "url": url,
                "title": title,
                "date": formatted_date
            })

        return result

    """
    get content from url
    @param url: str
    @return content: str
    """
    @staticmethod
    def get_content(url: str) -> str:
        response = request_url(url)

        tree = html.fromstring(response.text)
        div_xpath = "//div[@class='c-article-body main-content']"
        divs = tree.xpath(div_xpath)

        p_elements = divs[0].xpath(".//p")

        paragraphs = []
        for p in p_elements:
            p_str = p.text_content().strip()
            paragraphs.append(p_str)
        
        return "/n".join(paragraphs)
    
    def parse(self) -> List[InfoItem]:
        items = []
        items_on_page = self.get_items_metadata(self.response_)

        for item in items_on_page:
            url = item["url"]
            content = self.get_content(url)
            item["content"] = content
            items.append(InfoItem(
                url=item["url"],
                title=item["title"],
                date=item["date"],
                content=item["content"],
            ))
        
        # log
        self.logger_.log(C.INFO, 
                        f"fetch {len(items)} items")

        return items