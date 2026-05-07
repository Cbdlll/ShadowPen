"""
Hybrid XSS attack surface crawler (crawler.py)

Features:
- Stage 1: Full asset discovery using GoSpider (subdomains, JS files, URLs)
- Stage 2: Deep interaction probing using Playwright + DeepInteractionEngine (Depth=2 BFS)
- Output: Attack surface list (result.json) containing URLs, parameters, depth, trigger chains, etc.

Usage:
    python crawler.py <target_url>

Example:
    python crawler.py http://127.0.0.1:3000
"""
import asyncio
import logging
from typing import List
from dataclasses import dataclass

from playwright.async_api import async_playwright

from crawler_engine import CrawlerConfig
from crawler_engine.utils import GoSpiderWrapper, ResultWriter, URLUtils
from crawler_engine.analyzers import DeepInteractionEngine, TrafficInterceptor

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class ScannerConfig:
    """Scanner configuration"""
    MAX_ACTIONS_PER_PAGE: int = 50
    MAX_DEPTH: int = 2
    GLOBAL_TIMEOUT: int = 3600  # 1 hour
    MAX_URLS: int = 100
    INTERACTION_TIMEOUT: int = 3000
    CONCURRENT_PAGES: int = 3


class XSSScanner:
    """Intelligent hybrid architecture XSS scanner"""
    
    def __init__(self, config: ScannerConfig = None):
        self.config = config or ScannerConfig()
        self.writer = ResultWriter("result.json")
        self.gospider = GoSpiderWrapper()
        
        # Global deduplication manager (shared by all workers)
        from crawler_engine.utils import GlobalDeduplicationManager
        self.global_dedup = GlobalDeduplicationManager()
    
    async def scan(self, target_domain: str) -> str:
        """Main scan workflow

        Args:
            target_domain: Target domain

        Returns:
            Path to result.json file
        """
        logger.info(f"========== XSS Scanner Started ==========")
        logger.info(f"Target: {target_domain}")
        logger.info(f"Configuration: {self.config}")
        
        try:
            # Stage 1: Asset Discovery
            urls = await self._asset_discovery(target_domain)
            
            # Stage 2: Deep Inspection
            await self._deep_inspection(urls)
            
            logger.info(f"========== Scan Completed ==========")
            logger.info(f"Results saved to: result.json")

            # Print deduplication statistics
            self.global_dedup.print_stats()
            
            return "result.json"
            
        except asyncio.TimeoutError:
            logger.error(f"Scan timed out ({self.config.GLOBAL_TIMEOUT}s)")
            raise
        except Exception as e:
            logger.error(f"Scan failed: {e}", exc_info=True)
            raise
    
    async def _asset_discovery(self, target: str) -> List[str]:
        """Stage 1: Asset discovery"""
        logger.info("=" * 60)
        logger.info("Stage 1: Asset discovery using GoSpider")
        logger.info("=" * 60)
        
        # Check GoSpider availability
        is_available = await self.gospider.check_availability()
        
        if is_available:
            urls = await self.gospider.discover_urls(
                target,
                concurrency=10,
                depth=2
            )
            logger.info(f"GoSpider discovered {len(urls)} URLs")
        else:
            logger.warning("GoSpider unavailable, using fallback mode")
            urls = [target]
        
        # URL deduplication and filtering
        unique_urls = self._deduplicate_urls(urls, target)
        logger.info(f"After deduplication: {len(unique_urls)} unique URLs")

        # Limit count
        if len(unique_urls) > self.config.MAX_URLS:
            logger.warning(f"URL count exceeds limit ({self.config.MAX_URLS}), truncating")
            unique_urls = unique_urls[:self.config.MAX_URLS]
        
        return unique_urls
    
    async def _deep_inspection(self, urls: List[str]):
        """Stage 2: Deep inspection"""
        logger.info("=" * 60)
        logger.info("Stage 2: Deep interaction probing")
        logger.info("=" * 60)
        logger.info(f"URLs to inspect: {len(urls)}")

        # Clear old results
        self.writer.clear()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                # Process in concurrent batches
                for i in range(0, len(urls), self.config.CONCURRENT_PAGES):
                    batch = urls[i:i + self.config.CONCURRENT_PAGES]
                    tasks = [self._inspect_url(browser, url) for url in batch]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
            finally:
                await browser.close()
    
    async def _inspect_url(self, browser, url: str):
        """Deep inspection of a single URL (4-layer full probing)"""
        context = None
        try:
            logger.info(f"Inspecting: {url}")

            # Create isolated context
            context = await browser.new_context()
            page = await context.new_page()
            
            # ========== Layer 1: URL static analysis ==========
            from crawler_engine.analyzers import URLAnalyzer
            url_analyzer = URLAnalyzer()
            url_surfaces = url_analyzer.analyze_url(url)
            logger.debug(f"URL analysis: found {len(url_surfaces)} attack surfaces")
            
            # ========== Layer 2: Start traffic interception (must be before navigation) ==========
            interceptor = TrafficInterceptor(
                scope_domains=[],
                capture_all=True,  # Do not filter cross-origin
                page_url=url
            )
            await interceptor.start_interception(page)
            
            # ========== Navigate to page ==========
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # **SPA wait mechanism** (critical!)
            await asyncio.sleep(2)  # Wait for JavaScript rendering
            try:
                await page.wait_for_load_state("domcontentloaded")
            except:
                pass
            
            # ========== Layer 3: DOM static analysis ==========
            from crawler_engine.analyzers import DOMAnalyzer
            dom_analyzer = DOMAnalyzer()
            dom_surfaces = await dom_analyzer.analyze_page(page, url)
            logger.debug(f"DOM static analysis: found {len(dom_surfaces)} attack surfaces")
            
            # ========== Layer 4: Deep interaction (Depth=2 BFS) ==========
            interaction_engine = DeepInteractionEngine(
                max_depth=self.config.MAX_DEPTH,
                max_actions=self.config.MAX_ACTIONS_PER_PAGE,
                interaction_timeout=self.config.INTERACTION_TIMEOUT,
                global_dedup=self.global_dedup  # Pass global deduplicator
            )
            
            interaction_surfaces = await interaction_engine.explore_page(page, interceptor, url)
            logger.debug(f"Deep interaction exploration: found {len(interaction_surfaces)} attack surfaces")
            
            # ========== Merge all 4 layers of attack surfaces ==========
            all_surfaces = url_surfaces + dom_surfaces + interaction_surfaces
            logger.info(f"✓ {url}: Total {len(all_surfaces)} attack surfaces found "
                       f"(URL:{len(url_surfaces)} + DOM:{len(dom_surfaces)} + Interaction:{len(interaction_surfaces)})")
            
            # Save results (batch write, with deduplication enabled)
            simplified_surfaces = []
            for surface in all_surfaces:
                surface_dict = surface.to_dict()
                # Simplified format (only XSS test essentials)
                simplified = {
                    "base_url": url,
                    "request_url": surface_dict["url"],
                    "method": surface_dict["method"],
                    "param_name": surface_dict["param_name"],
                    "param_location": surface_dict["param_type"],
                    "depth_level": surface_dict.get("depth_level", 0),
                    "trigger_chain": surface_dict.get("trigger_chain", "page_load"),
                    "sample_payload": surface_dict.get("sample_payload", ""),
                    "is_cross_origin": surface_dict.get("is_cross_origin", False),
                }
                simplified_surfaces.append(simplified)
            
            # Batch write (with auto deduplication)
            self.writer.write_surfaces(simplified_surfaces)
            
        except Exception as e:
            logger.error(f"✗ {url}: {str(e)}")
        finally:
            if context:
                await context.close()
    
    def _deduplicate_urls(self, urls: List[str], target_domain: str) -> List[str]:
        """URL deduplication

        Deduplicate based on (domain, path, sorted_query_keys)
        """
        seen = set()
        unique = []
        
        for url in urls:
            # Basic validation
            if not URLUtils.is_valid_http_url(url):
                continue
            
            # Scope filter (keep only target domain and its subdomains)
            url_domain = URLUtils.get_domain(url)
            target_dom = URLUtils.get_domain(target_domain)
            if not (url_domain == target_dom or url_domain.endswith(f".{target_dom}")):
                continue
            
            # Generate deduplication fingerprint
            normalized = URLUtils.normalize_url(url)
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(normalized)
            query_keys = tuple(sorted(parse_qs(parsed.query).keys()))
            fingerprint = (parsed.netloc, parsed.path, query_keys)
            
            if fingerprint not in seen:
                seen.add(fingerprint)
                unique.append(url)
        
        return unique


async def main():
    """Main entry point"""
    import sys
    
    if len(sys.argv) < 2:
        print("Usage: python crawler.py <target_domain>")
        print("Example: python crawler.py http://127.0.0.1:3000")
        sys.exit(1)
    
    target = sys.argv[1]
    
    # Create scanner
    config = ScannerConfig(
        MAX_DEPTH=2,
        MAX_ACTIONS_PER_PAGE=50,
        MAX_URLS=50,  # Limit URL count to avoid excessive duration
    )
    
    scanner = XSSScanner(config)
    
    try:
        result_file = await scanner.scan(target)
        print(f"\n✓ Scan completed! Results saved to: {result_file}")
    except KeyboardInterrupt:
        print("\n✗ Scan interrupted by user")
    except Exception as e:
        print(f"\n✗ Scan failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
