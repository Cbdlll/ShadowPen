"""
DOM Analyzer Module

Deeply analyze page DOM structure, extract all possible input points
"""
from typing import List, Optional
from playwright.async_api import Page
from ..models import AttackSurface, ParamType, SourceType
from ..utils.exceptions import CrawlerException
import logging

logger = logging.getLogger(__name__)


class DOMAnalyzer:
    """DOM Static Analyzer

    Features:
    - Extract form input elements
    - Identify hidden input fields
    - Identify contenteditable elements
    - Penetrate Shadow DOM
    """
    
    async def analyze_page(self, page: Page, current_url: str) -> List[AttackSurface]:
        """Analyze page DOM and extract attack surfaces

        Args:
            page: Playwright page object
            current_url: Current page URL

        Returns:
            List of attack surfaces
        """
        surfaces = []
        
        try:
            # 1. Extract standard form inputs
            surfaces.extend(await self._extract_form_inputs(page, current_url))
            
            # 2. Extract hidden inputs
            surfaces.extend(await self._extract_hidden_inputs(page, current_url))
            
            # 3. Extract contenteditable elements
            surfaces.extend(await self._extract_contenteditable(page, current_url))
            
            # 4. Penetrate Shadow DOM
            surfaces.extend(await self._extract_shadow_dom_inputs(page, current_url))
            
        except Exception as e:
            logger.error(f"DOM analysis failed: {e}")
            raise CrawlerException(f"DOM analysis failed: {e}")
        
        logger.info(f"DOM analysis completed, found {len(surfaces)} attack surfaces")
        return surfaces
    
    async def _extract_form_inputs(self, page: Page, current_url: str) -> List[AttackSurface]:
        """Extract form input elements"""
        surfaces = []
        
        # Find all input elements (excluding hidden)
        input_selectors = [
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
            'textarea',
            'select',
        ]
        
        for selector in input_selectors:
            try:
                elements = await page.query_selector_all(selector)
                
                for element in elements:
                    # Get element attributes
                    name = await element.get_attribute('name')
                    elem_id = await element.get_attribute('id')
                    elem_type = await element.get_attribute('type') or selector.split('[')[0]
                    
                    # Parameter name prefers name, then id
                    param_name = name or elem_id
                    
                    # Skip inputs without name or id
                    # Unless it is an obvious search box
                    if not param_name:
                        is_search = False
                        # Check if it has search characteristics
                        try:
                            placeholder = await element.get_attribute('placeholder') or ''
                            aria_label = await element.get_attribute('aria-label') or ''
                            title = await element.get_attribute('title') or ''
                            class_attr = await element.get_attribute('class') or ''
                            
                            # Comprehensive judgment
                            search_indicators = [placeholder, aria_label, title, class_attr, elem_type]
                            if any('search' in s.lower() for s in search_indicators):
                                is_search = True
                                # Try to extract a more meaningful name from attributes
                                for attr in [placeholder, aria_label, title]:
                                    if attr:
                                        # Clean string: lowercase, replace non-alphanumeric with underscore
                                        import re
                                        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', attr).strip('_').lower()
                                        if clean_name:
                                            param_name = clean_name
                                            break
                                
                                # Fallback name
                                if not param_name:
                                    param_name = "search_input"
                        except:
                            pass
                            
                        if not is_search:
                            continue
                    
                    # Determine the form's method
                    form = await element.evaluate_handle('el => el.form')
                    method = "GET"
                    action = current_url
                    
                    if form:
                        method = await form.evaluate('f => f.method || "GET"')
                        action = await form.evaluate('f => f.action || window.location.href')
                        method = method.upper()
                    
                    surfaces.append(AttackSurface(
                        url=action,
                        method=method,
                        param_name=param_name,
                        param_type=ParamType.FORM_INPUT,
                        source=SourceType.DOM_FORM,
                        element_selector=selector,
                        element_type=elem_type,
                    ))
                    
            except Exception as e:
                logger.debug(f"Extract {selector} failed: {e}")
                continue
        
        return surfaces
    
    async def _extract_hidden_inputs(self, page: Page, current_url: str) -> List[AttackSurface]:
        """Extract hidden input fields"""
        surfaces = []
        
        try:
            hidden_inputs = await page.query_selector_all('input[type="hidden"]')
            
            for element in hidden_inputs:
                name = await element.get_attribute('name')
                if not name:
                    continue
                
                # Get form info
                form = await element.evaluate_handle('el => el.form')
                method = "POST"
                action = current_url
                
                if form:
                    method = await form.evaluate('f => f.method || "POST"')
                    action = await form.evaluate('f => f.action || window.location.href')
                    method = method.upper()
                
                surfaces.append(AttackSurface(
                    url=action,
                    method=method,
                    param_name=name,
                    param_type=ParamType.HIDDEN_INPUT,
                    source=SourceType.DOM_STATIC,
                    element_selector='input[type="hidden"]',
                    element_type="hidden",
                ))
                
        except Exception as e:
            logger.debug(f"Failed to extract hidden inputs: {e}")
        
        return surfaces
    
    async def _extract_contenteditable(self, page: Page, current_url: str) -> List[AttackSurface]:
        """Extract contenteditable elements"""
        surfaces = []
        
        try:
            elements = await page.query_selector_all('[contenteditable="true"]')
            
            for idx, element in enumerate(elements):
                elem_id = await element.get_attribute('id')
                param_name = elem_id or f"contenteditable_{idx}"
                
                surfaces.append(AttackSurface(
                    url=current_url,
                    method="POST",  # Assume rich text is usually submitted via POST
                    param_name=param_name,
                    param_type=ParamType.CONTENTEDITABLE,
                    source=SourceType.DOM_STATIC,
                    element_selector='[contenteditable="true"]',
                    element_type="contenteditable",
                ))
                
        except Exception as e:
            logger.debug(f"Failed to extract contenteditable: {e}")
        
        return surfaces
    
    async def _extract_shadow_dom_inputs(self, page: Page, current_url: str) -> List[AttackSurface]:
        """Penetrate Shadow DOM to extract inputs"""
        surfaces = []
        
        try:
            # Execute JS script to penetrate Shadow DOM
            shadow_inputs = await page.evaluate("""
                () => {
                    const inputs = [];
                    
                    function traverseShadow(root) {
                        // Find all input elements
                        const selectors = [
                            'input:not([type="submit"]):not([type="button"])',
                            'textarea',
                            'select'
                        ];
                        
                        for (const selector of selectors) {
                            const elements = root.querySelectorAll(selector);
                            elements.forEach(el => {
                                inputs.push({
                                    name: el.name || el.id || '',
                                    type: el.type || selector.split(':')[0],
                                    isHidden: el.type === 'hidden'
                                });
                            });
                        }
                        
                        // Recursively traverse Shadow Root
                        const shadowHosts = root.querySelectorAll('*');
                        shadowHosts.forEach(host => {
                            if (host.shadowRoot) {
                                traverseShadow(host.shadowRoot);
                            }
                        });
                    }
                    
                    traverseShadow(document);
                    return inputs;
                }
            """)
            
            for input_data in shadow_inputs:
                if not input_data.get('name'):
                    continue
                
                param_type = ParamType.HIDDEN_INPUT if input_data.get('isHidden') else ParamType.FORM_INPUT
                
                surfaces.append(AttackSurface(
                    url=current_url,
                    method="POST",
                    param_name=input_data['name'],
                    param_type=param_type,
                    source=SourceType.DOM_STATIC,
                    element_selector="shadow_dom",
                    element_type=input_data.get('type', 'unknown'),
                ))
                
        except Exception as e:
            logger.debug(f"Shadow DOM penetration failed: {e}")
        
        return surfaces
