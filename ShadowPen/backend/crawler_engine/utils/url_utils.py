"""
工具模块：URL 处理工具

提供 URL 解析、规范化、域名判断等功能
"""
from urllib.parse import urlparse, urljoin, parse_qs
from typing import Optional, List


class URLUtils:
    """URL 工具类"""
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """规范化 URL，移除 Fragment"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (
            f"?{parsed.query}" if parsed.query else ""
        )
    
    @staticmethod
    def get_domain(url: str) -> str:
        """提取域名（主机名，不含端口）"""
        parsed = urlparse(url)
        # 分离主机名和端口
        hostname = parsed.hostname or parsed.netloc.split(':')[0]
        return hostname
    
    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """判断两个 URL 是否同域"""
        return URLUtils.get_domain(url1) == URLUtils.get_domain(url2)
    
    @staticmethod
    def is_in_scope(url: str, scope_domains: str | List[str]) -> bool:
        """判断 URL 是否在爬取范围内
        
        Args:
            url: 待检查的 URL
            scope_domains: 允许的域名范围（单个字符串或字符串列表）
        """
        if not scope_domains:
            return True
            
        if isinstance(scope_domains, str):
            scope_domains = [scope_domains]
            
        url_domain = URLUtils.get_domain(url)
        
        for scope in scope_domains:
            # 处理 scope 包含端口的情况
            scope_hostname = scope.split(':')[0] if ':' in scope else scope
            
            # 检查是否匹配（完全匹配或子域名）
            if url_domain == scope_hostname or url_domain.endswith(f".{scope_hostname}"):
                return True
                
        # 特殊处理 localhost 和 127.0.0.1 的互通
        if url_domain in ['localhost', '127.0.0.1']:
            for scope in scope_domains:
                scope_hostname = scope.split(':')[0] if ':' in scope else scope
                if scope_hostname in ['localhost', '127.0.0.1']:
                    return True
                    
        return False    
    @staticmethod
    def resolve_relative_url(base_url: str, relative_url: str) -> str:
        """将相对 URL 转换为绝对 URL"""
        return urljoin(base_url, relative_url)
    
    @staticmethod
    def extract_query_params(url: str) -> dict:
        """提取 URL 查询参数"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # 将列表值转换为单值（取第一个）
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    
    @staticmethod
    def is_valid_http_url(url: str) -> bool:
        """判断是否为有效的 HTTP(S) URL"""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except:
            return False
