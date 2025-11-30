"""
全局去重管理器

功能：
- 全局 URL 去重（避免重复访问链接）
- 智能元素指纹去重（区分公共组件和业务组件）
"""
import hashlib
import logging
from typing import Set, Optional
from urllib.parse import urlparse, urljoin, parse_qs, urlencode
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationConfig:
    """去重配置"""
    enable_global_url_dedup: bool = True        # 启用全局 URL 去重
    enable_element_dedup: bool = True           # 启用元素指纹去重
    navigation_dedup_scope: str = "root_domain" # 导航组件去重范围（root_domain/full_path）
    business_dedup_scope: str = "full_path"     # 业务组件去重范围


class GlobalDeduplicationManager:
    """全局去重管理器（单例模式）
    
    策略：
    1. 全局 URL 去重 - 避免重复访问相同链接
    2. 混合元素去重 - 导航组件全局去重，业务组件页面级去重
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
        
        # 全局去重集合
        self.visited_urls: Set[str] = set()
        self.clicked_signatures: Set[str] = set()
        
        # 统计
        self.stats = {
            "url_skipped": 0,
            "element_skipped": 0,
            "url_visited": 0,
            "element_clicked": 0,
        }
        
        self._initialized = True
        logger.info("全局去重管理器已初始化")
    
    def reset(self):
        """重置去重状态（用于测试）"""
        self.visited_urls.clear()
        self.clicked_signatures.clear()
        self.stats = {k: 0 for k in self.stats}
        logger.info("去重管理器已重置")
    
    # ============ URL 去重 ============
    
    def should_visit_url(self, url: str) -> bool:
        """检查 URL 是否应该访问
        
        Args:
            url: 待检查的 URL
            
        Returns:
            True 表示应该访问，False 表示跳过
        """
        if not self.config.enable_global_url_dedup:
            return True
        
        normalized = self.normalize_url(url)
        
        if normalized in self.visited_urls:
            self.stats["url_skipped"] += 1
            logger.debug(f"跳过已访问 URL: {url}")
            return False
        
        self.visited_urls.add(normalized)
        self.stats["url_visited"] += 1
        return True
    
    def normalize_url(self, url: str) -> str:
        """URL 规范化
        
        规则：
        1. 去除 fragment (#)
        2. 转换为小写
        3. 查询参数排序
        """
        try:
            parsed = urlparse(url)
            
            # 基础 URL
            normalized = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            # 规范化查询参数
            if parsed.query:
                params = parse_qs(parsed.query, keep_blank_values=True)
                sorted_params = sorted(params.items())
                normalized += "?" + urlencode(sorted_params, doseq=True)
            
            return normalized.lower()
        except Exception as e:
            logger.debug(f"URL 规范化失败: {e}")
            return url.lower()
    
    # ============ 元素指纹去重 ============
    
    def should_click_element(
        self,
        element_text: str,
        element_selector: str,
        page_url: str,
        is_navigation: bool = None
    ) -> bool:
        """检查元素是否应该点击
        
        Args:
            element_text: 元素文本
            element_selector: 元素选择器
            page_url: 当前页面 URL
            is_navigation: 是否是导航组件（None 则自动判断）
            
        Returns:
            True 表示应该点击，False 表示跳过
        """
        if not self.config.enable_element_dedup:
            return True
        
        # 自动判断是否是导航组件
        if is_navigation is None:
            is_navigation = self._is_navigation_component(element_text, element_selector)
        
        # 生成指纹
        signature = self._generate_element_signature(
            element_text,
            element_selector,
            page_url,
            is_navigation
        )
        
        if signature in self.clicked_signatures:
            self.stats["element_skipped"] += 1
            logger.debug(f"跳过已点击元素: {element_text[:20]}... (导航组件: {is_navigation})")
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
        """生成元素指纹
        
        策略：
        - 导航组件：使用 root_domain（全局去重）
        - 业务组件：使用 full_path（页面级去重）
        """
        # 清理文本
        text = (text or "").strip()[:100]
        
        # 确定去重范围
        if is_navigation:
            scope = self._extract_scope(page_url, self.config.navigation_dedup_scope)
        else:
            scope = self._extract_scope(page_url, self.config.business_dedup_scope)
        
        # 生成指纹
        fingerprint_data = f"{text}|{selector}|{scope}"
        return hashlib.md5(fingerprint_data.encode()).hexdigest()
    
    def _is_navigation_component(self, text: str, selector: str) -> bool:
        """判断是否是导航/公共组件
        
        启发式规则：
        1. 选择器包含 nav, header, footer, menu 等关键词
        2. 文本是常见导航词汇（登录、注册、首页等）
        """
        text_lower = (text or "").lower()
        selector_lower = (selector or "").lower()
        
        # 导航关键词
        nav_keywords = [
            'nav', 'header', 'footer', 'menu', 'sidebar',
            'topbar', 'bottom', 'breadcrumb', 'toolbar'
        ]
        
        # 公共文本
        common_texts = [
            'login', 'logout', 'sign in', 'sign up', 'register',
            'home', 'about', 'contact', 'help', 'faq',
            '登录', '注册', '首页', '关于', '联系', '帮助'
        ]
        
        # 检查选择器
        if any(kw in selector_lower for kw in nav_keywords):
            return True
        
        # 检查文本
        if any(ct in text_lower for ct in common_texts):
            return True
        
        return False
    
    def _extract_scope(self, url: str, scope_type: str) -> str:
        """提取去重范围
        
        Args:
            url: 完整 URL
            scope_type: "root_domain" 或 "full_path"
        """
        try:
            parsed = urlparse(url)
            
            if scope_type == "root_domain":
                # 提取根域名（不含子域）
                # 例如：a.target.com → target.com
                parts = parsed.netloc.split('.')
                if len(parts) >= 2:
                    return '.'.join(parts[-2:])
                return parsed.netloc
            
            elif scope_type == "full_path":
                # 完整路径（含域名和路径）
                return f"{parsed.netloc}{parsed.path}"
            
            else:
                return parsed.netloc
                
        except Exception as e:
            logger.debug(f"范围提取失败: {e}")
            return url
    
    # ============ 统计信息 ============
    
    def get_stats(self) -> dict:
        """获取统计信息"""
        total_urls = self.stats["url_visited"] + self.stats["url_skipped"]
        total_elements = self.stats["element_clicked"] + self.stats["element_skipped"]
        
        return {
            **self.stats,
            "url_dedup_rate": f"{self.stats['url_skipped'] / total_urls * 100:.1f}%" if total_urls > 0 else "0%",
            "element_dedup_rate": f"{self.stats['element_skipped'] / total_elements * 100:.1f}%" if total_elements > 0 else "0%",
        }
    
    def print_stats(self):
        """打印统计信息"""
        stats = self.get_stats()
        logger.info("=" * 60)
        logger.info("全局去重统计")
        logger.info("=" * 60)
        logger.info(f"URL 访问: {stats['url_visited']} | 跳过: {stats['url_skipped']} | 去重率: {stats['url_dedup_rate']}")
        logger.info(f"元素点击: {stats['element_clicked']} | 跳过: {stats['element_skipped']} | 去重率: {stats['element_dedup_rate']}")
        logger.info("=" * 60)
