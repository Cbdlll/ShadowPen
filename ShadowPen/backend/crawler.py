"""
混合式 XSS 攻击面爬虫 (crawler.py)

功能：
- Stage 1: 使用 GoSpider 进行全量资产发现（子域名、JS 文件、URL）
- Stage 2: 使用 Playwright + DeepInteractionEngine 进行深度交互探测（Depth=2 BFS）
- 输出：攻击面列表（result.json），包含 URL、参数、深度、触发链等信息

用法：
    python crawler.py <target_url>
    
示例：
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
    """扫描器配置"""
    MAX_ACTIONS_PER_PAGE: int = 50
    MAX_DEPTH: int = 2
    GLOBAL_TIMEOUT: int = 3600  # 1小时
    MAX_URLS: int = 100
    INTERACTION_TIMEOUT: int = 3000
    CONCURRENT_PAGES: int = 3


class XSSScanner:
    """智能混合架构 XSS 扫描器"""
    
    def __init__(self, config: ScannerConfig = None):
        self.config = config or ScannerConfig()
        self.writer = ResultWriter("result.json")
        self.gospider = GoSpiderWrapper()
        
        # 全局去重管理器（所有 Worker 共享）
        from crawler_engine.utils import GlobalDeduplicationManager
        self.global_dedup = GlobalDeduplicationManager()
    
    async def scan(self, target_domain: str) -> str:
        """主扫描流程
        
        Args:
            target_domain: 目标域名
            
        Returns:
            result.json 文件路径
        """
        logger.info(f"========== XSS 扫描器启动 ==========")
        logger.info(f"目标: {target_domain}")
        logger.info(f"配置: {self.config}")
        
        try:
            # Stage 1: Asset Discovery
            urls = await self._asset_discovery(target_domain)
            
            # Stage 2: Deep Inspection
            await self._deep_inspection(urls)
            
            logger.info(f"========== 扫描完成 ==========")
            logger.info(f"结果已保存到: result.json")
            
            # 打印去重统计
            self.global_dedup.print_stats()
            
            return "result.json"
            
        except asyncio.TimeoutError:
            logger.error(f"扫描超时 ({self.config.GLOBAL_TIMEOUT}s)")
            raise
        except Exception as e:
            logger.error(f"扫描失败: {e}", exc_info=True)
            raise
    
    async def _asset_discovery(self, target: str) -> List[str]:
        """Stage 1: 资产发现"""
        logger.info("=" * 60)
        logger.info("Stage 1: 使用 GoSpider 进行资产发现")
        logger.info("=" * 60)
        
        # 检查 GoSpider 可用性
        is_available = await self.gospider.check_availability()
        
        if is_available:
            urls = await self.gospider.discover_urls(
                target,
                concurrency=10,
                depth=2
            )
            logger.info(f"GoSpider 发现 {len(urls)} 个 URL")
        else:
            logger.warning("GoSpider 不可用，使用降级模式")
            urls = [target]
        
        # URL 去重和过滤
        unique_urls = self._deduplicate_urls(urls, target)
        logger.info(f"去重后: {len(unique_urls)} 个唯一 URL")
        
        # 限制数量
        if len(unique_urls) > self.config.MAX_URLS:
            logger.warning(f"URL 数量超过限制({self.config.MAX_URLS})，截断处理")
            unique_urls = unique_urls[:self.config.MAX_URLS]
        
        return unique_urls
    
    async def _deep_inspection(self, urls: List[str]):
        """Stage 2: 深度探测"""
        logger.info("=" * 60)
        logger.info("Stage 2: 深度交互探测")
        logger.info("=" * 60)
        logger.info(f"待探测 URL 数量: {len(urls)}")
        
        # 清空旧结果
        self.writer.clear()
        
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            
            try:
                # 分批并发处理
                for i in range(0, len(urls), self.config.CONCURRENT_PAGES):
                    batch = urls[i:i + self.config.CONCURRENT_PAGES]
                    tasks = [self._inspect_url(browser, url) for url in batch]
                    await asyncio.gather(*tasks, return_exceptions=True)
                    
            finally:
                await browser.close()
    
    async def _inspect_url(self, browser, url: str):
        """深度检查单个 URL（4 层完整探测）"""
        context = None
        try:
            logger.info(f"正在探测: {url}")
            
            # 创建独立上下文
            context = await browser.new_context()
            page = await context.new_page()
            
            # ========== 第 1 层：URL 静态分析 ==========
            from crawler_engine.analyzers import URLAnalyzer
            url_analyzer = URLAnalyzer()
            url_surfaces = url_analyzer.analyze_url(url)
            logger.debug(f"URL 分析: 发现 {len(url_surfaces)} 个攻击面")
            
            # ========== 第 2 层：启动流量拦截（必须在导航前）==========
            interceptor = TrafficInterceptor(
                scope_domains=[],
                capture_all=True,  # 跨域不过滤
                page_url=url
            )
            await interceptor.start_interception(page)
            
            # ========== 导航到页面 ==========
            await page.goto(url, wait_until="networkidle", timeout=30000)
            
            # **SPA 等待机制**（关键！）
            await asyncio.sleep(2)  # 等待 JavaScript 渲染
            try:
                await page.wait_for_load_state("domcontentloaded")
            except:
                pass
            
            # ========== 第 3 层：DOM 静态分析 ==========
            from crawler_engine.analyzers import DOMAnalyzer
            dom_analyzer = DOMAnalyzer()
            dom_surfaces = await dom_analyzer.analyze_page(page, url)
            logger.debug(f"DOM 静态分析: 发现 {len(dom_surfaces)} 个攻击面")
            
            # ========== 第 4 层：深度交互（Depth=2 BFS）==========
            interaction_engine = DeepInteractionEngine(
                max_depth=self.config.MAX_DEPTH,
                max_actions=self.config.MAX_ACTIONS_PER_PAGE,
                interaction_timeout=self.config.INTERACTION_TIMEOUT,
                global_dedup=self.global_dedup  # 传递全局去重器
            )
            
            interaction_surfaces = await interaction_engine.explore_page(page, interceptor, url)
            logger.debug(f"深度交互探索: 发现 {len(interaction_surfaces)} 个攻击面")
            
            # ========== 合并所有 4 层的攻击面 ==========
            all_surfaces = url_surfaces + dom_surfaces + interaction_surfaces
            logger.info(f"✓ {url}: 总计发现 {len(all_surfaces)} 个攻击面 "
                       f"(URL:{len(url_surfaces)} + DOM:{len(dom_surfaces)} + 交互:{len(interaction_surfaces)})")
            
            # 保存结果(批量写入,启用去重)
            simplified_surfaces = []
            for surface in all_surfaces:
                surface_dict = surface.to_dict()
                # 简化格式（仅保留 XSS 测试必需信息）
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
            
            # 批量写入(带自动去重)
            self.writer.write_surfaces(simplified_surfaces)
            
        except Exception as e:
            logger.error(f"✗ {url}: {str(e)}")
        finally:
            if context:
                await context.close()
    
    def _deduplicate_urls(self, urls: List[str], target_domain: str) -> List[str]:
        """URL 去重
        
        基于 (domain, path, sorted_query_keys) 去重
        """
        seen = set()
        unique = []
        
        for url in urls:
            # 基本验证
            if not URLUtils.is_valid_http_url(url):
                continue
            
            # 范围过滤（只保留目标域及其子域）
            url_domain = URLUtils.get_domain(url)
            target_dom = URLUtils.get_domain(target_domain)
            if not (url_domain == target_dom or url_domain.endswith(f".{target_dom}")):
                continue
            
            # 生成去重指纹
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
    """主入口"""
    import sys
    
    if len(sys.argv) < 2:
        print("用法: python crawler.py <target_domain>")
        print("示例: python crawler.py http://127.0.0.1:3000")
        sys.exit(1)
    
    target = sys.argv[1]
    
    # 创建扫描器
    config = ScannerConfig(
        MAX_DEPTH=2,
        MAX_ACTIONS_PER_PAGE=50,
        MAX_URLS=50,  # 限制 URL 数量避免过长时间
    )
    
    scanner = XSSScanner(config)
    
    try:
        result_file = await scanner.scan(target)
        print(f"\n✓ 扫描完成！结果保存在: {result_file}")
    except KeyboardInterrupt:
        print("\n✗ 用户中断扫描")
    except Exception as e:
        print(f"\n✗ 扫描失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
