"""
XSS 爬虫引擎配置模块

定义爬虫运行时配置参数
"""
from dataclasses import dataclass, field
from typing import Optional, List
import os


@dataclass
class CrawlerConfig:
    """爬虫配置类"""
    
    # 浏览器配置
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    
    # 超时配置（毫秒）
    navigation_timeout: int = 30000  # 30秒
    wait_for_load_timeout: int = 5000  # 5秒
    interaction_timeout: int = 3000  # 3秒
    
    # 并发配置
    max_concurrent_pages: int = 3
    
    # 爬取限制
    max_depth: int = 3
    max_pages_per_domain: int = 50
    scope_domains: List[str] = field(default_factory=list)  # 允许爬取的额外域名范围
    
    # 网络配置
    enable_javascript: bool = True
    block_resources: List[str] = field(default_factory=lambda: ["image", "stylesheet", "font", "media"])
    
    # 配置化: 代码开头应有配置区，可设置 MAX_CONCURRENCY (并发数), CRAWL_DEPTH (点击深度), GOSPIDER_PATH (工具路径)。
    
    # 交互配置
    enable_form_submission: bool = True
    enable_button_clicks: bool = True
    form_fill_timeout: int = 2000
    
    # 跨域捕获配置
    enable_cross_origin_capture: bool = True  # 启用跨域无差别捕获（关键！）
    
    # 安全配置
    respect_robots_txt: bool = False
    user_agent: Optional[str] = None
    
    # 调试配置
    debug: bool = False
    screenshot_on_error: bool = False
    
    @classmethod
    def from_env(cls) -> "CrawlerConfig":
        """从环境变量加载配置"""
        return cls(
            headless=os.getenv("CRAWLER_HEADLESS", "true").lower() == "true",
            browser_type=os.getenv("CRAWLER_BROWSER", "chromium"),
            navigation_timeout=int(os.getenv("CRAWLER_NAV_TIMEOUT", "30000")),
            max_depth=int(os.getenv("CRAWLER_MAX_DEPTH", "3")),
            max_pages_per_domain=int(os.getenv("CRAWLER_MAX_PAGES", "50")),
            debug=os.getenv("CRAWLER_DEBUG", "false").lower() == "true",
        )
