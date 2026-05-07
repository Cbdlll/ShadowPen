"""
Global Deduplication Manager

Features:
- Global URL deduplication (avoids revisiting the same links)
- Smart element fingerprint deduplication (distinguishes common components from business components)
"""
import hashlib
import logging
from typing import Set, Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationConfig:
    """Deduplication configuration"""
    enable_global_url_dedup: bool = True        # Enable global URL deduplication
    enable_element_dedup: bool = True           # Enable element fingerprint deduplication
    navigation_dedup_scope: str = "root_domain" # Navigation component dedup scope (root_domain/full_path)
    business_dedup_scope: str = "full_path"     # Business component dedup scope


class GlobalDeduplicationManager:
    """Global Deduplication Manager (Singleton pattern)

    Strategy:
    1. Global URL deduplication - avoids revisiting the same links
    2. Mixed element deduplication - global dedup for navigation components, page-level dedup for business components
    """
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config: DeduplicationConfig = None):
        if self._initialized:
            return
        
        self.config = config or DeduplicationConfig()
        
        # Global deduplication sets
        self.visited_urls: Set[str] = set()
        self.clicked_signatures: Set[str] = set()
        
        # Statistics
        self.stats = {
            "url_skipped": 0,
            "element_skipped": 0,
            "url_visited": 0,
            "element_clicked": 0,
        }
        
        self._initialized = True
        logger.info("Global deduplication manager initialized")
    
    def reset(self):
        """Reset deduplication state (for testing)"""
        self.visited_urls.clear()
        self.clicked_signatures.clear()
        self.stats = {k: 0 for k in self.stats}
        logger.info("Deduplication manager reset")
    
    # ============ URL Deduplication ============
    
    def should_visit_url(self, url: str) -> bool:
        """Check whether a URL should be visited

        Args:
            url: URL to check

        Returns:
            True means it should be visited, False means skip
        """
        if not self.config.enable_global_url_dedup:
            return True
        
        normalized = self.normalize_url(url)
        
        if normalized in self.visited_urls:
            self.stats["url_skipped"] += 1
            logger.debug(f"Skipping already visited URL: {url}")
            return False
        
        self.visited_urls.add(normalized)
        self.stats["url_visited"] += 1
        return True
    
    def normalize_url(self, url: str) -> str:
        """URL normalization

        Rules:
        1. Remove fragment (#)
        2. Convert to lowercase
        3. Sort query parameters
        """
        try:
            parsed = urlparse(url)
            
            # Base URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # Normalize query parameters
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                sorted_params = sorted(params.items())
                normalized += "?" + urlencode(sorted_params, doseq=True)
            
            return normalized.lower()
        except Exception as e:
            logger.debug(f"URL normalization failed: {e}")
            return url.lower()
    
    # ============ Element Fingerprint Deduplication ============
    
    def should_click_element(
        self,
        element_text: str,
        element_selector: str,
        page_url: str,
        is_navigation: bool = None
    ) -> bool:
        """Check whether an element should be clicked

        Args:
            element_text: Element text
            element_selector: Element selector
            page_url: Current page URL
            is_navigation: Whether it is a navigation component (None triggers auto-detection)

        Returns:
            True means it should be clicked, False means skip
        """
        if not self.config.enable_element_dedup:
            return True
        
        # Auto-detect whether it is a navigation component
        if is_navigation is None:
            is_navigation = self._is_navigation_component(element_text, element_selector)
        
        # Generate fingerprint
        signature = self._generate_element_signature(
            element_text,
            element_selector,
            page_url,
            is_navigation
        )
        
        if signature in self.clicked_signatures:
            self.stats["element_skipped"] += 1
            logger.debug(f"Skipping already clicked element: {element_text[:20]}... (navigation: {is_navigation})")
            return False
        
        self.clicked_signatures.add(signature)
        self.stats["element_clicked"] += 1
        return True
    
    def _generate_element_signature(
        self,
        text: str,
        selector: str,
        page_url: str,
        is_navigation: bool
    ) -> str:
        """Generate element fingerprint

        Strategy:
        - Navigation components: use root_domain (global deduplication)
        - Business components: use full_path (page-level deduplication)
        """
        # Clean text
        text = (text or "").strip()[:100]
        
        # Determine dedup scope
        if is_navigation:
            scope = self._extract_scope(page_url, self.config.navigation_dedup_scope)
        else:
            scope = self._extract_scope(page_url, self.config.business_dedup_scope)
        
        # Generate fingerprint
        fingerprint_data = f"{text}|{selector}|{scope}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def _is_navigation_component(self, text: str, selector: str) -> bool:
        """Determine whether it is a navigation/common component

        Heuristic rules:
        1. Selector contains keywords like nav, header, footer, menu, etc.
        2. Text contains common navigation words (login, register, home, etc.)
        """
        text_lower = (text or "").lower()
        selector_lower = (selector or "").lower()
        
        # Navigation keywords
        nav_keywords = [
            'nav', 'header', 'footer', 'menu', 'sidebar',
            'topbar', 'bottom', 'breadcrumb', 'toolbar'
        ]
        
        # Common texts
        common_texts = [
            'login', 'logout', 'sign in', 'sign up', 'register',
            'home', 'about', 'contact', 'help', 'faq',
        ]
        
        # Check selector
        if any(kw in selector_lower for kw in nav_keywords):
            return True
        
        # Check text
        if any(ct in text_lower for ct in common_texts):
            return True
        
        return False
    
    def _extract_scope(self, url: str, scope_type: str) -> str:
        """Extract dedup scope

        Args:
            url: Full URL
            scope_type: "root_domain" or "full_path"
        """
        try:
            parsed = urlparse(url)
            
            if scope_type == "root_domain":
                # Extract root domain (without subdomain)
                # e.g.: a.target.com -> target.com
                parts = parsed.netloc.split('.')
                if len(parts) >= 2:
                    return '.'.join(parts[-2:])
                return parsed.netloc
            
            elif scope_type == "full_path":
                # Full path (including domain and path)
                return f"{parsed.netloc}{parsed.path}"
            
            else:
                return parsed.netloc
                
        except Exception as e:
            logger.debug(f"Scope extraction failed: {e}")
            return url
    
    # ============ Statistics ============
    
    def get_stats(self) -> dict:
        """Get statistics"""
        total_urls = self.stats["url_visited"] + self.stats["url_skipped"]
        total_elements = self.stats["element_clicked"] + self.stats["element_skipped"]
        
        return {
            **self.stats,
            "url_dedup_rate": f"{self.stats['url_skipped'] / total_urls * 100:.1f}%" if total_urls > 0 else "0%",
            "element_dedup_rate": f"{self.stats['element_skipped'] / total_elements * 100:.1f}%" if total_elements > 0 else "0%",
        }
    
    def print_stats(self):
        """Print statistics"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("Global deduplication statistics")
        logger.info("=" * 60)
        logger.info(f"URL visited: {stats['url_visited']} | skipped: {stats['url_skipped']} | dedup rate: {stats['url_dedup_rate']}")
        logger.info(f"Element clicked: {stats['element_clicked']} | skipped: {stats['element_skipped']} | dedup rate: {stats['element_dedup_rate']}")
        logger.info("=" * 60)
