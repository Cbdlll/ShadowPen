"""
HTTP 响应分析器

监听 HTTP 响应,检测安全漏洞
"""
from typing import List, Dict, Any, Optional
from playwright.async_api import Response, Request
from ..models import AttackSurface, ParamType, SourceType
import logging
import re

logger = logging.getLogger(__name__)


class ResponseAnalyzer:
    """HTTP 响应分析器
    
    功能:
    - 检测 HTTP Header Injection (CRLF 注入)
    - 识别 JSONP 端点特征
    - 分析 CSP 策略
    """
    
    def __init__(self):
        self._captured_surfaces: List[AttackSurface] = []
        self._analyzed_urls: set = set()  # 避免重复分析
    
    async def analyze_response(
        self, 
        response: Response, 
        current_url: str,
        known_params: List[str] = None
    ) -> List[AttackSurface]:
        """分析单个 HTTP 响应
        
        Args:
            response: Playwright Response 对象
            current_url: 当前页面 URL
            known_params: 已知的参数名列表
            
        Returns:
            发现的攻击面列表
        """
        surfaces = []
        request_url = response.url
        
        # 避免重复分析同一 URL
        if request_url in self._analyzed_urls:
            return surfaces
        self._analyzed_urls.add(request_url)
        
        try:
            # 1. JSONP 检测
            if await self._is_jsonp_response(response):
                jsonp_surface = await self._create_jsonp_surface(response, current_url)
                if jsonp_surface:
                    surfaces.append(jsonp_surface)
                    logger.info(f"发现 JSONP 端点: {request_url}")
            
            # 2. Header Injection 检测
            if known_params and await self._has_header_injection_risk(response, known_params):
                header_surface = self._create_header_injection_surface(response, current_url)
                if header_surface:
                    surfaces.append(header_surface)
                    logger.warning(f"检测到 Header Injection 风险: {request_url}")
            
            # 3. CSP 分析 (可选,仅记录日志)
            await self._analyze_csp(response)
            
            # 缓存结果
            self._captured_surfaces.extend(surfaces)
            
        except Exception as e:
            logger.debug(f"响应分析失败: {request_url} - {e}")
        
        return surfaces
    
    async def _is_jsonp_response(self, response: Response) -> bool:
        """识别 JSONP 响应
        
        检测条件:
        1. Content-Type 包含 javascript
        2. 响应体匹配 callback(...) 模式
        """
        try:
            content_type = response.headers.get('content-type', '').lower()
            
            # 检查 Content-Type
            if 'javascript' not in content_type and 'json' not in content_type:
                return False
            
            # 获取响应体
            body = await response.text()
            if not body:
                return False
            
            # 匹配 JSONP 模式: callback_name(...)
            # 允许的模式: funcName(...), func123(...), $callback(...)
            jsonp_pattern = r'^\s*[\w$]+\s*\('
            if re.match(jsonp_pattern, body):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"JSONP 检测失败: {e}")
            return False
    
    async def _create_jsonp_surface(
        self, 
        response: Response, 
        current_url: str
    ) -> Optional[AttackSurface]:
        """创建 JSONP 攻击面
        
        从 URL 中提取 callback 参数名
        """
        try:
            request = response.request
            url = request.url
            
            # 从 URL 中提取查询参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # 查找可能的 callback 参数
            callback_param = None
            for param_name in params.keys():
                # 常见的 callback 参数名
                if param_name.lower() in ['callback', 'jsonp', 'cb', 'jsoncallback']:
                    callback_param = param_name
                    break
            
            if not callback_param:
                # 如果没有明确的 callback,使用第一个参数
                callback_param = list(params.keys())[0] if params else 'callback'
            
            return AttackSurface(
                url=url,
                method=request.method,
                param_name=callback_param,
                param_type=ParamType.QUERY_PARAM,
                source=SourceType.TRAFFIC_INTERCEPT,
                page_url=current_url,
                vulnerability_type="JSONP",
                sample_payload="malicious_callback",
                element_type="jsonp_endpoint"
            )
            
        except Exception as e:
            logger.debug(f"创建 JSONP 攻击面失败: {e}")
            return None
    
    async def _has_header_injection_risk(
        self, 
        response: Response, 
        known_params: List[str]
    ) -> bool:
        """检测响应头是否存在注入风险
        
        检查敏感响应头中是否包含 CRLF 字符
        """
        try:
            # 敏感响应头
            risky_headers = [
                'location', 
                'set-cookie', 
                'refresh',
                'x-redirect',
                'content-disposition'
            ]
            
            headers = response.headers
            
            for header_name in risky_headers:
                header_value = headers.get(header_name, '')
                
                if not header_value:
                    continue
                
                # 检查 CRLF 序列
                if '\r' in header_value or '\n' in header_value:
                    logger.warning(
                        f"发现 CRLF 序列在响应头 {header_name}: "
                        f"{repr(header_value[:100])}"
                    )
                    return True
                
                # 检查是否包含已知参数值 (简化检测)
                for param in known_params:
                    if param in header_value:
                        logger.info(
                            f"响应头 {header_name} 包含参数 {param}, "
                            f"可能存在注入风险"
                        )
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Header Injection 检测失败: {e}")
            return False
    
    def _create_header_injection_surface(
        self, 
        response: Response, 
        current_url: str
    ) -> Optional[AttackSurface]:
        """创建 Header Injection 攻击面"""
        try:
            request = response.request
            url = request.url
            
            # 从 URL 中提取参数
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # 找到可疑参数
            suspicious_param = None
            for param_name in params.keys():
                # 常见的可注入参数
                if param_name.lower() in ['msg', 'message', 'url', 'redirect', 'next']:
                    suspicious_param = param_name
                    break
            
            if not suspicious_param:
                suspicious_param = list(params.keys())[0] if params else 'msg'
            
            return AttackSurface(
                url=url,
                method=request.method,
                param_name=suspicious_param,
                param_type=ParamType.QUERY_PARAM,
                source=SourceType.TRAFFIC_INTERCEPT,
                page_url=current_url,
                vulnerability_type="HEADER_INJECTION",
                sample_payload="test%0d%0aX-Injected:true",
                element_type="http_response_header"
            )
            
        except Exception as e:
            logger.debug(f"创建 Header Injection 攻击面失败: {e}")
            return None
    
    async def _analyze_csp(self, response: Response):
        """分析 CSP 策略 (仅记录日志)"""
        try:
            csp = response.headers.get('content-security-policy')
            
            if not csp:
                return
            
            # 检查是否存在不安全的指令
            risky_directives = [
                'unsafe-inline',
                'unsafe-eval',
                '*'  # 通配符
            ]
            
            for directive in risky_directives:
                if directive in csp.lower():
                    logger.warning(
                        f"检测到宽松的 CSP 策略 (包含 {directive}): "
                        f"{response.url}"
                    )
                    break
            
        except Exception as e:
            logger.debug(f"CSP 分析失败: {e}")
    
    def get_captured_surfaces(self) -> List[AttackSurface]:
        """获取所有捕获的攻击面"""
        return self._captured_surfaces.copy()
    
    def clear(self):
        """清空缓存"""
        self._captured_surfaces.clear()
        self._analyzed_urls.clear()
