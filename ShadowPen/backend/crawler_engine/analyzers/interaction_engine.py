"""
Interaction Engine Module

Proactively trigger page interactions to capture hidden API requests
"""
from typing import List
from playwright.async_api import Page, TimeoutError as PlaywrightTimeout
from ..models import AttackSurface, SourceType
from .traffic_interceptor import TrafficInterceptor
from ..utils.exceptions import InteractionException
import logging
import asyncio

logger = logging.getLogger(__name__)


class InteractionEngine:
    """Interaction Trigger Engine

    Features:
    - Auto-fill and submit forms
    - Click interactive elements
    - Wait for network requests to complete
    """
    
    def __init__(self, fill_timeout: int = 2000, click_timeout: int = 3000):
        self.fill_timeout = fill_timeout
        self.click_timeout = click_timeout
    
    async def trigger_interactions(
        self,
        page: Page,
        interceptor: TrafficInterceptor
    ) -> List[AttackSurface]:
        """Trigger page interactions

        Args:
            page: Playwright page object
            interceptor: Traffic interceptor (for capturing interaction-triggered requests)

        Returns:
            List of attack surfaces discovered after interaction
        """
        surfaces = []
        
        # Record initial capture count
        initial_count = len(interceptor.get_captured_surfaces())
        
        # 1. Auto-fill and submit forms
        await self._fill_and_submit_forms(page)
        
        # 2. Click interactive elements
        await self._click_interactive_elements(page)
        
        # 3. Wait for network requests to complete
        await asyncio.sleep(1)  # Give requests some time to complete
        
        # 4. Get attack surfaces captured after interaction
        all_surfaces = interceptor.get_captured_surfaces()
        new_surfaces = all_surfaces[initial_count:]
        
        # Mark source as post-interaction traffic
        for surface in new_surfaces:
            surface.source = SourceType.TRAFFIC_INTERCEPT_AFTER_INTERACTION
            surfaces.append(surface)
        
        logger.info(f"Interaction trigger completed, added {len(surfaces)} new attack surfaces")
        return surfaces
    
    async def _fill_and_submit_forms(self, page: Page):
        """Auto-fill and submit forms"""
        try:
            # Find all forms
            forms = await page.query_selector_all('form')
            
            for form in forms:
                try:
                    # Fill form fields
                    await self._fill_form(page, form)
                    
                    # Find submit button
                    submit_btn = await form.query_selector(
                        'button[type="submit"], input[type="submit"]'
                    )
                    
                    if submit_btn:
                        # Click submit button
                        await submit_btn.click(timeout=self.click_timeout)
                        # Wait for possible navigation or request
                        await asyncio.sleep(0.5)
                    else:
                        # Attempt direct form submission
                        await form.evaluate('form => form.submit()')
                        await asyncio.sleep(0.5)
                        
                except PlaywrightTimeout:
                    logger.debug("Form submission timeout")
                except Exception as e:
                    logger.debug(f"Form processing failed: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Form fill failed: {e}")
    
    async def _fill_form(self, page: Page, form):
        """Fill single form"""
        # Find input fields in form
        inputs = await form.query_selector_all(
            'input:not([type="submit"]):not([type="button"]):not([type="hidden"]), textarea'
        )
        
        for input_elem in inputs:
            try:
                input_type = await input_elem.get_attribute('type') or 'text'
                
                # Fill test data based on type
                test_value = self._get_test_value(input_type)
                
                await input_elem.fill(test_value, timeout=self.fill_timeout)
                
            except PlaywrightTimeout:
                continue
            except Exception as e:
                logger.debug(f"Input fill failed: {e}")
                continue
    
    def _get_test_value(self, input_type: str) -> str:
        """Get test fill value"""
        test_values = {
            'text': 'test_value',
            'email': 'test@example.com',
            'password': 'Test123!',
            'tel': '1234567890',
            'number': '123',
            'url': 'https://example.com',
            'search': 'test search',
            'date': '2024-01-01',
        }
        
        return test_values.get(input_type, 'test')
    
    async def _click_interactive_elements(self, page: Page):
        """Click interactive elements"""
        # Interactive element selectors
        selectors = [
            'button:not([type="submit"])',  # Non-submit button
            'a[href="#"]',                   # Anchor link (may trigger JS)
            '[onclick]',                     # Elements with onClick event
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                
                # Limit clicks to avoid excessive interaction
                for element in elements[:5]:  # Max 5 clicks per type
                    try:
                        # Check if element is visible
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue
                        
                        # Click element
                        await element.click(timeout=self.click_timeout)
                        
                        # Brief wait
                        await asyncio.sleep(0.3)
                        
                    except PlaywrightTimeout:
                        continue
                    except Exception as e:
                        logger.debug(f"Element click failed: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"Interactive element lookup failed: {e}")
                continue
