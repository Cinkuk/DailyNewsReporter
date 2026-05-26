"""
router of parser. allocate feed to corresponding parser
"""

from feed_parser import (BaseParser, CustomRSSParser, arXivParser, NatureNewsParser)

class router():
    def __init__(self) -> None:
        self.router_map = {
            "BBC World": BaseParser,
            "Guardian World": BaseParser,
            "Ars Technica": BaseParser,
            "The Verge AI": BaseParser,
            "CNBC": BaseParser,
            "Financial Times": BaseParser,
            "UN News": BaseParser,
            "WHO": BaseParser,
            "TechCrunch Layoffs": BaseParser,
            "Crunchbase News": BaseParser,
            "a16z Blog": BaseParser,
            "Stratechery": BaseParser,
            "YC Blog": BaseParser,
            "Krebs Security": BaseParser,
            "Politico Tech": BaseParser,
            "CNBC Tech": BaseParser,
            "Product Hunt": BaseParser,
            "SemiAnalysis": BaseParser,
            "ScienceDaily": BaseParser,
            "Mongabay": BaseParser,

            "MIT Tech Review": CustomRSSParser,
            "VentureBeat": CustomRSSParser,
            "The New Stack": CustomRSSParser,
            "Singularity Hub": CustomRSSParser,
            "Human Progress": CustomRSSParser,
            "联合早报": CustomRSSParser,
            "南方周末": CustomRSSParser,

            "ArXiv AI": arXivParser,
            "Nature News": NatureNewsParser
            }
        self.feeds = self.router_map.keys()

    """
    return corresponding parser. 
    if input a invalid name, return None
    @param feed str, feed's name
    @return corresponding parser or None
    """
    def route(self, feed: str):
        if not feed in self.feeds:
            return None
        return self.router_map[feed]