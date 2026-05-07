"""
Deep Interaction Engine (Depth=2 BFS Algorithm)

Implements intelligent interaction exploration to discover input points hidden in dynamic components like Modals, Tabs, Drawers, etc.
"""
import asyncio
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Set, Optional, Deque
from collections import deque

from playwright.async_api import Page, ElementHandle, TimeoutError as PlaywrightTimeout

from ..models import AttackSurface, ParamType, SourceType

logger = logging.getLogger(__name__)


@dataclass
class InteractionNode:
    """Interaction node (BFS queue element)"""
    element_selector: str              # Element selector
    element_fingerprint: str           # Element fingerprint (for deduplication)
    element_text: str                  # Element text
    depth: int                         # Current depth (0, 1, 2)
    trigger_chain: List[str]           # Trigger chain
    element_handle: Optional[ElementHandle] = None  # Playwright element handle


class DeepInteractionEngine:
    """Deep Interaction Engine

    Core algorithm: BFS breadth-first exploration
    - Depth 0: Initial page state
    - Depth 1: First interaction trigger (e.g. click button)
    - Depth 2: Second interaction trigger (e.g. click submit in modal)
    """
    
    def __init__(
        self,
        max_depth: int = 2,
        max_actions: int = 50,
        interaction_timeout: int = 3000,
        wait_after_click: float = 0.5,
        global_dedup=None  # GlobalDeduplicationManager instance
    ):
        """
        Args:
            max_depth: Maximum interaction depth
            max_actions: Maximum actions per page (circuit breaker)
            interaction_timeout: Single interaction timeout (milliseconds)
            wait_after_click: Wait time after click (seconds)
            global_dedup: Global deduplication manager
        """
        self.max_depth = max_depth
        self.max_actions = max_actions
        self.interaction_timeout = interaction_timeout
        self.wait_after_click = wait_after_click
        self.global_dedup = global_dedup  # Global deduplicator

        # State tracking (page-level deduplication, supplement to global deduplication)
        self._visited_fingerprints: Set[str] = set()
        self._known_element_fingerprints: Set[str] = set()  # **P2-A: Maintain known element fingerprints**
        self._action_count = 0
        self._captured_surfaces: List[AttackSurface] = []
    
    async def explore_page(
        self,
        page: Page,
        traffic_interceptor,  # TrafficInterceptor instance
        base_url: str
    ) -> List[AttackSurface]:
        """BFS explore page

        Args:
            page: Playwright page object
            traffic_interceptor: Traffic interceptor (for syncing depth information)
            base_url: Base URL

        Returns:
            List of discovered attack surfaces
        """
        logger.info(f"Starting deep interaction exploration (max_depth={self.max_depth})")
        
        # Initialize queue
        queue: Deque[InteractionNode] = deque()
        
        # Depth 0: Scan initial page elements
        initial_elements = await self._find_interactive_elements(page)
        for elem in initial_elements:
            node = await self._create_interaction_node(page, elem, depth=0, trigger_chain=["page_load"])
            if node:
                queue.append(node)
        
        logger.info(f"Initialized queue: {len(queue)} interactive elements")
        
        # BFS traversal
        while queue and self._action_count < self.max_actions:
            node = queue.popleft()
            
            # Page-level deduplication check (quick filter)
            if node.element_fingerprint in self._visited_fingerprints:
                continue
            
            self._visited_fingerprints.add(node.element_fingerprint)
            
            # Global deduplication check (cross-page deduplication)
            if self.global_dedup and not await self._should_interact_with_element(page, node):
                logger.debug(f"Global dedup skipped: {node.element_text[:30]}")
                continue
            
            # **BUG FIX: Proactively submit all forms on the page**
            # Only submit at initial depth (depth=0) to avoid duplicates
            # 3. Proactively submit forms (P1: critical fix)
            current_url = page.url # Get current page URL
            await self._submit_all_forms(page, traffic_interceptor, current_url)
            
            # 4. Proactively trigger search inputs (P2: navbar search optimization)
            await self._trigger_search_inputs(page, traffic_interceptor)
            
            # Execute interaction
            success = await self._perform_interaction(page, node, traffic_interceptor)
            self._action_count += 1
            
            if not success:
                continue
            
            # Wait for DOM to stabilize
            await asyncio.sleep(0.2)
            
            # If depth limit not reached, scan for new elements
            if node.depth < self.max_depth:
                new_elements = await self._detect_new_elements(page)
                for elem in new_elements:
                    new_node = await self._create_interaction_node(
                        page,
                        elem,
                        depth=node.depth + 1,
                        trigger_chain=node.trigger_chain + [f"click_{node.element_text[:20]}"]
                    )
                    if new_node and new_node.element_fingerprint not in self._visited_fingerprints:
                        queue.append(new_node)
        
        logger.info(
            f"Interaction exploration completed: executed {self._action_count} actions, "
            f"visited {len(self._visited_fingerprints)} unique elements"
        )
        
        # Merge traffic interceptor captured results
        all_surfaces = self._captured_surfaces + traffic_interceptor.get_captured_surfaces()
        return all_surfaces
    
    async def _find_interactive_elements(self, page: Page) -> List[ElementHandle]:
        """Find all interactive elements (**P2-B: extended version**)"""
        # **P2-B: Extended selectors, including event triggers**
        selector = """
            button:not([disabled]),
            a[href]:not([href^="#"]):not([href=""]),
            input[type="submit"]:not([disabled]),
            input[type="button"]:not([disabled]),
            [role="button"],
            [onclick],
            [onmouseover],
            [onmouseenter],
            [onfocus],
            select[onchange],
            input[onchange],
            .btn,
            .button
        """
        
        try:
            elements = await page.query_selector_all(selector)
            # Filter invisible elements
            visible_elements = []
            for elem in elements:
                is_visible = await elem.is_visible()
                if is_visible:
                    visible_elements.append(elem)
            return visible_elements
        except Exception as e:
            logger.debug(f"Failed to find interactive elements: {e}")
            return []
    
    async def _create_interaction_node(
        self,
        page: Page,
        element: ElementHandle,
        depth: int,
        trigger_chain: List[str]
    ) -> Optional[InteractionNode]:
        """Create interaction node"""
        try:
            # Get element info
            text = await element.text_content() or ""
            text = text.strip()[:50]
            
            # Generate selector
            selector = await element.evaluate("""
                el => {
                    if (el.id) return '#' + el.id;
                    const classes = Array.from(el.classList).join('.');
                    return el.tagName.toLowerCase() + (classes ? '.' + classes : '');
                }
            """)
            
            # Generate fingerprint
            bounds = await element.bounding_box()
            fingerprint_data = f"{page.url}|{selector}|{text}|{bounds}"
            fingerprint = hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
            
            return InteractionNode(
                element_selector=selector,
                element_fingerprint=fingerprint,
                element_text=text,
                depth=depth,
                trigger_chain=trigger_chain.copy(),
                element_handle=element
            )
            
        except Exception as e:
            logger.debug(f"Failed to create interaction node: {e}")
            return None
    
    async def _should_interact_with_element(
        self,
        page: Page,
        node: InteractionNode
    ) -> bool:
        """Determine if should interact with element (global deduplication check)

        Returns:
            True means should interact, False means skip
        """
        if not self.global_dedup:
            return True
        
        try:
            # 1. Check if it is a link
            tag_name = await node.element_handle.evaluate('el => el.tagName')
            if tag_name and tag_name.lower() == 'a':
                href = await node.element_handle.get_attribute('href')
                if href:
                    from urllib.parse import urljoin
                    absolute_url = urljoin(page.url, href)
                    if not self.global_dedup.should_visit_url(absolute_url):
                        return False
            
            # 2. Check element fingerprint (global deduplication)
            if not self.global_dedup.should_click_element(
                element_text=node.element_text,
                element_selector=node.element_selector,
                page_url=page.url,
                is_navigation=None  # Auto-detect
            ):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"Global deduplication check failed: {e}")
            return True  # Allow interaction on failure
    
    async def _perform_interaction(
        self,
        page: Page,
        node: InteractionNode,
        traffic_interceptor
    ) -> bool:
        """Execute interaction (**P2-B: supports multiple trigger types**)

        Returns:
            Returns True on success, False on failure
        """
        try:
            # Pre-fill form
            await self._pre_fill_forms(page, node.element_handle)
            
            # Update traffic interceptor depth and trigger chain
            traffic_interceptor.depth_level = node.depth
            traffic_interceptor.trigger_chain = node.trigger_chain
            traffic_interceptor.action_trigger = f"click_{node.element_text[:20]}"
            
            # **P2-B: Determine interaction type**
            elem = node.element_handle
            tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")
            
            # Check for special event handlers
            has_onmouseover = await elem.evaluate("el => !!el.onmouseover")
            has_onchange = await elem.evaluate("el => !!el.onchange")
            
            if has_onmouseover:
                # Trigger mouseover event
                logger.debug(
                    f"[Depth {node.depth}] Trigger onmouseover: {node.element_selector} "
                    f"({node.element_text[:30]})"
                )
                await elem.hover(timeout=self.interaction_timeout)
            
            elif tag_name == 'select' or has_onchange:
                # Select dropdown or trigger change event
                logger.debug(
                    f"[Depth {node.depth}] Trigger onchange: {node.element_selector}"
                )
                if tag_name == 'select':
                    # Select second option (skip default value)
                    try:
                        await elem.select_option(index=1)
                    except:
                        await elem.select_option(index=0)
                else:
                    # For input, modify value to trigger change
                    await elem.fill("XSS_Probe_Change")
            
            else:
                # Default click
                logger.debug(
                    f"[Depth {node.depth}] Click element: {node.element_selector} "
                    f"({node.element_text[:30]})"
                )
                await elem.click(timeout=self.interaction_timeout)
            
            # **BUG FIX: Increase wait time to ensure async requests (like form submissions) complete**
            await asyncio.sleep(self.wait_after_click + 1.0)  # Additional 1 second
            
            # Attempt to wait for network idle
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass  # Ignore timeout
            
            return True
            
        except PlaywrightTimeout:
            logger.debug(f"Interaction timeout: {node.element_selector}")
            return False
        except Exception as e:
            logger.debug(f"Interaction failed: {e}")
            return False
    
    async def _pre_fill_forms(self, page: Page, element: ElementHandle):
        """Pre-fill form: auto-fill nearby input fields"""
        try:
            # Find nearby forms or global input fields (including select)
            nearby_elements = await element.evaluate("""
                el => {
                    // 1. Try to find owning form
                    const form = el.closest('form');
                    let elements = [];
                    
                    if (form) {
                        // Include input, textarea, select
                        elements = Array.from(form.querySelectorAll('input:not([type="submit"]):not([type="button"]), textarea, select'));
                    } else {
                        // 2. If no form (common in SPA), find all visible elements on page
                        elements = Array.from(document.querySelectorAll('input:not([type="submit"]):not([type="button"]), textarea, select'));
                        
                        // Filter out hidden ones
                        elements = elements.filter(i => {
                            const style = window.getComputedStyle(i);
                            return style.display !== 'none' && style.visibility !== 'hidden';
                        });
                    }
                    
                    return elements.map(elem => ({
                        selector: elem.id ? '#' + elem.id : elem.name ? '[name="' + elem.name + '"]' : null,
                        type: elem.type || elem.tagName.toLowerCase(),
                        tagName: elem.tagName.toLowerCase(),
                        className: elem.className,
                        hasOptions: elem.tagName.toLowerCase() === 'select' && elem.options.length > 0,
                        firstOptionValue: elem.tagName.toLowerCase() === 'select' && elem.options.length > 1 ? elem.options[1].value : ''
                    })).filter(x => x.selector || x.className);
                }
            """)
            
            # Fill form
            for elem_info in nearby_elements:
                try:
                    selector = elem_info.get('selector')
                    if not selector and elem_info.get('className'):
                        # Try to build class selector
                        classes = elem_info['className'].split()
                        if classes:
                            selector = '.' + '.'.join(classes)
                            
                    if not selector:
                        continue

                    form_elem = await page.query_selector(selector)
                    if not form_elem:
                        continue
                    
                    # Handle select element
                    if elem_info.get('tagName') == 'select':
                        if elem_info.get('hasOptions') and elem_info.get('firstOptionValue'):
                            try:
                                await form_elem.select_option(elem_info['firstOptionValue'])
                                await form_elem.evaluate("""el => {
                                    el.dispatchEvent(new Event('change', { bubbles: true }));
                                }""")
                            except:
                                pass
                        continue
                    
                    # Handle input and textarea
                    try:
                        # Check if already filled
                        value = await form_elem.input_value()
                        if value:
                            continue
                    except:
                        pass
                        
                    # Fill different values based on type
                    elem_type = elem_info.get('type', '')
                    if elem_type == 'email':
                        await form_elem.fill("xss_probe@test.com")
                    elif elem_type == 'tel':
                        await form_elem.fill("1234567890")
                    elif elem_type == 'number':
                        await form_elem.fill("123")
                    elif elem_type == 'url':
                        await form_elem.fill("http://attacker.com")
                    else:
                        await form_elem.fill("XSS_Probe")
                    
                    # Manually trigger events for React/Vue compatibility
                    await form_elem.evaluate("""el => {
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""")
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug(f"Pre-fill form failed: {e}")
    
    async def _detect_new_elements(self, page: Page) -> List[ElementHandle]:
        """Detect newly appeared elements (**P2-A: real DOM diff comparison**)

        Compare element sets before and after interaction, only return new elements
        """
        # Wait for animation/rendering to complete
        await asyncio.sleep(0.3)
        
        # Get all current interactive elements
        current_elements = await self._find_interactive_elements(page)
        
        # Extract new elements
        new_elements = []
        
        for elem in current_elements:
            try:
                # Generate element fingerprint
                fingerprint = await self._generate_element_fingerprint(page, elem)
                
                if not fingerprint:
                    continue
                
                # Check if it is a new element
                if fingerprint not in self._known_element_fingerprints:
                    new_elements.append(elem)
                    self._known_element_fingerprints.add(fingerprint)
                    
            except Exception as e:
                logger.debug(f"Element fingerprint generation failed: {e}")
                continue
        
        if new_elements:
            logger.debug(f"Detected {len(new_elements)} new elements (total {len(current_elements)})")
        
        return new_elements
    
    async def _generate_element_fingerprint(self, page: Page, element: ElementHandle) -> Optional[str]:
        """Generate element fingerprint (**P2-A: new method**)

        Generate unique identifier based on element tag, id, class, position

        Args:
            page: Page object
            element: Element handle

        Returns:
            Fingerprint string, None on failure
        """
        try:
            fingerprint_data = await element.evaluate("""
                el => {
                    // Get tag name
                    const tag = el.tagName.toLowerCase();
                    
                    // Get id and class
                    const id = el.id || '';
                    const classes = Array.from(el.classList).sort().join('.');
                    
                    // Get position (to distinguish different instances of the same element)
                    const bounds = el.getBoundingClientRect();
                    const position = `${Math.round(bounds.x)},${Math.round(bounds.y)}`;
                    
                    // Get text content (truncated to avoid being too long)
                    const text = (el.textContent || '').trim().slice(0, 30);
                    
                    // Combine fingerprint
                    return `${tag}|${id}|${classes}|${position}|${text}`;
                }
            """)
            
            # Generate hash to shorten fingerprint length
            import hashlib
            return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.debug(f"Fingerprint generation failed: {e}")
            return None
    
    async def _submit_all_forms(self, page: Page, traffic_interceptor, base_url: str):
        """Proactively submit page forms - minimalist robust version

        Strategy:
        1. Only fill basic inputs (text/email) - avoid complex elements
        2. Skip select/radio/checkbox - prevent crashes
        3. Fail fast - all operations have timeouts
        4. Fault tolerance first - any error does not affect subsequent forms
        """
        try:
            # Smart wait for forms to appear
            try:
                await page.wait_for_selector('form', timeout=3000, state='attached')
            except:
                return  # No forms, return directly
            
            forms = await page.query_selector_all('form')
            if not forms:
                return
            
            logger.info(f"Detected {len(forms)} forms, starting processing")
            
            for idx, form in enumerate(forms):
                try:
                    # Quick fill - only handle safe input types
                    filled = await self._fill_form_safely(form, idx)
                    
                    if not filled:
                        logger.debug(f"Form {idx} has no fillable inputs, skipping")
                        continue
                    
                    # Attempt submission
                    success = await self._submit_form_safely(form, idx, traffic_interceptor)
                    
                    if success:
                        # Wait for network requests
                        await asyncio.sleep(1.5)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=2000)
                        except:
                            pass
                    
                except Exception as e:
                    logger.debug(f"Form {idx} processing failed (ignored): {e}")
                    continue  # Continue processing next form
            
        except Exception as e:
            logger.debug(f"Form submission processing error: {e}")
    
    async def _fill_form_safely(self, form, form_idx: int) -> bool:
        """Safely fill form - only handle basic input types

        Returns:
            bool: Whether at least one field was filled
        """
        try:
            # Only find safe input types
            inputs = await form.query_selector_all(
                'input[type="text"], input[type="email"], input[type="password"], '
                'input:not([type]), textarea'
            )
            
            if not inputs:
                logger.debug(f"Form {form_idx} has no fillable inputs")
                return False
            
            filled_count = 0
            filled_fields = []
            for input_elem in inputs[:5]:  # Limit to 5 fields max for speed
                try:
                    input_type = await input_elem.get_attribute('type') or 'text'
                    input_name = await input_elem.get_attribute('name') or 'input'
                    
                    # Check if visible and editable
                    is_visible = await input_elem.is_visible()
                    is_enabled = await input_elem.is_enabled()
                    
                    if not (is_visible and is_enabled):
                        continue
                    
                    # Quick fill
                    if input_type == 'email':
                        await input_elem.fill('test@xss.com', timeout=1000)
                    elif input_type == 'password':
                        await input_elem.fill('Pass123', timeout=1000)
                    else:
                        await input_elem.fill(f'test_{input_name}', timeout=1000)
                    
                    filled_count += 1
                    filled_fields.append(input_name)
                    
                except:
                    continue  # Ignore single input errors
            
            if filled_count > 0:
                logger.info(f"Form {form_idx} filled {filled_count} fields: {', '.join(filled_fields[:3])}")
            return filled_count > 0
            
        except:
            return False
    
    async def _submit_form_safely(self, form, form_idx: int, traffic_interceptor) -> bool:
        """Safely submit form

        Returns:
            bool: Whether submission was triggered successfully
        """
        try:
            # Update interceptor context
            traffic_interceptor.action_trigger = f"form_{form_idx}"
            
            # Find submit button
            logger.debug(f"Form {form_idx} finding submit button...")
            submit_btn = await form.query_selector(
                'button[type="submit"], input[type="submit"]'
            )
            
            if submit_btn:
                # Check if button is clickable
                is_visible = await submit_btn.is_visible()
                is_enabled = await submit_btn.is_enabled()
                logger.debug(f"Form {form_idx} button status: visible={is_visible}, enabled={is_enabled}")
                
                if is_visible and is_enabled:
                    logger.info(f"Form {form_idx} clicking submit button...")
                    await submit_btn.click(timeout=2000)
                    logger.info(f"Form {form_idx} submitted (button click)")
                    return True
                else:
                    logger.debug(f"Form {form_idx} button not clickable")
            else:
                logger.debug(f"Form {form_idx} submit button not found")
            
            # Fallback: attempt direct submit()
            logger.debug(f"Form {form_idx} attempting direct submit()...")
            try:
                await form.evaluate('f => f.submit()', timeout=1000)
                logger.info(f"Form {form_idx} submitted (direct submit)")
                return True
            except Exception as e2:
                logger.debug(f"Form {form_idx} direct submit failed: {e2}")
            
            logger.warning(f"Form {form_idx} unable to submit")
            return False
            
        except Exception as e:
            logger.warning(f"Form {form_idx} submission error: {e}")
            return False

    async def _trigger_search_inputs(self, page: Page, traffic_interceptor):
        """Proactively trigger search input interactions

        For standalone search inputs in navigation bars, etc.:
        1. Identify: type="search", placeholder="search", name="q", etc.
        2. Interact: enter keyword -> press Enter -> click search icon
        """
        try:
            # 1. Find potential search input fields
            # Note: "搜索" in the selector below is the Chinese word for "search" -
            # kept intentionally to match Chinese-language search inputs on target pages
            search_inputs = await page.query_selector_all(
                'input[type="search"], '
                'input[name*="search" i], input[name="q" i], '
                'input[placeholder*="search" i], input[placeholder*="搜索" i], '
                'input[aria-label*="search" i]'
            )
            
            if not search_inputs:
                return
            
            logger.info(f"Detected {len(search_inputs)} potential search inputs, starting interaction")
            
            for idx, input_el in enumerate(search_inputs):
                try:
                    if not await input_el.is_visible():
                        continue
                        
                    # Update interceptor context
                    traffic_interceptor.action_trigger = f"search_input_{idx}"
                    
                    # 1. Focus and input
                    await input_el.fill("XSS_SEARCH_TEST", timeout=1000)
                    
                    # 2. Simulate Enter key (most common search trigger)
                    logger.info(f"Search input {idx}: simulating Enter key submission")
                    await input_el.press("Enter", timeout=1000)
                    
                    # Wait for possible navigation or request
                    await asyncio.sleep(1)
                    
                    # 3. Try to find and click adjacent search button (if Enter has no effect)
                    # Search logic: nearby button or icon
                    # Simple attempt: if no navigation/request occurred, try clicking button within parent element

                    # Restore context (for subsequent operations)
                    traffic_interceptor.action_trigger = "page_load"
                    
                except Exception as e:
                    logger.debug(f"Search input {idx} interaction failed: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"Search input trigger logic error: {e}")

        """Proactively submit all forms on the page (**BUG FIX: actively trigger network requests**)

        Identify forms on the page, fill test data and submit to trigger POST requests for traffic interceptor capture
        Supports dynamic rendering of SPA frameworks like React/Vue/Angular

        Args:
            page: Playwright page object
            traffic_interceptor: Traffic interceptor instance
            base_url: Current page URL
        """
        try:
            # **Smart wait for SPA framework rendering (React/Vue/Angular/Svelte, etc.)**
            # Wait for form elements to appear, up to 3 seconds
            try:
                await page.wait_for_selector('form', timeout=3000, state='attached')
                logger.debug("Detected form elements rendered")
            except:
                logger.debug("No <form> tag detected (may not be a form page or uses custom submission)")
                return
            
            # Find all forms
            forms = await page.query_selector_all('form')
            
            if not forms:
                return
            
            logger.info(f"Found {len(forms)} forms, preparing to submit")
            
            for idx, form in enumerate(forms):
                try:
                    # Get form attributes
                    action = await form.get_attribute('action') or ''
                    method = (await form.get_attribute('method') or 'GET').upper()
                    
                    # Find all input elements in the form
                    inputs = await form.query_selector_all('input:not([type="hidden"]), textarea, select')
                    
                    if not inputs:
                        logger.debug(f"Form {idx} has no input elements, skipping")
                        continue
                    
                    # Fill form
                    filled_count = 0
                    for input_elem in inputs:
                        try:
                            input_type = await input_elem.get_attribute('type') or 'text'
                            input_name = await input_elem.get_attribute('name')
                            tag_name = await input_elem.evaluate('el => el.tagName.toLowerCase()')
                            
                            if not input_name:
                                continue
                            
                            # Fill test data based on type
                            if input_type in ['text', 'search', 'url']:
                                await input_elem.fill(f"XSS_Test_{input_name}")
                            elif input_type == 'email':
                                await input_elem.fill("xss@test.com")
                            elif input_type == 'tel':
                                await input_elem.fill("1234567890")
                            elif input_type == 'number':
                                await input_elem.fill("123")
                            elif input_type == 'password':
                                await input_elem.fill("TestPass123")
                            elif tag_name == 'textarea':
                                await input_elem.fill(f"XSS_Content_{input_name}")
                            elif tag_name == 'select':
                                # Select first non-empty option
                                try:
                                    await input_elem.select_option(index=1)
                                except:
                                    await input_elem.select_option(index=0)
                            else:
                                await input_elem.fill("test_value")
                            
                            filled_count += 1
                        except Exception as e:
                            logger.debug(f"Failed to fill input: {input_name} - {e}")
                            continue
                    
                    if filled_count == 0:
                        logger.debug(f"Form {idx} unable to fill any fields, skipping")
                        continue
                    
                    # Update traffic interceptor context
                    traffic_interceptor.action_trigger = f"form_submit_{idx}"
                    
                    # Find submit button
                    submit_btn = await form.query_selector('button[type="submit"], input[type="submit"], button:not([type="button"])')
                    
                    if submit_btn:
                        logger.info(f"Submit form {idx} (action={action}, method={method})")
                        try:
                            await submit_btn.click(timeout=3000)
                            logger.info(f"Form {idx} submit button click succeeded")
                        except Exception as e:
                            logger.warning(f"Form {idx} submission failed: {e}")
                            # Continue waiting, may have partial effect
                    else:
                        # No submit button found, attempting direct form submission
                        logger.info(f"Direct form submission {idx} (no submit button)")
                        try:
                            await form.evaluate("form => form.submit()")
                            logger.info(f"Form {idx} direct submission succeeded")
                        except Exception as e:
                            logger.warning(f"Form {idx} direct submission failed: {e}")
                            # Continue waiting
                    
                    # Wait for request to complete
                    await asyncio.sleep(2)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except:
                        pass  # Ignore timeout
                    
                except Exception as e:
                    logger.debug(f"Form {idx} submission failed: {e}")
                    continue
            
        except Exception as e:
            logger.debug(f"Form submission processing failed: {e}")
