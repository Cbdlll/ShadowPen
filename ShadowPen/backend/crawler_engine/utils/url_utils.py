"""
Utils module: URL Processing Utilities

Provides URL parsing, normalization, domain checking, and other functions
"""
from urllib.parse import urlparse, urljoin, parse_qs
from typing import Optional, List


class URLUtils:
    """URL utility class"""
    
    @staticmethod
    def normalize_url(url: str) -> str:
        """Normalize URL, remove fragment"""
        parsed = urlparse(url)
        return f"{parsed.scheme}://{parsed.netloc}{parsed.path}" + (
            f"?{parsed.query}" if parsed.query else ""
        )
    
    @staticmethod
    def get_domain(url: str) -> str:
        """Extract domain (hostname without port)"""
        parsed = urlparse(url)
        # Separate hostname and port
        hostname = parsed.hostname or parsed.netloc.split(':')[0]
        return hostname
    
    @staticmethod
    def is_same_domain(url1: str, url2: str) -> bool:
        """Check whether two URLs belong to the same domain"""
        return URLUtils.get_domain(url1) == URLUtils.get_domain(url2)
    
    @staticmethod
    def is_in_scope(url: str, scope_domains: str | List[str]) -> bool:
        """Check whether a URL is within the crawling scope

        Args:
            url: URL to check
            scope_domains: Allowed domain scope (single string or list of strings)
        """
        if not scope_domains:
            return True
            
        if isinstance(scope_domains, str):
            scope_domains = [scope_domains]
            
        url_domain = URLUtils.get_domain(url)
        
        for scope in scope_domains:
            # Handle scope containing port
            scope_hostname = scope.split(':')[0] if ':' in scope else scope
            
            # Check for match (exact match or subdomain)
            if url_domain == scope_hostname or url_domain.endswith(f".{scope_hostname}"):
                return True
                
        # Special handling for localhost and 127.0.0.1 interchangeability
        if url_domain in ['localhost', '127.0.0.1']:
            for scope in scope_domains:
                scope_hostname = scope.split(':')[0] if ':' in scope else scope
                if scope_hostname in ['localhost', '127.0.0.1']:
                    return True
                    
        return False    
    @staticmethod
    def resolve_relative_url(base_url: str, relative_url: str) -> str:
        """Convert a relative URL to an absolute URL"""
        return urljoin(base_url, relative_url)
    
    @staticmethod
    def extract_query_params(url: str) -> dict:
        """Extract URL query parameters"""
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # Convert list values to single value (take the first one)
        return {k: v[0] if len(v) == 1 else v for k, v in params.items()}
    
    @staticmethod
    def is_valid_http_url(url: str) -> bool:
        """Check whether it is a valid HTTP(S) URL"""
        try:
            parsed = urlparse(url)
            return parsed.scheme in ("http", "https") and bool(parsed.netloc)
        except:
            return False
