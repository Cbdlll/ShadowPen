async def _submit_all_forms(self, page: Page, traffic_interceptor, base_url: str):
    """Proactively submit all forms on the page (**BUG FIX: actively trigger network requests**)

    Args:
        page: Page object
        traffic_interceptor: Traffic interceptor
        base_url: Base URL
    """
    try:
        # Find all forms
        forms = await page.query_selector_all('form')
        
        if not forms:
            return
        
        logger.info(f"Found {len(forms)} forms, preparing to submit")
        
        for idx, form in enumerate(forms):
            try:
                # Get form action and method
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
                    input_type = await input_elem.get_attribute('type') or 'text'
                    input_name = await input_elem.get_attribute('name')
                    
                    if not input_name:
                        continue
                    
                    # Fill test data based on type
                    try:
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
                        elif input_elem.tag_name == 'textarea':
                            await input_elem.fill(f"XSS_Content_{input_name}")
                        elif input_elem.tag_name == 'select':
                            # Select first non-empty option
                            try:
                                await input_elem.select_option(index=1)
                            except:
                                await input_elem.select_option(index=0)
                        
                        filled_count += 1
                    except Exception as e:
                        logger.debug(f"Failed to fill input: {input_name} - {e}")
                
                if filled_count == 0:
                    continue
                
                # Update traffic interceptor context
                traffic_interceptor.action_trigger = f"form_submit_{idx}"
                
                # Find submit button
                submit_btn = await form.query_selector('button[type="submit"], input[type="submit"], button:not([type="button"])')
                
                if submit_btn:
                    logger.info(f"Submit form {idx} (action={action}, method={method})")
                    await submit_btn.click(timeout=3000)
                else:
                    # No submit button found, attempting direct form submission
                    await form.evaluate("form => form.submit()")
                    logger.info(f"Direct form submission {idx}")
                
                # Wait for request to complete
                await asyncio.sleep(2)
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass
                
            except Exception as e:
                logger.debug(f"Form {idx} submission failed: {e}")
                continue
        
    except Exception as e:
        logger.debug(f"Form submission processing failed: {e}")
