"""
JavaScript Hook Injector

Intercept dangerous function calls at runtime to discover JS-based XSS vulnerabilities
"""
from typing import List, Dict, Any
from playwright.async_api import Page
from ..models import AttackSurface, ParamType, SourceType
import logging
import re

logger = logging.getLogger(__name__)


# Hook injection script
HOOK_SCRIPT = """
(function() {
    // Save original functions
    const original = {
        eval: window.eval,
        setTimeout: window.setTimeout,
        setInterval: window.setInterval,
        documentWrite: document.write,
        Function: window.Function
    };
    
    // Result storage
    window.__xss_hook_results = [];
    
    // Hook eval
    window.eval = function(code) {
        window.__xss_hook_results.push({
            function: 'eval',
            argument: String(code),
            stack: new Error().stack,
            timestamp: Date.now()
        });
        return original.eval.apply(this, arguments);
    };
    
    // Hook setTimeout (string form only)
    window.setTimeout = function(code, delay) {
        if (typeof code === 'string') {
            window.__xss_hook_results.push({
                function: 'setTimeout',
                argument: code,
                delay: delay,
                timestamp: Date.now()
            });
        }
        return original.setTimeout.apply(this, arguments);
    };
    
    // Hook setInterval (string form only)
    window.setInterval = function(code, delay) {
        if (typeof code === 'string') {
            window.__xss_hook_results.push({
                function: 'setInterval',
                argument: code,
                delay: delay,
                timestamp: Date.now()
            });
        }
        return original.setInterval.apply(this, arguments);
    };
    
    // Hook document.write
    document.write = function(html) {
        window.__xss_hook_results.push({
            function: 'document.write',
            argument: String(html),
            timestamp: Date.now()
        });
        return original.documentWrite.apply(this, arguments);
    };
    
    // Hook Function constructor
    window.Function = function() {
        const args = Array.from(arguments);
        window.__xss_hook_results.push({
            function: 'Function',
            argument: args.join(', '),
            timestamp: Date.now()
        });
        return original.Function.apply(this, arguments);
    };
    
    // Hook dynamic script creation
    const originalCreateElement = document.createElement;
    document.createElement = function(tagName) {
        const element = originalCreateElement.apply(this, arguments);
        
        if (tagName && tagName.toLowerCase() === 'script') {
            // Hook src property
            const originalSrcDescriptor = Object.getOwnPropertyDescriptor(HTMLScriptElement.prototype, 'src');
            if (originalSrcDescriptor && originalSrcDescriptor.set) {
                Object.defineProperty(element, 'src', {
                    set: function(value) {
                        window.__xss_hook_results.push({
                            function: 'dynamic_script_src',
                            argument: String(value),
                            timestamp: Date.now()
                        });
                        originalSrcDescriptor.set.call(this, value);
                    },
                    get: originalSrcDescriptor.get
                });
            }
            
            // Hook textContent property
            const originalTextContentDescriptor = Object.getOwnPropertyDescriptor(Node.prototype, 'textContent');
            if (originalTextContentDescriptor && originalTextContentDescriptor.set) {
                Object.defineProperty(element, 'textContent', {
                    set: function(value) {
                        if (value) {
                            window.__xss_hook_results.push({
                                function: 'dynamic_script_content',
                                argument: String(value),
                                timestamp: Date.now()
                            });
                        }
                        originalTextContentDescriptor.set.call(this, value);
                    },
                    get: originalTextContentDescriptor.get
                });
            }
        }
        
        return element;
    };
    
    console.log('[XSS Hook] JavaScript Hook injected');
})();
"""


class JSHookInjector:
    """JavaScript Hook Injector

    Features:
    - Inject Hook script before page load
    - Intercept eval, setTimeout, setInterval, document.write, Function
    - Intercept dynamic script tag creation
    - Extract parameter references, identify XSS risks
    """
    
    async def inject_hooks(self, page: Page):
        """Inject Hook before page load

        Args:
            page: Playwright page object
        """
        try:
            await page.add_init_script(HOOK_SCRIPT)
            logger.debug("JS Hook script injected")
        except Exception as e:
            logger.error(f"Hook injection failed: {e}")
    
    async def collect_results(self, page: Page, current_url: str) -> List[AttackSurface]:
        """Collect Hook results and convert to attack surfaces

        Args:
            page: Playwright page object
            current_url: Current page URL

        Returns:
            List of attack surfaces
        """
        surfaces = []
        
        try:
            # Get Hook results
            results = await page.evaluate("() => window.__xss_hook_results || []")
            
            if not results:
                logger.debug("No dangerous function calls captured")
                return surfaces
            
            logger.info(f"Captured {len(results)} dangerous function calls")
            
            # Process each result
            for result in results:
                func_name = result.get('function', 'unknown')
                argument = result.get('argument', '')
                
                # Extract parameter references
                params = self._extract_params_from_code(argument)
                
                if params:
                    # Found parameter references, creating attack surfaces
                    for param in params:
                        surfaces.append(AttackSurface(
                            url=current_url,
                            method="GET",  # Usually client-side processing
                            param_name=param,
                            param_type=ParamType.JS_DYNAMIC,
                            source=SourceType.JS_STATIC_ANALYSIS,
                            dangerous_function=func_name,
                            sample_payload=argument[:200],  # Truncate to avoid being too long
                            element_type=func_name
                        ))
                else:
                    # Record dangerous function call even without parameter references
                    surfaces.append(AttackSurface(
                        url=current_url,
                        method="GET",
                        param_name=f"{func_name}_dynamic",
                        param_type=ParamType.JS_DYNAMIC,
                        source=SourceType.JS_STATIC_ANALYSIS,
                        dangerous_function=func_name,
                        sample_payload=argument[:200],
                        element_type=func_name
                    ))
            
            logger.info(f"JS Hook analysis completed, found {len(surfaces)} attack surfaces")
            
        except Exception as e:
            logger.error(f"Hook result collection failed: {e}")
        
        return surfaces
    
    def _extract_params_from_code(self, code: str) -> List[str]:
        """Extract URL parameter references from JS code

        Args:
            code: JavaScript code string

        Returns:
            List of parameter names
        """
        params = set()
        
        # Pattern 1: URLSearchParams.get('param')
        pattern1 = r"\.get\(['\"](\w+)['\"]\)"
        params.update(re.findall(pattern1, code))
        
        # Pattern 2: params.param or query.param
        pattern2 = r"(?:params|query|search)\.(\w+)"
        params.update(re.findall(pattern2, code))
        
        # Pattern 3: query['param'] or query["param"]
        pattern3 = r"(?:params|query|search)\[['\"](\w+)['\"]\]"
        params.update(re.findall(pattern3, code))
        
        # Pattern 4: location.search (generic)
        if 'location.search' in code or 'window.location.search' in code:
            params.add('_url_search_')
        
        # Pattern 5: location.hash
        if 'location.hash' in code or 'window.location.hash' in code:
            params.add('_url_hash_')
        
        # Pattern 6: document.URL
        if 'document.URL' in code or 'document.url' in code:
            params.add('_document_url_')
        
        return list(params)
    
    async def clear_results(self, page: Page):
        """Clear Hook results

        Args:
            page: Playwright page object
        """
        try:
            await page.evaluate("() => { window.__xss_hook_results = []; }")
        except Exception as e:
            logger.debug(f"Failed to clear Hook results: {e}")
