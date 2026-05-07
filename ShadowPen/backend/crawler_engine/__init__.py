"""
XSS Crawler Engine

Modular, loosely coupled XSS attack surface detection crawler
"""
from .crawler import XSSSurfaceCrawler, crawl_surface
from .config import CrawlerConfig
from .models import AttackSurface, CrawlResult, ParamType, SourceType

# Provide interface compatible with main.py
async def crawl_target(url: str, max_pages: int = 10) -> dict:
    """Crawl target URL (compatible interface)

    Args:
        url: Target URL
        max_pages: Maximum pages to crawl

    Returns:
        Dictionary containing attack surfaces
    """
    result = await crawl_surface(url, max_pages=max_pages)
    return result.to_dict()


__all__ = [
    "XSSSurfaceCrawler",
    "crawl_surface",
    "crawl_target",
    "CrawlerConfig",
    "AttackSurface",
    "CrawlResult",
    "ParamType",
    "SourceType",
]
