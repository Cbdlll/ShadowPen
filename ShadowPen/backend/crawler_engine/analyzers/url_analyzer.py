"""
URL 分析器模块

智能分析 URL 结构，识别路径参数和查询参数
"""
from typing import List, Tuple
import re
from urllib.parse import urlparse, parse_qs
from ..models import AttackSurface, ParamType, SourceType
import logging

logger = logging.getLogger(__name__)


class URLAnalyzer:
    """URL 模式分析器
    
    功能:
    - 识别 RESTful 路径参数
    - 提取查询参数
    - URL 模式规范化
    """
    
    # RESTful 参数模式
    PATTERNS = {
        'numeric': re.compile(r'^[0-9]+$'),           # 纯数字: 123
        'uuid': re.compile(r'^[a-f0-9-]{32,36}$'),    # UUID: a1b2-c3d4-...
        'id_prefix': re.compile(r'^(id|ID)_?\d+$'),   # ID 前缀: id_123
        'hash': re.compile(r'^[a-f0-9]{32,64}$'),     # Hash: md5/sha256
    }
    
    def analyze_url(self, url: str, method: str = "GET") -> List[AttackSurface]:
        """分析 URL，提取攻击面
        
        Args:
            url: 目标 URL
            method: HTTP 方法
            
        Returns:
            攻击面列表
        """
        surfaces = []
        
        # 1. 提取查询参数
        surfaces.extend(self._extract_query_params(url, method))
        
        # 2. 检测路径参数
        surfaces.extend(self._detect_path_params(url, method))
        
        return surfaces
    
    def _extract_query_params(self, url: str, method: str) -> List[AttackSurface]:
        """提取查询参数"""
        surfaces = []
        
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # 基础 URL（不含查询字符串）
            base_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}"
            
            for param_name, values in params.items():
                surfaces.append(AttackSurface(
                    url=base_url,
                    method=method,
                    param_name=param_name,
                    param_type=ParamType.QUERY_PARAM,
                    source=SourceType.URL_ANALYSIS,
                    context={"sample_value": values[0] if values else None},
                ))
                
        except Exception as e:
            logger.debug(f"查询参数提取失败: {e}")
        
        return surfaces
    
    def _detect_path_params(self, url: str, method: str) -> List[AttackSurface]:
        """检测 RESTful 路径参数"""
        surfaces = []
        
        try:
            parsed = urlparse(url)
            path_segments = [s for s in parsed.path.split('/') if s]
            
            for idx, segment in enumerate(path_segments):
                # 检查是否匹配任何参数模式
                param_type_name = self._match_param_pattern(segment)
                
                if param_type_name:
                    # 构建路径模式 URL
                    normalized_path = self._normalize_path(path_segments, idx)
                    pattern_url = f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
                    
                    surfaces.append(AttackSurface(
                        url=pattern_url,
                        method=method,
                        param_name=segment,  # 原始值作为参数名
                        param_type=ParamType.PATH_PARAM,
                        source=SourceType.URL_ANALYSIS,
                        context={
                            "pattern_type": param_type_name,
                            "position": idx,
                            "sample_value": segment,
                        },
                    ))
                    
        except Exception as e:
            logger.debug(f"路径参数检测失败: {e}")
        
        return surfaces
    
    def _match_param_pattern(self, segment: str) -> str | None:
        """检查路径片段是否匹配参数模式
        
        Args:
            segment: 路径片段
            
        Returns:
            匹配的模式名称，如果不匹配返回 None
        """
        for pattern_name, regex in self.PATTERNS.items():
            if regex.match(segment):
                return pattern_name
        return None
    
    def _normalize_path(self, segments: List[str], param_index: int) -> str:
        """规范化路径，将参数位置替换为占位符
        
        Args:
            segments: 路径片段列表
            param_index: 参数所在位置
            
        Returns:
            规范化的路径
        """
        normalized = segments.copy()
        normalized[param_index] = "{param}"
        return "/" + "/".join(normalized)
