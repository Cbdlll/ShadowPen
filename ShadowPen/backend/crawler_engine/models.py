"""
XSS Crawler Engine Data Models

Defines core data structures for attack surfaces, parameter types, etc.
"""
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Optional, Dict, Any
import hashlib
import json


class ParamType(str, Enum):
    """Parameter type enumeration"""
    QUERY_PARAM = "query_param"          # URL query parameter
    PATH_PARAM = "path_param"            # URL path parameter
    JSON_BODY = "json_body"              # JSON request body field
    FORM_DATA = "form_data"              # Form data
    FORM_INPUT = "form_input"            # HTML form input
    HIDDEN_INPUT = "hidden_input"        # Hidden input field
    CONTENTEDITABLE = "contenteditable"  # Contenteditable element
    HEADER = "header"                    # HTTP Header


class SourceType(str, Enum):
    """Discovery source enumeration"""
    DOM_FORM = "dom_form"                                # DOM form analysis
    DOM_STATIC = "dom_static"                            # DOM static element
    TRAFFIC_INTERCEPT = "traffic_intercept"              # Traffic interception
    TRAFFIC_INTERCEPT_AFTER_INTERACTION = "traffic_intercept_after_interaction"  # Post-interaction traffic
    URL_ANALYSIS = "url_analysis"                        # URL pattern analysis
    INTERACTION_TRIGGER = "interaction_trigger"          # Interaction trigger


@dataclass
class AttackSurface:
    """Attack surface data model

    Represents a potential XSS injection point
    """
    url: str                                    # Full URL
    method: str                                 # HTTP method (GET, POST, PUT, DELETE, etc.)
    param_name: str                             # Parameter name
    param_type: ParamType                       # Parameter type
    source: SourceType                          # Discovery source

    # Optional fields
    element_selector: Optional[str] = None      # DOM element selector
    element_type: Optional[str] = None          # Element type (input, textarea, etc.)
    raw_request: Optional[str] = None           # Raw request snapshot
    context: Optional[Dict[str, Any]] = None    # Additional context information

    # Hybrid scanner additional fields
    page_url: Optional[str] = None              # Trigger page URL
    action_trigger: str = "page_load"           # Trigger action (page_load, click_button_#id, etc.)
    is_cross_origin: bool = False               # Whether cross-origin request
    timestamp: Optional[str] = None             # Discovery timestamp

    # Deep interaction additional fields
    depth_level: int = 0                        # Interaction depth (0, 1, 2)
    trigger_chain: str = "page_load"            # Full trigger chain
    sample_payload: str = ""                    # Sample payload (for verification)

    # Internal fields
    fingerprint: str = field(init=False)        # Unique fingerprint
    url_pattern: str = field(init=False)        # URL pattern (for deduplication)
    
    def __post_init__(self):
        """Post-initialization: generate fingerprint and URL pattern"""
        # Generate URL pattern (normalize path parameters)
        self.url_pattern = self._normalize_url()
        
        # Generate unique fingerprint
        self.fingerprint = self._generate_fingerprint()
    
    def _normalize_url(self) -> str:
        """Normalize URL, replace path parameters with placeholders

        e.g.: /user/123 -> /user/{id}
              /api/order/uuid-123 -> /api/order/{uuid}
        """
        from urllib.parse import urlparse, parse_qs
        
        parsed = urlparse(self.url)
        path = parsed.path
        
        # If path parameter, replace with placeholder
        if self.param_type == ParamType.PATH_PARAM:
            # Simple strategy: replace parameter value with {param}
            path = path.replace(f"/{self.param_name}", "/{param}")

        # Rebuild URL (excluding query parameters to avoid specific values affecting fingerprint)
        return f"{parsed.scheme}://{parsed.netloc}{path}"
    
    def _generate_fingerprint(self) -> str:
        """Generate unique fingerprint

        Based on: (Method, URL_Pattern, Param_Name, Param_Type)
        """
        fingerprint_data = f"{self.method}|{self.url_pattern}|{self.param_name}|{self.param_type.value}"
        return hashlib.sha256(fingerprint_data.encode()).hexdigest()[:16]
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary (for JSON serialization)"""
        data = asdict(self)
        # Convert enum to string value
        data["param_type"] = self.param_type.value
        # source may be a string or enum
        data["source"] = self.source.value if isinstance(self.source, SourceType) else self.source
        return data
    
    def to_json(self) -> str:
        """Convert to JSON string"""
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
    """Crawl result data model"""
    target_url: str                             # Target URL
    pages_crawled: int                          # Number of pages crawled
    surfaces: list[AttackSurface]               # List of discovered attack surfaces
    errors: list[Dict[str, str]] = field(default_factory=list)  # Error list

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            "target_url": self.target_url,
            "pages_crawled": self.pages_crawled,
            "total_surfaces": len(self.surfaces),
            "surfaces": [s.to_dict() for s in self.surfaces],
            "errors": self.errors,
        }
    
    def to_json(self) -> str:
        """Convert to JSON string"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
