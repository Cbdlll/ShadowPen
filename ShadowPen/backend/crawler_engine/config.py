"""
XSS Crawler Engine Configuration Module

Defines crawler runtime configuration parameters
"""
from dataclasses import dataclass, field
from typing import Optional, List
import os


@dataclass
class CrawlerConfig:
    """Crawler configuration class"""

    # Browser configuration
    headless: bool = True
    browser_type: str = "chromium"  # chromium, firefox, webkit
    
    # Timeout configuration (milliseconds)
    navigation_timeout: int = 30000  # 30 seconds
    wait_for_load_timeout: int = 5000  # 5 seconds
    interaction_timeout: int = 3000  # 3 seconds
    
    # Concurrency configuration
    max_concurrent_pages: int = 3
    
    # Crawl limits
    max_depth: int = 3
    max_pages_per_domain: int = 50
    scope_domains: List[str] = field(default_factory=list)  # Additional allowed domain scope for crawling
    
    # Network configuration
    enable_javascript: bool = True
    block_resources: List[str] = field(default_factory=lambda: ["image", "stylesheet", "font", "media"])
    
    # Configuration: Code header should have a config section for MAX_CONCURRENCY, CRAWL_DEPTH, GOSPIDER_PATH.

    # Interaction configuration
    enable_form_submission: bool = True
    enable_button_clicks: bool = True
    form_fill_timeout: int = 2000
    
    # Cross-origin capture configuration
    enable_cross_origin_capture: bool = True  # Enable cross-origin indiscriminate capture (critical!)
    
    # Security configuration
    respect_robots_txt: bool = False
    user_agent: Optional[str] = None
    
    # Debug configuration
    debug: bool = False
    screenshot_on_error: bool = False
    
    @classmethod
    def from_env(cls) -> "CrawlerConfig":
        """Load configuration from environment variables"""
        return cls(
            headless=os.getenv("CRAWLER_HEADLESS", "true").lower() == "true",
            browser_type=os.getenv("CRAWLER_BROWSER", "chromium"),
            navigation_timeout=int(os.getenv("CRAWLER_NAV_TIMEOUT", "30000")),
            max_depth=int(os.getenv("CRAWLER_MAX_DEPTH", "3")),
            max_pages_per_domain=int(os.getenv("CRAWLER_MAX_PAGES", "50")),
            debug=os.getenv("CRAWLER_DEBUG", "false").lower() == "true",
        )
