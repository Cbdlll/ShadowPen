"""
XSS 爬虫引擎

模块化、高解耦的 XSS 攻击面探测爬虫
"""
from .crawler import XSSSurfaceCrawler, crawl_surface
from .config import CrawlerConfig
from .models import AttackSurface, CrawlResult, ParamType, SourceType

# 提供兼容 main.py 的接口
async def crawl_target(url: str, max_pages: int = 10) -> dict:
    """爬取目标 URL（兼容接口）
    
    Args:
        url: 目标 URL
        max_pages: 最大爬取页数
        
    Returns:
        包含攻击面的字典
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
