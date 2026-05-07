"""
Traffic Interceptor Module

Monitor and analyze all network requests, extract parameters
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
    """Traffic Interceptor

    Features:
    - Monitor all network requests
    - Parse JSON Body
    - Parse FormData
    - Extract Header parameters
    """
    
    def __init__(self, scope_domains: List[str], capture_all: bool = False, page_url: str = "", action_trigger: str = "page_load"):
        """Initialize traffic interceptor

        Args:
            scope_domains: List of allowed domain scopes
            capture_all: Whether to capture all domain traffic (indiscriminate capture mode)
            page_url: Current page URL (for marking trigger source)
            action_trigger: Trigger action description (e.g. "page_load", "click_button_#id")

        Note: depth_level and trigger_chain are designed as dynamically modifiable properties,
        updated by DeepInteractionEngine at runtime
        """
        self.scope_domains = scope_domains
        self.capture_all = capture_all
        self.page_url = page_url
        self.action_trigger = action_trigger
        
        # Deep interaction related (dynamically modifiable)
        self.depth_level: int = 0
        self.trigger_chain: List[str] = ["page_load"]
        
        self._captured_surfaces: List[AttackSurface] = []
        self._active = False
    
    async def start_interception(self, page: Page):
        """Start traffic interception

        Args:
            page: Playwright page object
        """
        self._active = True
        page.on("request", self._handle_request)
        mode = "indiscriminate capture" if self.capture_all else f"scope: {self.scope_domains}"
        logger.info(f"Traffic interception started ({mode})")
    
    def stop_interception(self):
        """Stop interception"""
        self._active = False
        logger.info("Traffic interception stopped")

    def _get_timestamp(self):
        return datetime.now().isoformat()

    
    def _is_cross_origin(self, request_url: str) -> bool:
        """Determine if request is cross-origin

        Args:
            request_url: Request URL

        Returns:
            True means cross-origin, False means same-origin
        """
        if not self.page_url:
            return False
        
        from ..utils import URLUtils
        return URLUtils.get_domain(request_url) != URLUtils.get_domain(self.page_url)
    
    async def _handle_request(self, request: Request):
        """Handle intercepted request"""
        if not self._active:
            return
        
        try:
            url = request.url
            method = request.method
            
            # Cross-origin check
            is_cross_origin = self._is_cross_origin(url)
            
            # Filter logic
            if not self.capture_all:
                # Non-indiscriminate mode: only process requests within scope
                if not URLUtils.is_in_scope(url, self.scope_domains):
                    return
            # Indiscriminate mode: capture all requests, no filtering needed
            
            # Filter static resources
            resource_type = request.resource_type
            if resource_type in ["image", "stylesheet", "font", "media"]:
                # logger.debug(f"Filtered static resource: {url} ({resource_type})")
                return
            
            # **DEBUG: Log all intercepted requests**
            logger.debug(f"Intercepted request: {method} {url} (crossorigin={is_cross_origin})")
            
            # 1. Analyze POST/PUT/PATCH/DELETE/OPTIONS
            if method.upper() in ["POST", "PUT", "PATCH", "DELETE", "OPTIONS"]:
                post_data = request.post_data or ""  # Allow empty
                
                # Record request even without body (especially OPTIONS and DELETE)
                if method == "OPTIONS":
                     # Record OPTIONS request as cross-origin detection clue
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
                    # Handle data request
                    if post_data:
                        self._parse_post_data(url, method, post_data, request, is_cross_origin)
                    else:
                        # POST/DELETE without body, record URL itself
                        self._captured_surfaces.append(AttackSurface(
                            url=url,
                            method=method,
                            param_name="body", # Mark as empty body
                            param_type=ParamType.JSON_BODY, # Assume
                            source=SourceType.TRAFFIC_INTERCEPT,
                            page_url=self.page_url,
                            action_trigger=self.action_trigger,
                            is_cross_origin=is_cross_origin,
                            timestamp=self._get_timestamp(),
                            depth_level=self.depth_level,
                            trigger_chain=" -> ".join(self.trigger_chain),
                            sample_payload="",
                        ))
            
            # **BUG FIX: Add GET request parameter capture**
            elif method.upper() == "GET":
                # 1. Parse URL query parameters
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
                    logger.debug(f"GET request parameters: {url} ({len(params)} parameters)")
                
                # 2. Detect RESTful path parameters (check if path contains test payload)
                # The test payload used in DeepInteractionEngine is "XSS_SEARCH_TEST"
                path = unquote(parsed.path)
                if "XSS_SEARCH_TEST" in path:
                    # Extract path segments containing payload as parameters
                    segments = path.strip('/').split('/')
                    for i, segment in enumerate(segments):
                        if "XSS_SEARCH_TEST" in segment:
                            self._captured_surfaces.append(AttackSurface(
                                url=url,
                                method=method,
                                param_name=f"path_param_{i}", # Use position as parameter name
                                param_type=ParamType.QUERY_PARAM, # Temporarily classified as QUERY_PARAM or new PATH_PARAM
                                source=SourceType.TRAFFIC_INTERCEPT,
                                page_url=self.page_url,
                                action_trigger=self.action_trigger,
                                is_cross_origin=is_cross_origin,
                                timestamp=self._get_timestamp(),
                                depth_level=self.depth_level,
                                trigger_chain=" -> ".join(self.trigger_chain),
                                sample_payload=segment,
                            ))
                            logger.info(f"Captured RESTful path parameter: {url} (Segment {i})")
            
            # 2. Analyze Query parameters (handled by URL analyzer, skipped here)

            # 3. Optional: analyze Headers
            # self._parse_headers(url, method, request.headers)
            
        except Exception as e:
            logger.debug(f"Request handling failed: {url} - {e}")
    
    def _parse_post_data(self, url: str, method: str, post_data: str, request: Request, is_cross_origin: bool = False):
        """Parse POST data"""
        content_type = request.headers.get("content-type", "")
        
        logger.debug(f"Parse POST data: {url}, content-type={content_type}, body length={len(post_data)}")
        
        # JSON format
        if "application/json" in content_type:
            self._parse_json_body(url, method, post_data, is_cross_origin)
        
        # Form format
        elif "application/x-www-form-urlencoded" in content_type:
            self._parse_form_data(url, method, post_data, is_cross_origin)
        
        # Multipart
        elif "multipart/form-data" in content_type:
            self._parse_multipart_data(url, method, post_data, is_cross_origin)
    
    def _parse_json_body(self, url: str, method: str, json_str: str, is_cross_origin: bool = False):
        """Recursively parse JSON Body"""
        try:
            if not json_str:
                return

            data = json.loads(json_str)
            # Extract all level keys as parameter names
            param_names = self._extract_json_keys(data)
            
            # Add timestamp
            from datetime import datetime
            timestamp = datetime.now().isoformat()
            
            if not param_names:
                logger.debug(f"No parameters found in JSON Body: {url}")
                return

            for param_name in param_names:
                self._captured_surfaces.append(AttackSurface(
                    url=url,
                    method=method,
                    param_name=param_name,
                    param_type=ParamType.JSON_BODY,
                    source=SourceType.TRAFFIC_INTERCEPT,
                    raw_request=json_str[:500],
                    # Hybrid scanner fields
                    page_url=self.page_url,
                    action_trigger=self.action_trigger,
                    is_cross_origin=is_cross_origin,
                    timestamp=timestamp,
                    # Deep interaction fields
                    depth_level=self.depth_level,
                    trigger_chain=" -> ".join(self.trigger_chain),
                    sample_payload="XSS_Probe",
                ))
            logger.debug(f"Captured JSON parameters: {url} -> {param_names}")
                
        except json.JSONDecodeError:
            logger.debug(f"JSON parse failed: {json_str[:100]}")
        except Exception as e:
            logger.debug(f"JSON processing error: {e}")

    def _parse_form_data(self, url: str, method: str, post_data: str, is_cross_origin: bool = False):
        """Parse Form Data"""
        try:
            from urllib.parse import parse_qs
            params = parse_qs(post_data)
            
            # Add timestamp
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
                    # Hybrid scanner fields
                    page_url=self.page_url,
                    action_trigger=self.action_trigger,
                    is_cross_origin=is_cross_origin,
                    timestamp=timestamp,
                    # Deep interaction fields
                    depth_level=self.depth_level,
                    trigger_chain=" -> ".join(self.trigger_chain),
                    sample_payload="XSS_Probe",
                ))
            logger.debug(f"Captured Form parameters: {url} -> {list(params.keys())}")
            
        except Exception as e:
            logger.debug(f"Form Data parsing failed: {e}")
    
    def _extract_json_keys(self, data: Any, prefix: str = "") -> List[str]:
        """Recursively extract all keys from JSON

        Args:
            data: JSON data
            prefix: Key prefix (for nested objects)

        Returns:
            List of key names
        """
        keys = []
        
        if isinstance(data, dict):
            for key, value in data.items():
                full_key = f"{prefix}.{key}" if prefix else key
                keys.append(full_key)
                
                # Recursively process nested objects/arrays
                if isinstance(value, (dict, list)):
                    keys.extend(self._extract_json_keys(value, full_key))
        
        elif isinstance(data, list):
            # Only process the first element as sample
            if data and isinstance(data[0], (dict, list)):
                keys.extend(self._extract_json_keys(data[0], prefix))
        
        return keys
    
    def _parse_form_data(self, url: str, method: str, form_data: str, is_cross_origin: bool = False):
        """Parse application/x-www-form-urlencoded"""
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
            logger.debug(f"Form data parsing failed: {e}")
    
    def _parse_multipart_data(self, url: str, method: str, multipart_data: str, is_cross_origin: bool = False):
        """Parse multipart/form-data (simplified)"""
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
            logger.debug(f"Multipart data parsing failed: {e}")
    
    def get_captured_surfaces(self) -> List[AttackSurface]:
        """Get captured attack surfaces"""
        return self._captured_surfaces.copy()
    
    def clear(self):
        """Clear captured data"""
        self._captured_surfaces.clear()
