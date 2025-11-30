async def _submit_all_forms(self, page: Page, traffic_interceptor, base_url: str):
    """主动提交页面上的所有表单 (**BUG FIX: 主动触发网络请求**)
    
    Args:
        page: 页面对象
        traffic_interceptor: 流量拦截器
        base_url: 基础URL
    """
    try:
        # 查找所有表单
        forms = await page.query_selector_all('form')
        
        if not forms:
            return
        
        logger.info(f"发现 {len(forms)} 个表单,准备主动提交")
        
        for idx, form in enumerate(forms):
            try:
                # 获取表单的 action 和 method
                action = await form.get_attribute('action') or ''
                method = (await form.get_attribute('method') or 'GET').upper()
                
                # 查找表单内的所有输入元素
                inputs = await form.query_selector_all('input:not([type="hidden"]), textarea, select')
                
                if not inputs:
                    logger.debug(f"表单 {idx} 无输入元素,跳过")
                    continue
                
                # 填充表单
                filled_count = 0
                for input_elem in inputs:
                    input_type = await input_elem.get_attribute('type') or 'text'
                    input_name = await input_elem.get_attribute('name')
                    
                    if not input_name:
                        continue
                    
                    # 根据类型填充测试数据
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
                            # 选择第一个非空选项
                            try:
                                await input_elem.select_option(index=1)
                            except:
                                await input_elem.select_option(index=0)
                        
                        filled_count += 1
                    except Exception as e:
                        logger.debug(f"填充输入框失败: {input_name} - {e}")
                
                if filled_count == 0:
                    continue
                
                # 更新流量拦截器上下文
                traffic_interceptor.action_trigger = f"form_submit_{idx}"
                
                # 查找提交按钮
                submit_btn = await form.query_selector('button[type="submit"], input[type="submit"], button:not([type="button"])')
                
                if submit_btn:
                    logger.info(f"提交表单 {idx} (action={action}, method={method})")
                    await submit_btn.click(timeout=3000)
                else:
                    # 没有提交按钮,尝试直接提交表单
                    await form.evaluate("form => form.submit()")
                    logger.info(f"直接提交表单 {idx}")
                
                # 等待请求完成
                await asyncio.sleep(2)
                try:
                    await page.wait_for_load_state("networkidle", timeout=3000)
                except:
                    pass
                
            except Exception as e:
                logger.debug(f"表单 {idx} 提交失败: {e}")
                continue
        
    except Exception as e:
        logger.debug(f"表单提交处理失败: {e}")
