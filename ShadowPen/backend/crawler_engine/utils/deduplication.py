"""
Utils module: Deduplication Engine

Fingerprint-based attack surface deduplication mechanism
"""
from typing import List, Set
from ..models import AttackSurface


class DeduplicationEngine:
    """Deduplication Engine"""
    
    def __init__(self):
        self._seen_fingerprints: Set[str] = set()
    
    def add(self, surface: AttackSurface) -> bool:
        """Add an attack surface. Returns False if it already exists.

        Args:
            surface: Attack surface object

        Returns:
            bool: True means new record, False means duplicate
        """
        if surface.fingerprint in self._seen_fingerprints:
            return False
        
        self._seen_fingerprints.add(surface.fingerprint)
        return True
    
    def deduplicate(self, surfaces: List[AttackSurface]) -> List[AttackSurface]:
        """Batch deduplication

        Args:
            surfaces: List of attack surfaces

        Returns:
            Deduplicated list of attack surfaces
        """
        unique_surfaces = []
        for surface in surfaces:
            if self.add(surface):
                unique_surfaces.append(surface)
        return unique_surfaces
    
    def reset(self):
        """Reset deduplication records"""
        self._seen_fingerprints.clear()
    
    def size(self) -> int:
        """Return the number of recorded unique fingerprints"""
        return len(self._seen_fingerprints)
    
    @staticmethod
    def deduplicate_list(surfaces: List[AttackSurface]) -> List[AttackSurface]:
        """Static method: deduplicate a list

        Args:
            surfaces: List of attack surfaces

        Returns:
            Deduplicated list of attack surfaces
        """
        seen = set()
        unique = []
        
        for surface in surfaces:
            if surface.fingerprint not in seen:
                seen.add(surface.fingerprint)
                unique.append(surface)
        
        return unique
