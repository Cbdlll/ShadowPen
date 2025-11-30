"""
DOM 分析器模块

深度分析页面 DOM 结构，提取所有可能的输入点
"""
from typing import List, Optional
from playwright.async_api import Page
from ..models import AttackSurface, ParamType, SourceType
from ..utils.exceptions import CrawlerException
import logging

logger = logging.getLogger(__name__)


class DOMAnalyzer:
    """DOM 静态分析器
    
    功能:
    - 提取表单输入元素
    - 识别隐藏输入字段
    - 识别 contenteditable 元素
    - 穿透 Shadow DOM
    """
    
    async def analyze_page(self, page: Page, current_url: str) -> List[AttackSurface]:
        """分析页面 DOM，提取攻击面
        
        Args:
            page: Playwright 页面对象
            current_url: 当前页面 URL
            
        Returns:
            攻击面列表
        """
        surfaces = []
        
        try:
            # 1. 提取标准表单输入
            surfaces.extend(await self._extract_form_inputs(page, current_url))
            
            # 2. 提取隐藏输入
            surfaces.extend(await self._extract_hidden_inputs(page, current_url))
            
            # 3. 提取 contenteditable 元素
            surfaces.extend(await self._extract_contenteditable(page, current_url))
            
            # 4. 穿透 Shadow DOM
            surfaces.extend(await self._extract_shadow_dom_inputs(page, current_url))
            
        except Exception as e:
            logger.error(f"DOM 分析失败: {e}")
            raise CrawlerException(f"DOM analysis failed: {e}")
        
        logger.info(f"DOM 分析完成，发现 {len(surfaces)} 个攻击面")
        return surfaces
    
    async def _extract_form_inputs(self, page: Page, current_url: str) -> List[AttackSurface]:
        """提取表单输入元素"""
        surfaces = []
        
        # 查找所有输入元素（排除 hidden）
        input_selectors = [
            'input:not([type="hidden"]):not([type="submit"]):not([type="button"])',
            'textarea',
            'select',
        ]
        
        for selector in input_selectors:
            try:
                elements = await page.query_selector_all(selector)
                
                for element in elements:
                    # 获取元素属性
                    name = await element.get_attribute('name')
                    elem_id = await element.get_attribute('id')
                    elem_type = await element.get_attribute('type') or selector.split('[')[0]
                    
                    # 参数名优先使用 name，其次 id
                    param_name = name or elem_id
                    
                    # 跳过没有 name 或 id 的输入框
                    # 除非它是明显的搜索框
                    if not param_name:
                        is_search = False
                        # 检查是否具有搜索特征
                        try:
                            placeholder = await element.get_attribute('placeholder') or ''
                            aria_label = await element.get_attribute('aria-label') or ''
                            title = await element.get_attribute('title') or ''
                            class_attr = await element.get_attribute('class') or ''
                            
                            # 综合判断
                            search_indicators = [placeholder, aria_label, title, class_attr, elem_type]
                            if any('search' in s.lower() or '搜索' in s for s in search_indicators):
                                is_search = True
                                # 尝试从属性中提取更有意义的名称
                                for attr in [placeholder, aria_label, title]:
                                    if attr:
                                        # 清理字符串: 转小写, 替换非字母数字为下划线
                                        import re
                                        clean_name = re.sub(r'[^a-zA-Z0-9]', '_', attr).strip('_').lower()
                                        if clean_name:
                                            param_name = clean_name
                                            break
                                
                                # 兜底名称
                                if not param_name:
                                    param_name = "search_input"
                        except:
                            pass
                            
                        if not is_search:
                            continue
                    
                    # 判断所属表单的方法
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
                logger.debug(f"提取 {selector} 失败: {e}")
                continue
        
        return surfaces
    
    async def _extract_hidden_inputs(self, page: Page, current_url: str) -> List[AttackSurface]:
        """提取隐藏输入字段"""
        surfaces = []
        
        try:
            hidden_inputs = await page.query_selector_all('input[type="hidden"]')
            
            for element in hidden_inputs:
                name = await element.get_attribute('name')
                if not name:
                    continue
                
                # 获取表单信息
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
            logger.debug(f"提取隐藏输入失败: {e}")
        
        return surfaces
    
    async def _extract_contenteditable(self, page: Page, current_url: str) -> List[AttackSurface]:
        """提取 contenteditable 元素"""
        surfaces = []
        
        try:
            elements = await page.query_selector_all('[contenteditable="true"]')
            
            for idx, element in enumerate(elements):
                elem_id = await element.get_attribute('id')
                param_name = elem_id or f"contenteditable_{idx}"
                
                surfaces.append(AttackSurface(
                    url=current_url,
                    method="POST",  # 假设富文本通常通过 POST 提交
                    param_name=param_name,
                    param_type=ParamType.CONTENTEDITABLE,
                    source=SourceType.DOM_STATIC,
                    element_selector='[contenteditable="true"]',
                    element_type="contenteditable",
                ))
                
        except Exception as e:
            logger.debug(f"提取 contenteditable 失败: {e}")
        
        return surfaces
    
    async def _extract_shadow_dom_inputs(self, page: Page, current_url: str) -> List[AttackSurface]:
        """穿透 Shadow DOM 提取输入"""
        surfaces = []
        
        try:
            # 执行 JS 脚本穿透 Shadow DOM
            shadow_inputs = await page.evaluate("""
                () => {
                    const inputs = [];
                    
                    function traverseShadow(root) {
                        // 查找所有输入元素
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
                        
                        // 递归遍历 Shadow Root
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
            logger.debug(f"Shadow DOM 穿透失败: {e}")
        
        return surfaces
