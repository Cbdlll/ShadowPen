"""
XSS Crawler Engine Main Module

Integrates all analyzers for complete attack surface detection
"""
from typing import List, Set, Dict, Any
from playwright.async_api import async_playwright, Browser, Page, TimeoutError as PlaywrightTimeout
import asyncio
import logging

from .config import CrawlerConfig
from .models import AttackSurface, CrawlResult
from .analyzers import DOMAnalyzer, TrafficInterceptor, InteractionEngine, URLAnalyzer, JSHookInjector, ResponseAnalyzer
from .utils import DeduplicationEngine, URLUtils
from .utils.exceptions import CrawlerException, BrowserException, NavigationException

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class XSSSurfaceCrawler:
    """XSS Attack Surface Crawler Engine

    Core features:
    - Integrates four analyzers (DOM, Traffic, Interaction, URL)
    - BFS page traversal
    - Automatic deduplication
    - Robust exception handling
    """
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        
        # Browser instance
        self._browser: Browser | None = None
        self._playwright = None
        
        # Analyzers
        self._dom_analyzer = DOMAnalyzer()
        self._url_analyzer = URLAnalyzer()
        self._js_hook = JSHookInjector()  # JS Hook injector
        self._response_analyzer = ResponseAnalyzer()  # Response analyzer
        self._interaction_engine = InteractionEngine(
            fill_timeout=self.config.form_fill_timeout,
            click_timeout=self.config.interaction_timeout,
        )
        
        # Deduplication engine
        self._dedup = DeduplicationEngine()
        
        # Crawl state
        self._visited_urls: Set[str] = set()
        self._url_queue: List[str] = []
        self._errors: List[Dict[str, str]] = []
    
    async def crawl(self, target_url: str, scope_domain: str = None, max_pages: int = None) -> CrawlResult:
        """Start crawling

        Args:
            target_url: Entry URL
            scope_domain: Primary crawl scope domain (legacy parameter compatible)
            max_pages: Maximum pages to crawl

        Returns:
            CrawlResult object
        """
        if not URLUtils.is_valid_http_url(target_url):
            raise ValueError(f"Invalid URL: {target_url}")
        
        # Determine crawl scope
        primary_domain = scope_domain or URLUtils.get_domain(target_url)
        
        # Build complete scope list
        active_scopes = [primary_domain]
        if self.config.scope_domains:
            active_scopes.extend(self.config.scope_domains)
            
        # Auto-add localhost/127.0.0.1 mapping
        if primary_domain in ['localhost', '127.0.0.1']:
            active_scopes.append('localhost' if primary_domain == '127.0.0.1' else '127.0.0.1')
            
        max_pages = max_pages or self.config.max_pages_per_domain
        
        logger.info(f"Start crawling: {target_url} (scope: {active_scopes}, max pages: {max_pages})")
        
        try:
            # Initialize browser
            await self._ensure_browser_ready()
            
            # Initialize queue
            self._url_queue = [target_url]
            all_surfaces: List[AttackSurface] = []
            
            # BFS traversal
            while self._url_queue and len(self._visited_urls) < max_pages:
                current_url = self._url_queue.pop(0)
                
                # Skip visited or out-of-scope URL
                if current_url in self._visited_urls:
                    logger.debug(f"Skip visited URL: {current_url}")
                    continue
                
                # Page navigation restricted to primary domain to avoid crawling external sites
                # But traffic interception uses active_scopes
                if not URLUtils.is_in_scope(current_url, primary_domain):
                    logger.warning(f"Skip out-of-scope page: {current_url} (primary domain: {primary_domain})")
                    continue
                
                # Mark as visited
                self._visited_urls.add(current_url)
                
                # Crawl single page
                try:
                    page_surfaces = await self._crawl_page(current_url, active_scopes)
                    all_surfaces.extend(page_surfaces)
                    logger.info(
                        f"[{len(self._visited_urls)}/{max_pages}] Crawled: {current_url}, "
                        f"found {len(page_surfaces)} attack surfaces"
                    )
                except Exception as e:
                    error_msg = f"Page crawl failed: {current_url} - {str(e)}"
                    logger.error(error_msg)
                    self._errors.append({"url": current_url, "error": str(e)})
                    continue
            
            # Deduplication
            unique_surfaces = self._dedup.deduplicate(all_surfaces)
            
            logger.info(
                f"Crawl completed: visited {len(self._visited_urls)} pages, "
                f"found {len(all_surfaces)} attack surfaces, {len(unique_surfaces)} after deduplication"
            )
            
            return CrawlResult(
                target_url=target_url,
                pages_crawled=len(self._visited_urls),
                surfaces=unique_surfaces,
                errors=self._errors,
            )
            
        finally:
            # Ensure resource cleanup
            await self.close()
    
    async def _crawl_page(self, url: str, scope_domains: List[str]) -> List[AttackSurface]:
        """Crawl single page

        Args:
            url: Page URL
            scope_domains: Allowed traffic interception scope

        Returns:
            List of attack surfaces discovered on this page
        """
        page: Page | None = None
        surfaces: List[AttackSurface] = []
        
        try:
            # Create new page
            page = await self._browser.new_page()
            
            # **P1-B: Inject JS Hook (before page load)**
            await self._js_hook.inject_hooks(page)
            
            # Set timeout
            page.set_default_navigation_timeout(self.config.navigation_timeout)
            page.set_default_timeout(self.config.wait_for_load_timeout)
            
            # Start traffic interceptor (using extended scope)
            # Note: pass page_url for cross-origin detection
            # When enable_cross_origin_capture=True, enables indiscriminate capture of cross-origin traffic from unknown domains
            traffic_interceptor = TrafficInterceptor(
                scope_domains=scope_domains,
                capture_all=self.config.enable_cross_origin_capture,  # Controlled by config
                page_url=url,
                action_trigger="page_load"
            )
            await traffic_interceptor.start_interception(page)
            
            # **P1-A: Listen for response events**
            async def handle_response(response):
                # Extract known parameter names
                known_params = [s.param_name for s in surfaces if hasattr(s, 'param_name')]
                await self._response_analyzer.analyze_response(response, url, known_params)
            
            page.on("response", handle_response)
            
            # Navigate to page
            try:
                await page.goto(url, wait_until="domcontentloaded")
                # **BUG FIX: Increase wait time to ensure async requests complete**
                await page.wait_for_load_state("networkidle", timeout=self.config.wait_for_load_timeout)
            except PlaywrightTimeout:
                logger.warning(f"Page load timeout: {url}")
                # Continue analysis, partial content may have loaded
            
            # Get final URL (may have redirects)
            final_url = page.url
            
            # **BUG FIX P0: Ensure URL analyzer executes**
            # 1. URL analysis
            url_surfaces = self._url_analyzer.analyze_url(final_url, "GET")
            surfaces.extend(url_surfaces)
            logger.debug(f"URL analysis: found {len(url_surfaces)} attack surfaces")
            
            # 2. DOM analysis
            dom_surfaces = await self._dom_analyzer.analyze_page(page, final_url)
            surfaces.extend(dom_surfaces)
            
            # 3. Active interaction trigger
            if self.config.enable_form_submission or self.config.enable_button_clicks:
                interaction_surfaces = await self._interaction_engine.trigger_interactions(
                    page, traffic_interceptor
                )
                surfaces.extend(interaction_surfaces)
            
            # 4. Get traffic interceptor attack surfaces
            traffic_surfaces = traffic_interceptor.get_captured_surfaces()
            surfaces.extend(traffic_surfaces)
            
            # 5. **P1-B: Collect JS Hook results**
            js_hook_surfaces = await self._js_hook.collect_results(page, final_url)
            surfaces.extend(js_hook_surfaces)
            
            # 6. **P1-A: Collect response analysis results**
            response_surfaces = self._response_analyzer.get_captured_surfaces()
            surfaces.extend(response_surfaces)
            
            # 7. Extract page links (for BFS)
            # Use the first domain in list as primary domain for navigation restriction
            await self._extract_links(page, scope_domains[0])
            
            return surfaces
            
        except PlaywrightTimeout as e:
            raise NavigationException(f"Navigation timeout: {url}")
        except Exception as e:
            logger.error(f"Page processing error: {url} - {e}")
            raise
        finally:
            # Close page
            if page:
                try:
                    await page.close()
                except:
                    pass
    
    async def _extract_links(self, page: Page, scope_domain: str):
        """Extract page links and add to queue

        Args:
            page: Playwright page object
            scope_domain: Crawl scope domain (primary domain only)
        """
        try:
            # Extract all links
            links = await page.evaluate("""
                () => {
                    const anchors = document.querySelectorAll('a[href]');
                    return Array.from(anchors).map(a => a.href);
                }
            """)
            
            for link in links:
                # Normalize URL
                normalized_link = URLUtils.normalize_url(link)
                
                # Check if in scope and not visited
                # Note: page navigation strictly limited to scope_domain (primary domain)
                if (
                    URLUtils.is_in_scope(normalized_link, scope_domain)
                    and normalized_link not in self._visited_urls
                    and normalized_link not in self._url_queue
                ):
                    self._url_queue.append(normalized_link)
                    
        except Exception as e:
            logger.debug(f"Link extraction failed: {e}")
    
    async def _ensure_browser_ready(self):
        """Ensure browser is ready"""
        if self._browser:
            return
        
        try:
            self._playwright = await async_playwright().start()
            
            # Select browser based on config
            browser_type = getattr(self._playwright, self.config.browser_type)
            
            self._browser = await browser_type.launch(
                headless=self.config.headless,
            )
            
            logger.info(f"Browser started: {self.config.browser_type}")
            
        except Exception as e:
            raise BrowserException(f"Browser launch failed: {e}")
    
    async def close(self):
        """Close browser and release resources"""
        if self._browser:
            try:
                await self._browser.close()
                logger.info("Browser closed")
            except Exception as e:
                logger.error(f"Browser close failed: {e}")
            finally:
                self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.error(f"Playwright stop failed: {e}")
            finally:
                self._playwright = None
    
    def reset(self):
        """Reset crawler state (keep config)"""
        self._visited_urls.clear()
        self._url_queue.clear()
        self._errors.clear()
        self._dedup.reset()


# Convenience functions
async def crawl_surface(
    target_url: str,
    max_pages: int = 10,
    config: CrawlerConfig = None
) -> CrawlResult:
    """Convenient crawl function

    Args:
        target_url: Target URL
        max_pages: Maximum pages to crawl
        config: Custom configuration

    Returns:
        CrawlResult object
    """
    crawler = XSSSurfaceCrawler(config)
    try:
        return await crawler.crawl(target_url, max_pages=max_pages)
    finally:
        await crawler.close()
