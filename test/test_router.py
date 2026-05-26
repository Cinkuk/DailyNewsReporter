import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from feed_parser import (BaseParser, CustomRSSParser, arXivParser, NatureNewsParser)
from feed_router import router

def test_router():
    parser_router = router()
    router_map = {
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
    for feed, parser in parser_router.router_map.items():
        assert(parser_router.route(feed) == router_map[feed] == parser)
        print(f"[feed] {feed} router map pass")
    
    assert(parser_router.route("fake feed") == None)