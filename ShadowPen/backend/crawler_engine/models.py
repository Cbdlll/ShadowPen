"""
XSS 爬虫引擎数据模型

定义攻击面、参数类型等核心数据结构
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any
import hashlib
import json


class ParamType(str, Enum):
    """参数类型枚举"""
    QUERY_PARAM = "query_param"          # URL 查询参数
    PATH_PARAM = "path_param"            # URL 路径参数
    JSON_BODY = "json_body"              # JSON 请求体字段
    FORM_DATA = "form_data"              # 表单数据
    FORM_INPUT = "form_input"            # HTML 表单输入
    HIDDEN_INPUT = "hidden_input"        # 隐藏输入字段
    CONTENTEDITABLE = "contenteditable"  # 可编辑内容元素
    HEADER = "header"                    # HTTP Header


class SourceType(str, Enum):
    """发现来源枚举"""
    DOM_FORM = "dom_form"                                # DOM 表单分析
    DOM_STATIC = "dom_static"                            # DOM 静态元素
    TRAFFIC_INTERCEPT = "traffic_intercept"              # 流量拦截
    TRAFFIC_INTERCEPT_AFTER_INTERACTION = "traffic_intercept_after_interaction"  # 交互后流量
    URL_ANALYSIS = "url_analysis"                        # URL 模式分析
    INTERACTION_TRIGGER = "interaction_trigger"          # 交互触发


@dataclass
class AttackSurface:
    """攻击面数据模型
    
    表示一个可能的 XSS 注入点
    """
    url: str                                    # 完整 URL
    method: str                                 # HTTP 方法（GET, POST, PUT, DELETE 等）
    param_name: str                             # 参数名称
    param_type: ParamType                       # 参数类型
    source: SourceType                          # 发现来源
    
    # 可选字段
    element_selector: Optional[str] = None      # DOM 元素选择器
    element_type: Optional[str] = None          # 元素类型（input, textarea 等）
    raw_request: Optional[str] = None           # 原始请求快照
    context: Optional[Dict[str, Any]] = None    # 额外上下文信息
    
    # 混合式扫描器新增字段
    page_url: Optional[str] = None              # 触发页面 URL
    action_trigger: str = "page_load"           # 触发动作（page_load, click_button_#id 等）
    is_cross_origin: bool = False               # 是否跨域请求
    timestamp: Optional[str] = None             # 发现时间戳
    
    # 深度交互新增字段
    depth_level: int = 0                        # 交互深度（0, 1, 2）
    trigger_chain: str = "page_load"            # 完整触发链
    sample_payload: str = ""                    # 样本 payload（用于验证）
    
    # 内部字段
    fingerprint: str = field(init=False)        # 唯一指纹
    url_pattern: str = field(init=False)        # URL 模式（用于去重）
    
    def __post_init__(self):
        """初始化后处理：生成指纹和 URL 模式"""
        # 生成 URL 模式（规范化路径参数）
        self.url_pattern = self._normalize_url()
        
        # 生成唯一指纹
        self.fingerprint = self._generate_fingerprint()
    
    def _normalize_url(self) -> str:
        """规范化 URL，将路径参数替换为占位符
        
        例如: /user/123 -> /user/{id}
              /api/order/uuid-123 -> /api/order/{uuid}
        """
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(self.url)
        path = parsed.path
        
        # 如果是路径参数，替换为占位符
        if self.param_type == ParamType.PATH_PARAM:
            # 简单策略：将参数值替换为 {param}
            path = path.replace(f"/{self.param_name}", "/{param}")
        
        # 重建 URL（不包含查询参数，避免具体值影响指纹）
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    def _generate_fingerprint(self) -> str:
        """生成唯一指纹
        
        基于: (Method, URL_Pattern, Param_Name, Param_Type)
        """
        fingerprint_data = f"{self.method}|{self.url_pattern}|{self.param_name}|{self.param_type.value}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典（用于 JSON 序列化）"""
        data = asdict(self)
        # 将枚举转换为字符串值
        data["param_type"] = self.param_type.value
        # source 可能是字符串或枚举
        data["source"] = self.source.value if isinstance(self.source, SourceType) else self.source
        return data
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    def __repr__(self) -> str:
        return (
            f"AttackSurface("
            f"url={self.url!r}, "
            f"method={self.method}, "
            f"param={self.param_name}, "
            f"type={self.param_type.value}, "
            f"source={self.source.value}"
            f")"
        )


@dataclass
class CrawlResult:
    """爬取结果数据模型"""
    target_url: str                             # 目标 URL
    pages_crawled: int                          # 已爬取页面数
    surfaces: list[AttackSurface]               # 发现的攻击面列表
    errors: list[Dict[str, str]] = field(default_factory=list)  # 错误列表
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "target_url": self.target_url,
            "pages_crawled": self.pages_crawled,
            "total_surfaces": len(self.surfaces),
            "surfaces": [s.to_dict() for s in self.surfaces],
            "errors": self.errors,
        }
    
    def to_json(self) -> str:
        """转换为 JSON 字符串"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
