"""
结果持久化模块

实时追加写入扫描结果到 JSON 文件
"""
import json
import asyncio
import os
from typing import Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResultWriter:
    """结果写入器
    
    功能：
    - 实时追加写入 JSON
    - 文件锁保护（防止并发写入冲突）
    - 断点续传（文件已存在时继续追加）
    """
    
    def __init__(self, output_file: str = "result.json"):
        """
        Args:
            output_file: 输出文件路径
        """
        self.output_file = Path(output_file)
        self.lock = asyncio.Lock()
        self._init_file()
    
    def _init_file(self):
        """初始化输出文件"""
        if not self.output_file.exists():
            # 创建空 JSON 数组
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.info(f"创建输出文件: {self.output_file}")
        else:
            logger.info(f"输出文件已存在，将追加写入: {self.output_file}")
    
    async def append_surface(self, surface: Dict[str, Any]):
        """追加单条攻击面记录
        
        Args:
            surface: 攻击面字典
        """
        async with self.lock:
            try:
                # 读取现有数据
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # 追加新记录
                data.append(surface)
                
                # 写回文件
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                logger.error(f"写入结果失败: {e}")
    
    def _surface_to_dict(self, surface: Any) -> Dict[str, Any]:
        """将 AttackSurface 对象转换为字典"""
        if hasattr(surface, 'to_dict') and callable(surface.to_dict):
            return surface.to_dict()
        elif isinstance(surface, dict):
            return surface
        else:
            # Fallback for objects without a to_dict method, attempting to convert attributes
            return {k: v for k, v in surface.__dict__.items() if not k.startswith('_')}

    def write_surfaces(self, surfaces: List[Any]) -> None:
        """写入攻击面到文件（追加模式，带去重）
        
        去重策略: 基于 (request_url, method, param_name) 组合
        """
        if not surfaces:
            return
        
        # 读取现有数据
        existing_data = []
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning(f"无法读取现有文件 {self.output_file}，将创建新文件或覆盖")
                existing_data = []
        
        # 构建去重集合 (基于 request_url + method + param_name)
        seen_keys = set()
        for item in existing_data:
            key = f"{item.get('request_url', '')}|{item.get('method', '')}|{item.get('param_name', '')}"
            seen_keys.add(key)
        
        # 转换新攻击面为字典
        new_data = []
        duplicates_count = 0
        for surface in surfaces:
            surface_dict = self._surface_to_dict(surface)
            key = f"{surface_dict.get('request_url', '')}|{surface_dict.get('method', '')}|{surface_dict.get('param_name', '')}"
            
            # 去重检查
            if key not in seen_keys:
                new_data.append(surface_dict)
                seen_keys.add(key)
            else:
                duplicates_count += 1
        
        if duplicates_count > 0:
            logger.debug(f"去重: 跳过 {duplicates_count} 个重复攻击面")
        
        # 合并数据
        all_data = existing_data + new_data
        
        # 写入文件
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"写入 {len(new_data)} 个新攻击面到 {self.output_file} (总计 {len(all_data)} 个)")
        except Exception as e:
            logger.error(f"写入结果失败: {e}")
    
    def read_all(self) -> List[Dict[str, Any]]:
        """读取所有记录
        
        Returns:
            所有攻击面记录
        """
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"读取结果失败: {e}")
            return []
    
    def get_count(self) -> int:
        """获取记录数量"""
        return len(self.read_all())
    
    def clear(self):
        """清空文件"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        logger.info("已清空输出文件")
