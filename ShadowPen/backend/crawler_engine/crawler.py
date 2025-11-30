"""
XSS 爬虫引擎主模块

集成所有分析器，实现完整的攻击面探测
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
    """XSS 攻击面爬虫引擎
    
    核心功能:
    - 集成四大分析器（DOM、Traffic、Interaction、URL）
    - BFS 页面遍历
    - 自动去重
    - 健壮的异常处理
    """
    
    def __init__(self, config: CrawlerConfig = None):
        self.config = config or CrawlerConfig()
        
        # 浏览器实例
        self._browser: Browser | None = None
        self._playwright = None
        
        # 分析器
        self._dom_analyzer = DOMAnalyzer()
        self._url_analyzer = URLAnalyzer()
        self._js_hook = JSHookInjector()  # JS Hook 注入器
        self._response_analyzer = ResponseAnalyzer()  # 响应分析器
        self._interaction_engine = InteractionEngine(
            fill_timeout=self.config.form_fill_timeout,
            click_timeout=self.config.interaction_timeout,
        )
        
        # 去重引擎
        self._dedup = DeduplicationEngine()
        
        # 爬取状态
        self._visited_urls: Set[str] = set()
        self._url_queue: List[str] = []
        self._errors: List[Dict[str, str]] = []
    
    async def crawl(self, target_url: str, scope_domain: str = None, max_pages: int = None) -> CrawlResult:
        """开始爬取
        
        Args:
            target_url: 入口 URL
            scope_domain: 主要爬取范围域名（兼容旧参数）
            max_pages: 最大爬取页数
            
        Returns:
            CrawlResult 对象
        """
        if not URLUtils.is_valid_http_url(target_url):
            raise ValueError(f"无效的 URL: {target_url}")
        
        # 确定爬取范围
        primary_domain = scope_domain or URLUtils.get_domain(target_url)
        
        # 构建完整的范围列表
        active_scopes = [primary_domain]
        if self.config.scope_domains:
            active_scopes.extend(self.config.scope_domains)
            
        # 自动添加 localhost/127.0.0.1 的对应关系
        if primary_domain in ['localhost', '127.0.0.1']:
            active_scopes.append('localhost' if primary_domain == '127.0.0.1' else '127.0.0.1')
            
        max_pages = max_pages or self.config.max_pages_per_domain
        
        logger.info(f"开始爬取: {target_url} (范围: {active_scopes}, 最大页数: {max_pages})")
        
        try:
            # 初始化浏览器
            await self._ensure_browser_ready()
            
            # 初始化队列
            self._url_queue = [target_url]
            all_surfaces: List[AttackSurface] = []
            
            # BFS 遍历
            while self._url_queue and len(self._visited_urls) < max_pages:
                current_url = self._url_queue.pop(0)
                
                # 跳过已访问或超范围的 URL
                if current_url in self._visited_urls:
                    logger.debug(f"跳过已访问 URL: {current_url}")
                    continue
                
                # 页面导航主要限制在主域，避免爬到外部站点
                # 但流量拦截会使用 active_scopes
                if not URLUtils.is_in_scope(current_url, primary_domain):
                    logger.warning(f"跳过超范围页面: {current_url} (主域: {primary_domain})")
                    continue
                
                # 标记为已访问
                self._visited_urls.add(current_url)
                
                # 爬取单个页面
                try:
                    page_surfaces = await self._crawl_page(current_url, active_scopes)
                    all_surfaces.extend(page_surfaces)
                    logger.info(
                        f"[{len(self._visited_urls)}/{max_pages}] 已爬取: {current_url}, "
                        f"发现 {len(page_surfaces)} 个攻击面"
                    )
                except Exception as e:
                    error_msg = f"页面爬取失败: {current_url} - {str(e)}"
                    logger.error(error_msg)
                    self._errors.append({"url": current_url, "error": str(e)})
                    continue
            
            # 去重
            unique_surfaces = self._dedup.deduplicate(all_surfaces)
            
            logger.info(
                f"爬取完成: 访问了 {len(self._visited_urls)} 个页面, "
                f"发现 {len(all_surfaces)} 个攻击面, 去重后 {len(unique_surfaces)} 个"
            )
            
            return CrawlResult(
                target_url=target_url,
                pages_crawled=len(self._visited_urls),
                surfaces=unique_surfaces,
                errors=self._errors,
            )
            
        finally:
            # 确保资源清理
            await self.close()
    
    async def _crawl_page(self, url: str, scope_domains: List[str]) -> List[AttackSurface]:
        """爬取单个页面
        
        Args:
            url: 页面 URL
            scope_domains: 允许的流量拦截范围
            
        Returns:
            该页面发现的攻击面列表
        """
        page: Page | None = None
        surfaces: List[AttackSurface] = []
        
        try:
            # 创建新页面
            page = await self._browser.new_page()
            
            # **P1-B: 注入 JS Hook (在页面加载前)**
            await self._js_hook.inject_hooks(page)
            
            # 设置超时
            page.set_default_navigation_timeout(self.config.navigation_timeout)
            page.set_default_timeout(self.config.wait_for_load_timeout)
            
            # 启动流量拦截器（使用扩展的范围）
            # 注意：传递 page_url 用于跨域判断
            # enable_cross_origin_capture=True 时启用无差别捕获，可捕获未知域名的跨域流量
            traffic_interceptor = TrafficInterceptor(
                scope_domains=scope_domains,
                capture_all=self.config.enable_cross_origin_capture,  # 使用配置控制
                page_url=url,
                action_trigger="page_load"
            )
            await traffic_interceptor.start_interception(page)
            
            # **P1-A: 监听响应事件**
            async def handle_response(response):
                # 提取已知参数名
                known_params = [s.param_name for s in surfaces if hasattr(s, 'param_name')]
                await self._response_analyzer.analyze_response(response, url, known_params)
            
            page.on("response", handle_response)
            
            # 导航到页面
            try:
                await page.goto(url, wait_until="domcontentloaded")
                # **BUG FIX: 增加等待时间,确保异步请求完成**
                await page.wait_for_load_state("networkidle", timeout=self.config.wait_for_load_timeout)
            except PlaywrightTimeout:
                logger.warning(f"页面加载超时: {url}")
                # 继续分析，可能部分内容已加载
            
            # 获取最终 URL（可能有重定向）
            final_url = page.url
            
            # **BUG FIX P0: 确保 URL 分析器执行**
            # 1. URL 分析
            url_surfaces = self._url_analyzer.analyze_url(final_url, "GET")
            surfaces.extend(url_surfaces)
            logger.debug(f"URL 分析: 发现 {len(url_surfaces)} 个攻击面")
            
            # 2. DOM 分析
            dom_surfaces = await self._dom_analyzer.analyze_page(page, final_url)
            surfaces.extend(dom_surfaces)
            
            # 3. 主动交互触发
            if self.config.enable_form_submission or self.config.enable_button_clicks:
                interaction_surfaces = await self._interaction_engine.trigger_interactions(
                    page, traffic_interceptor
                )
                surfaces.extend(interaction_surfaces)
            
            # 4. 获取流量拦截的攻击面
            traffic_surfaces = traffic_interceptor.get_captured_surfaces()
            surfaces.extend(traffic_surfaces)
            
            # 5. **P1-B: 收集 JS Hook 结果**
            js_hook_surfaces = await self._js_hook.collect_results(page, final_url)
            surfaces.extend(js_hook_surfaces)
            
            # 6. **P1-A: 收集响应分析结果**
            response_surfaces = self._response_analyzer.get_captured_surfaces()
            surfaces.extend(response_surfaces)
            
            # 7. 提取页面链接（用于 BFS）
            # 使用列表中的第一个域名作为主域进行导航限制
            await self._extract_links(page, scope_domains[0])
            
            return surfaces
            
        except PlaywrightTimeout as e:
            raise NavigationException(f"导航超时: {url}")
        except Exception as e:
            logger.error(f"页面处理异常: {url} - {e}")
            raise
        finally:
            # 关闭页面
            if page:
                try:
                    await page.close()
                except:
                    pass
    
    async def _extract_links(self, page: Page, scope_domain: str):
        """提取页面链接，加入队列
        
        Args:
            page: Playwright 页面对象
            scope_domain: 爬取范围域名（仅限主域）
        """
        try:
            # 提取所有链接
            links = await page.evaluate("""
                () => {
                    const anchors = document.querySelectorAll('a[href]');
                    return Array.from(anchors).map(a => a.href);
                }
            """)
            
            for link in links:
                # 规范化 URL
                normalized_link = URLUtils.normalize_url(link)
                
                # 检查是否在范围内且未访问
                # 注意：页面导航严格限制在 scope_domain（主域）
                if (
                    URLUtils.is_in_scope(normalized_link, scope_domain)
                    and normalized_link not in self._visited_urls
                    and normalized_link not in self._url_queue
                ):
                    self._url_queue.append(normalized_link)
                    
        except Exception as e:
            logger.debug(f"链接提取失败: {e}")
    
    async def _ensure_browser_ready(self):
        """确保浏览器已启动"""
        if self._browser:
            return
        
        try:
            self._playwright = await async_playwright().start()
            
            # 根据配置选择浏览器
            browser_type = getattr(self._playwright, self.config.browser_type)
            
            self._browser = await browser_type.launch(
                headless=self.config.headless,
            )
            
            logger.info(f"浏览器已启动: {self.config.browser_type}")
            
        except Exception as e:
            raise BrowserException(f"浏览器启动失败: {e}")
    
    async def close(self):
        """关闭浏览器，释放资源"""
        if self._browser:
            try:
                await self._browser.close()
                logger.info("浏览器已关闭")
            except Exception as e:
                logger.error(f"浏览器关闭失败: {e}")
            finally:
                self._browser = None
        
        if self._playwright:
            try:
                await self._playwright.stop()
            except Exception as e:
                logger.error(f"Playwright 停止失败: {e}")
            finally:
                self._playwright = None
    
    def reset(self):
        """重置爬虫状态（保留配置）"""
        self._visited_urls.clear()
        self._url_queue.clear()
        self._errors.clear()
        self._dedup.reset()


# 便捷函数
async def crawl_surface(
    target_url: str,
    max_pages: int = 10,
    config: CrawlerConfig = None
) -> CrawlResult:
    """便捷的爬取函数
    
    Args:
        target_url: 目标 URL
        max_pages: 最大爬取页数
        config: 自定义配置
        
    Returns:
        CrawlResult 对象
    """
    crawler = XSSSurfaceCrawler(config)
    try:
        return await crawler.crawl(target_url, max_pages=max_pages)
    finally:
        await crawler.close()
