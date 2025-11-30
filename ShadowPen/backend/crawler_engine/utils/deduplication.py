"""
工具模块：去重引擎

基于指纹的攻击面去重机制
"""
from typing import List, Set
from ..models import AttackSurface


class DeduplicationEngine:
    """去重引擎"""
    
    def __init__(self):
        self._seen_fingerprints: Set[str] = set()
    
    def add(self, surface: AttackSurface) -> bool:
        """添加攻击面，如果已存在则返回 False
        
        Args:
            surface: 攻击面对象
            
        Returns:
            bool: True 表示是新记录，False 表示重复
        """
        if surface.fingerprint in self._seen_fingerprints:
            return False
        
        self._seen_fingerprints.add(surface.fingerprint)
        return True
    
    def deduplicate(self, surfaces: List[AttackSurface]) -> List[AttackSurface]:
        """批量去重
        
        Args:
            surfaces: 攻击面列表
            
        Returns:
            去重后的攻击面列表
        """
        unique_surfaces = []
        for surface in surfaces:
            if self.add(surface):
                unique_surfaces.append(surface)
        return unique_surfaces
    
    def reset(self):
        """重置去重记录"""
        self._seen_fingerprints.clear()
    
    def size(self) -> int:
        """返回已记录的唯一指纹数量"""
        return len(self._seen_fingerprints)
    
    @staticmethod
    def deduplicate_list(surfaces: List[AttackSurface]) -> List[AttackSurface]:
        """静态方法：对列表进行去重
        
        Args:
            surfaces: 攻击面列表
            
        Returns:
            去重后的攻击面列表
        """
        seen = set()
        unique = []
        
        for surface in surfaces:
            if surface.fingerprint not in seen:
                seen.add(surface.fingerprint)
                unique.append(surface)
        
        return unique
