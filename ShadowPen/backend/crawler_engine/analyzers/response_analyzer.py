"""
HTTP Response Analyzer

Monitor HTTP responses and detect security vulnerabilities
"""
from typing import List, Dict, Any, Optional
from playwright.async_api import Response, Request
from ..models import AttackSurface, ParamType, SourceType
import logging
import re

logger = logging.getLogger(__name__)


class ResponseAnalyzer:
    """HTTP Response Analyzer

    Features:
    - Detect HTTP Header Injection (CRLF injection)
    - Identify JSONP endpoint characteristics
    - Analyze CSP policy
    """

    def __init__(self):
        self._captured_surfaces: List[AttackSurface] = []
        self._analyzed_urls: set = set()  # Avoid duplicate analysis
    
    async def analyze_response(
        self, 
        response: Response, 
        current_url: str,
        known_params: List[str] = None
    ) -> List[AttackSurface]:
        """Analyze a single HTTP response

        Args:
            response: Playwright Response object
            current_url: Current page URL
            known_params: List of known parameter names

        Returns:
            List of discovered attack surfaces
        """
        surfaces = []
        request_url = response.url
        
        # Avoid analyzing the same URL twice
        if request_url in self._analyzed_urls:
            return surfaces
        self._analyzed_urls.add(request_url)
        
        try:
            # 1. JSONP detection
            if await self._is_jsonp_response(response):
                jsonp_surface = await self._create_jsonp_surface(response, current_url)
                if jsonp_surface:
                    surfaces.append(jsonp_surface)
                    logger.info(f"Discovered JSONP endpoint: {request_url}")
            
            # 2. Header Injection detection
            if known_params and await self._has_header_injection_risk(response, known_params):
                header_surface = self._create_header_injection_surface(response, current_url)
                if header_surface:
                    surfaces.append(header_surface)
                    logger.warning(f"Header Injection risk detected: {request_url}")
            
            # 3. CSP analysis (optional, log only)
            await self._analyze_csp(response)
            
            # Cache results
            self._captured_surfaces.extend(surfaces)
            
        except Exception as e:
            logger.debug(f"Response analysis failed: {request_url} - {e}")
        
        return surfaces
    
    async def _is_jsonp_response(self, response: Response) -> bool:
        """Identify JSONP response

        Detection conditions:
        1. Content-Type contains javascript
        2. Response body matches callback(...) pattern
        """
        try:
            content_type = response.headers.get('content-type', '').lower()
            
            # Check Content-Type
            if 'javascript' not in content_type and 'json' not in content_type:
                return False
            
            # Get response body
            body = await response.text()
            if not body:
                return False
            
            # Match JSONP pattern: callback_name(...)
            # Allowed patterns: funcName(...), func123(...), $callback(...)
            jsonp_pattern = r'^\s*[\w$]+\s*\('
            if re.match(jsonp_pattern, body):
                return True
            
            return False
            
        except Exception as e:
            logger.debug(f"JSONP detection failed: {e}")
            return False
    
    async def _create_jsonp_surface(
        self, 
        response: Response, 
        current_url: str
    ) -> Optional[AttackSurface]:
        """Create JSONP attack surface

        Extract callback parameter name from URL
        """
        try:
            request = response.request
            url = request.url
            
            # Extract query parameters from URL
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Find possible callback parameter
            callback_param = None
            for param_name in params.keys():
                # Common callback parameter names
                if param_name.lower() in ['callback', 'jsonp', 'cb', 'jsoncallback']:
                    callback_param = param_name
                    break
            
            if not callback_param:
                # If no explicit callback, use the first parameter
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
            logger.debug(f"Failed to create JSONP attack surface: {e}")
            return None
    
    async def _has_header_injection_risk(
        self, 
        response: Response, 
        known_params: List[str]
    ) -> bool:
        """Check if response headers have injection risk

        Check if sensitive response headers contain CRLF characters
        """
        try:
            # Sensitive response headers
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
                
                # Check CRLF sequence
                if '\r' in header_value or '\n' in header_value:
                    logger.warning(
                        f"Found CRLF sequence in response header {header_name}: "
                        f"{repr(header_value[:100])}"
                    )
                    return True
                
                # Check if known parameter values are included (simplified detection)
                for param in known_params:
                    if param in header_value:
                        logger.info(
                            f"Response header {header_name} contains parameter {param}, "
                            f"may have injection risk"
                        )
                        return True
            
            return False
            
        except Exception as e:
            logger.debug(f"Header Injection detection failed: {e}")
            return False
    
    def _create_header_injection_surface(
        self, 
        response: Response, 
        current_url: str
    ) -> Optional[AttackSurface]:
        """Create Header Injection attack surface"""
        try:
            request = response.request
            url = request.url
            
            # Extract parameters from URL
            from urllib.parse import urlparse, parse_qs
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            
            # Found suspicious parameter
            suspicious_param = None
            for param_name in params.keys():
                # Common injectable parameters
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
            logger.debug(f"Failed to create Header Injection attack surface: {e}")
            return None
    
    async def _analyze_csp(self, response: Response):
        """Analyze CSP policy (log only)"""
        try:
            csp = response.headers.get('content-security-policy')
            
            if not csp:
                return
            
            # Check for unsafe directives
            risky_directives = [
                'unsafe-inline',
                'unsafe-eval',
                '*'  # Wildcard
            ]
            
            for directive in risky_directives:
                if directive in csp.lower():
                    logger.warning(
                        f"Detected permissive CSP policy (contains {directive}): "
                        f"{response.url}"
                    )
                    break
            
        except Exception as e:
            logger.debug(f"CSP analysis failed: {e}")
    
    def get_captured_surfaces(self) -> List[AttackSurface]:
        """Get all captured attack surfaces"""
        return self._captured_surfaces.copy()
    
    def clear(self):
        """Clear cache"""
        self._captured_surfaces.clear()
        self._analyzed_urls.clear()
