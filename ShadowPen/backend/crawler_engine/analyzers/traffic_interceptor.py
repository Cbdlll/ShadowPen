"""
流量拦截器模块

监听并分析所有网络请求，提取参数
"""
from typing import List, Dict, Any, Optional
from playwright.async_api import Page, Request
from ..models import AttackSurface, ParamType, SourceType
from ..utils.url_utils import URLUtils
import json
import logging

logger = logging.getLogger(__name__)

from datetime import datetime



class TrafficInterceptor:
    """流量拦截器
    
    功能:
    - 监听所有网络请求
    - 解析 JSON Body
    - 解析 FormData
    - 提取 Header 参数
    """
    
    def __init__(self, scope_domains: List[str], capture_all: bool = False, page_url: str = "", action_trigger: str = "page_load"):
        """初始化流量拦截器
        
        Args:
            scope_domains: 允许的域名范围列表
            capture_all: 是否捕获所有域名的流量（无差别捕获模式）
            page_url: 当前页面 URL（用于标记触发来源）
            action_trigger: 触发动作描述（如 "page_load", "click_button_#id"）
        
        注意：depth_level 和 trigger_chain 设计为可动态修改的属性，
        由 DeepInteractionEngine 在运行时更新
        """
        self.scope_domains = scope_domains
        self.capture_all = capture_all
        self.page_url = page_url
        self.action_trigger = action_trigger
        
        # 深度交互相关（可动态修改）
        self.depth_level: int = 0
        self.trigger_chain: List[str] = ["page_load"]
        
        self._captured_surfaces: List[AttackSurface] = []
        self._active = False
    
    async def start_interception(self, page: Page):
        """启动流量拦截
        
        Args:
            page: Playwright 页面对象
        """
        self._active = True
        page.on("request", self._handle_request)
        mode = "无差别捕获" if self.capture_all else f"范围: {self.scope_domains}"
        logger.info(f"流量拦截已启动 ({mode})")
    
    def stop_interception(self):
        """停止拦截"""
        self._active = False
        logger.info("流量拦截已停止")

    def _get_timestamp(self):
        return datetime.now().isoformat()

    
    def _is_cross_origin(self, request_url: str) -> bool:
        """判断请求是否跨域
        
        Args:
            request_url: 请求 URL
            
        Returns:
            True 表示跨域，False 表示同域
        """
        if not self.page_url:
            return False
        
        from ..utils import URLUtils
        return URLUtils.get_domain(request_url) != URLUtils.get_domain(self.page_url)
    
    async def _handle_request(self, request: Request):
        """处理拦截到的请求"""
        if not self._active:
            return
        
        try:
            url = request.url
            method = request.method
            
            # 跨域判断
            is_cross_origin = self._is_cross_origin(url)
            
            # 过滤逻辑
            if not self.capture_all:
                # 非无差别模式：只处理范围内的请求
                if not URLUtils.is_in_scope(url, self.scope_domains):
                    return
            # 无差别模式：捕获所有请求，无需过滤
            
            # 过滤静态资源
            resource_type = request.resource_type
            if resource_type in ["image", "stylesheet", "font", "media"]:
                # logger.debug(f"过滤静态资源: {url} ({resource_type})")
                return
            
            # **DEBUG: 记录所有拦截的请求**
            logger.debug(f"拦截请求: {method} {url} (crossorigin={is_cross_origin})")
            
            # 1. 分析 POST/PUT/PATCH/DELETE/OPTIONS
            if method.upper() in ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
                post_data = request.post_data or ""  # 允许为空
                
                # 即使没有 Body，也记录请求（特别是 OPTIONS 和 DELETE）
                if method == "OPTIONS":
                     # 记录 OPTIONS 请求作为跨域探测线索
                    self._captured_surfaces.append(AttackSurface(
                        url=url,
                        method=method,
                        param_name="cors_preflight",
                        param_type=ParamType.HEADER,
                        source=SourceType.TRAFFIC_INTERCEPT,
                        page_url=self.page_url,
                        action_trigger=self.action_trigger,
                        is_cross_origin=is_cross_origin,
                        timestamp=self._get_timestamp(),
                        depth_level=self.depth_level,
                        trigger_chain=" -> ".join(self.trigger_chain),
                        sample_payload="Access-Control-Request-Method",
                    ))
                else:
                    # 处理数据请求
                    if post_data:
                        self._parse_post_data(url, method, post_data, request, is_cross_origin)
                    else:
                        # 无 Body 的 POST/DELETE，记录 URL 本身
                        self._captured_surfaces.append(AttackSurface(
                            url=url,
                            method=method,
                            param_name="body", # 标记为空 body
                            param_type=ParamType.JSON_BODY, # 假设
                            source=SourceType.TRAFFIC_INTERCEPT,
                            page_url=self.page_url,
                            action_trigger=self.action_trigger,
                            is_cross_origin=is_cross_origin,
                            timestamp=self._get_timestamp(),
                            depth_level=self.depth_level,
                            trigger_chain=" -> ".join(self.trigger_chain),
                            sample_payload="",
                        ))
            
            # **BUG FIX: 添加 GET 请求参数捕获**
            elif method.upper() == "GET":
                # 1. 解析 URL 查询参数
                from urllib.parse import urlparse, parse_qs, unquote
                parsed = urlparse(url)
                if parsed.query:
                    params = parse_qs(parsed.query)
                    for param_name, param_values in params.items():
                        for param_value in param_values:
                            self._captured_surfaces.append(AttackSurface(
                                url=url,
                                method=method,
                                param_name=param_name,
                                param_type=ParamType.QUERY_PARAM,
                                source=SourceType.TRAFFIC_INTERCEPT,
                                page_url=self.page_url,
                                action_trigger=self.action_trigger,
                                is_cross_origin=is_cross_origin,
                                timestamp=self._get_timestamp(),
                                depth_level=self.depth_level,
                                trigger_chain=" -> ".join(self.trigger_chain),
                                sample_payload=param_value,
                            ))
                    logger.debug(f"GET 请求参数: {url} ({len(params)} 个参数)")
                
                # 2. 检测 RESTful 路径参数 (检查路径中是否包含测试 Payload)
                # 我们在 DeepInteractionEngine 中使用的测试 Payload 是 "XSS_SEARCH_TEST"
                path = unquote(parsed.path)
                if "XSS_SEARCH_TEST" in path:
                    # 提取包含 Payload 的路径段作为参数
                    segments = path.strip('/').split('/')
                    for i, segment in enumerate(segments):
                        if "XSS_SEARCH_TEST" in segment:
                            self._captured_surfaces.append(AttackSurface(
                                url=url,
                                method=method,
                                param_name=f"path_param_{i}", # 使用位置作为参数名
                                param_type=ParamType.QUERY_PARAM, # 暂时归类为 QUERY_PARAM 或新增 PATH_PARAM
                                source=SourceType.TRAFFIC_INTERCEPT,
                                page_url=self.page_url,
                                action_trigger=self.action_trigger,
                                is_cross_origin=is_cross_origin,
                                timestamp=self._get_timestamp(),
                                depth_level=self.depth_level,
                                trigger_chain=" -> ".join(self.trigger_chain),
                                sample_payload=segment,
                            ))
                            logger.info(f"捕获 RESTful 路径参数: {url} (Segment {i})")
            
            # 2. 分析 Query 参数（由 URL 分析器处理，这里跳过）
            
            # 3. 可选：分析 Headers
            # self._parse_headers(url, method, request.headers)
            
        except Exception as e:
            logger.debug(f"请求处理失败: {url} - {e}")
    
    def _parse_post_data(self, url: str, method: str, post_data: str, request: Request, is_cross_origin: bool = False):
        """解析 POST 数据"""
        content_type = request.headers.get("content-type", "")
        
        logger.debug(f"解析POST数据: {url}, content-type={content_type}, body长度={len(post_data)}")
        
        # JSON 格式
        if "application/json" in content_type:
            self._parse_json_body(url, method, post_data, is_cross_origin)
        
        # 表单格式
        elif "application/x-www-form-urlencoded" in content_type:
            self._parse_form_data(url, method, post_data, is_cross_origin)
        
        # Multipart
        elif "multipart/form-data" in content_type:
            self._parse_multipart_data(url, method, post_data, is_cross_origin)
    
    def _parse_json_body(self, url: str, method: str, json_str: str, is_cross_origin: bool = False):
        """递归解析 JSON Body"""
        try:
            if not json_str:
                return

            data = json.loads(json_str)
            # 提取所有层级的键作为参数名
            param_names = self._extract_json_keys(data)
            
            # 添加时间戳
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            
            if not param_names:
                logger.debug(f"JSON Body 中未发现参数: {url}")
                return

            for param_name in param_names:
                self._captured_surfaces.append(AttackSurface(
                    url=url,
                    method=method,
                    param_name=param_name,
                    param_type=ParamType.JSON_BODY,
                    source=SourceType.TRAFFIC_INTERCEPT,
                    raw_request=json_str[:500],
                    # 混合式扫描器字段
                    page_url=self.page_url,
                    action_trigger=self.action_trigger,
                    is_cross_origin=is_cross_origin,
                    timestamp=timestamp,
                    # 深度交互字段
                    depth_level=self.depth_level,
                    trigger_chain=" -> ".join(self.trigger_chain),
                    sample_payload="XSS_Probe",
                ))
            logger.debug(f"捕获 JSON 参数: {url} -> {param_names}")
                
        except json.JSONDecodeError:
            logger.debug(f"JSON 解析失败: {json_str[:100]}")
        except Exception as e:
            logger.debug(f"JSON 处理异常: {e}")

    def _parse_form_data(self, url: str, method: str, post_data: str, is_cross_origin: bool = False):
        """解析 Form Data"""
        try:
            from urllib.parse import parse_qs
            params = parse_qs(post_data)
            
            # 添加时间戳
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            
            for param_name in params.keys():
                self._captured_surfaces.append(AttackSurface(
                    url=url,
                    method=method,
                    param_name=param_name,
                    param_type=ParamType.POST_PARAM,
                    source=SourceType.TRAFFIC_INTERCEPT,
                    raw_request=post_data[:500],
                    # 混合式扫描器字段
                    page_url=self.page_url,
                    action_trigger=self.action_trigger,
                    is_cross_origin=is_cross_origin,
                    timestamp=timestamp,
                    # 深度交互字段
                    depth_level=self.depth_level,
                    trigger_chain=" -> ".join(self.trigger_chain),
                    sample_payload="XSS_Probe",
                ))
            logger.debug(f"捕获 Form 参数: {url} -> {list(params.keys())}")
            
        except Exception as e:
            logger.debug(f"Form Data 解析失败: {e}")
    
    def _extract_json_keys(self, data: Any, prefix: str = "") -> List[str]:
        """递归提取 JSON 中所有键
        
        Args:
            data: JSON 数据
            prefix: 键前缀（用于嵌套对象）
            
        Returns:
            键名列表
        """
        keys = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.append(full_key)
                
                # 递归处理嵌套对象/数组
                if isinstance(value, (dict, list)):
                    keys.extend(self._extract_json_keys(value, full_key))
        
        elif isinstance(data, list):
            # 仅处理第一个元素作为样本
            if data and isinstance(data[0], (dict, list)):
                keys.extend(self._extract_json_keys(data[0], prefix))
        
        return keys
    
    def _parse_form_data(self, url: str, method: str, form_data: str, is_cross_origin: bool = False):
        """解析 application/x-www-form-urlencoded"""
        try:
            from urllib.parse import parse_qs
            from datetime import datetime
            params = parse_qs(form_data)
            timestamp = datetime.now().isoformat()
            
            for param_name in params.keys():
                self._captured_surfaces.append(AttackSurface(
                    url=url,
                    method=method,
                    param_name=param_name,
                    param_type=ParamType.FORM_DATA,
                    source=SourceType.TRAFFIC_INTERCEPT,
                    page_url=self.page_url,
                    action_trigger=self.action_trigger,
                    is_cross_origin=is_cross_origin,
                    timestamp=timestamp,
                    depth_level=self.depth_level,
                    trigger_chain=" -> ".join(self.trigger_chain),
                    sample_payload="XSS_Probe",
                ))
                
        except Exception as e:
            logger.debug(f"表单数据解析失败: {e}")
    
    def _parse_multipart_data(self, url: str, method: str, multipart_data: str, is_cross_origin: bool = False):
        """解析 multipart/form-data（简化处理）"""
        try:
            import re
            from datetime import datetime
            names = re.findall(r'name="([^"]+)"', multipart_data)
            timestamp = datetime.now().isoformat()
            
            for param_name in names:
                self._captured_surfaces.append(AttackSurface(
                    url=url,
                    method=method,
                    param_name=param_name,
                    param_type=ParamType.FORM_DATA,
                    source=SourceType.TRAFFIC_INTERCEPT,
                    page_url=self.page_url,
                    action_trigger=self.action_trigger,
                    is_cross_origin=is_cross_origin,
                    timestamp=timestamp,
                    depth_level=self.depth_level,
                    trigger_chain=" -> ".join(self.trigger_chain),
                    sample_payload="XSS_Probe",
                ))
                
        except Exception as e:
            logger.debug(f"Multipart 数据解析失败: {e}")
    
    def get_captured_surfaces(self) -> List[AttackSurface]:
        """获取已捕获的攻击面"""
        return self._captured_surfaces.copy()
    
    def clear(self):
        """清空捕获的数据"""
        self._captured_surfaces.clear()
