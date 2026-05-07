"""
URL Analyzer Module

Intelligently analyze URL structure, identify path and query parameters
"""
from typing import List, Tuple
import re
from urllib.parse import urlparse, parse_qs
from ..models import AttackSurface, ParamType, SourceType
import logging

logger = logging.getLogger(__name__)


class URLAnalyzer:
    """URL Pattern Analyzer

    Features:
    - Identify RESTful path parameters
    - Extract query parameters
    - URL pattern normalization
    """

    # RESTful parameter patterns
    PATTERNS = {
        'numeric': re.compile(r'^[0-9]+$'),           # Numeric only: 123
        'uuid': re.compile(r'^[a-f0-9-]{32,36}$'),    # UUID: a1b2-c3d4-...
        'id_prefix': re.compile(r'^(id|ID)_?\d+$'),   # ID prefix: id_123
        'hash': re.compile(r'^[a-f0-9]{32,64}$'),     # Hash: md5/sha256
    }
    
    def analyze_url(self, url: str, method: str = "GET") -> List[AttackSurface]:
        """Analyze URL and extract attack surfaces

        Args:
            url: Target URL
            method: HTTP method

        Returns:
            List of attack surfaces
        """
        surfaces = []
        
        # 1. Extract query parameters
        surfaces.extend(self._extract_query_params(url, method))
        
        # 2. Detect path parameters
        surfaces.extend(self._detect_path_params(url, method))
        
        return surfaces
    
    def _extract_query_params(self, url: str, method: str) -> List[AttackSurface]:
        """Extract query parameters"""
        surfaces = []
        
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Base URL (without query string)
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
            logger.debug(f"Query parameter extraction failed: {e}")
        
        return surfaces
    
    def _detect_path_params(self, url: str, method: str) -> List[AttackSurface]:
        """Detect RESTful path parameters"""
        surfaces = []
        
        try:
            parsed = urlparse(url)
            path_segments = [s for s in parsed.path.split('/') if s]
            
            for idx, segment in enumerate(path_segments):
                # Check if matches any parameter pattern
                param_type_name = self._match_param_pattern(segment)
                
                if param_type_name:
                    # Build path pattern URL
                    normalized_path = self._normalize_path(path_segments, idx)
                    pattern_url = f"{parsed.scheme}://{parsed.netloc}{normalized_path}"
                    
                    surfaces.append(AttackSurface(
                        url=pattern_url,
                        method=method,
                        param_name=segment,  # Original value as parameter name
                        param_type=ParamType.PATH_PARAM,
                        source=SourceType.URL_ANALYSIS,
                        context={
                            "pattern_type": param_type_name,
                            "position": idx,
                            "sample_value": segment,
                        },
                    ))
                    
        except Exception as e:
            logger.debug(f"Path parameter detection failed: {e}")
        
        return surfaces
    
    def _match_param_pattern(self, segment: str) -> str | None:
        """Check if path segment matches parameter pattern

        Args:
            segment: Path segment

        Returns:
            Matched pattern name, None if no match
        """
        for pattern_name, regex in self.PATTERNS.items():
            if regex.match(segment):
                return pattern_name
        return None
    
    def _normalize_path(self, segments: List[str], param_index: int) -> str:
        """Normalize path, replace parameter position with placeholder

        Args:
            segments: Path segment list
            param_index: Parameter position

        Returns:
            Normalized path
        """
        normalized = segments.copy()
        normalized[param_index] = "{param}"
        return "/" + "/".join(normalized)
