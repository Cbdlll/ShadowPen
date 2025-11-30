"""
交互引擎模块

主动触发页面交互，捕获隐藏的 API 请求
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
    """交互触发引擎
    
    功能:
    - 自动填充并提交表单
    - 点击可交互元素
    - 等待网络请求完成
    """
    
    def __init__(self, fill_timeout: int = 2000, click_timeout: int = 3000):
        self.fill_timeout = fill_timeout
        self.click_timeout = click_timeout
    
    async def trigger_interactions(
        self,
        page: Page,
        interceptor: TrafficInterceptor
    ) -> List[AttackSurface]:
        """触发页面交互
        
        Args:
            page: Playwright 页面对象
            interceptor: 流量拦截器（用于捕获交互产生的请求）
            
        Returns:
            交互后发现的攻击面列表
        """
        surfaces = []
        
        # 记录初始捕获数量
        initial_count = len(interceptor.get_captured_surfaces())
        
        # 1. 自动填充并提交表单
        await self._fill_and_submit_forms(page)
        
        # 2. 点击可交互元素
        await self._click_interactive_elements(page)
        
        # 3. 等待网络请求完成
        await asyncio.sleep(1)  # 给请求一些时间完成
        
        # 4. 获取交互后捕获的攻击面
        all_surfaces = interceptor.get_captured_surfaces()
        new_surfaces = all_surfaces[initial_count:]
        
        # 标记来源为交互后流量
        for surface in new_surfaces:
            surface.source = SourceType.TRAFFIC_INTERCEPT_AFTER_INTERACTION
            surfaces.append(surface)
        
        logger.info(f"交互触发完成，新增 {len(surfaces)} 个攻击面")
        return surfaces
    
    async def _fill_and_submit_forms(self, page: Page):
        """自动填充并提交表单"""
        try:
            # 查找所有表单
            forms = await page.query_selector_all('form')
            
            for form in forms:
                try:
                    # 填充表单字段
                    await self._fill_form(page, form)
                    
                    # 查找提交按钮
                    submit_btn = await form.query_selector(
                        'button[type="submit"], input[type="submit"]'
                    )
                    
                    if submit_btn:
                        # 点击提交按钮
                        await submit_btn.click(timeout=self.click_timeout)
                        # 等待可能的导航或请求
                        await asyncio.sleep(0.5)
                    else:
                        # 尝试直接提交表单
                        await form.evaluate('form => form.submit()')
                        await asyncio.sleep(0.5)
                        
                except PlaywrightTimeout:
                    logger.debug("表单提交超时")
                except Exception as e:
                    logger.debug(f"表单处理失败: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"表单填充失败: {e}")
    
    async def _fill_form(self, page: Page, form):
        """填充单个表单"""
        # 查找表单内的输入字段
        inputs = await form.query_selector_all(
            'input:not([type="submit"]):not([type="button"]):not([type="hidden"]), textarea'
        )
        
        for input_elem in inputs:
            try:
                input_type = await input_elem.get_attribute('type') or 'text'
                
                # 根据类型填充测试数据
                test_value = self._get_test_value(input_type)
                
                await input_elem.fill(test_value, timeout=self.fill_timeout)
                
            except PlaywrightTimeout:
                continue
            except Exception as e:
                logger.debug(f"输入填充失败: {e}")
                continue
    
    def _get_test_value(self, input_type: str) -> str:
        """获取测试填充值"""
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
        """点击可交互元素"""
        # 可交互元素选择器
        selectors = [
            'button:not([type="submit"])',  # 非提交按钮
            'a[href="#"]',                   # 锚点链接（可能触发 JS）
            '[onclick]',                     # 带 onClick 事件的元素
        ]
        
        for selector in selectors:
            try:
                elements = await page.query_selector_all(selector)
                
                # 限制点击数量，避免过度交互
                for element in elements[:5]:  # 每种类型最多点击 5 个
                    try:
                        # 检查元素是否可见
                        is_visible = await element.is_visible()
                        if not is_visible:
                            continue
                        
                        # 点击元素
                        await element.click(timeout=self.click_timeout)
                        
                        # 短暂等待
                        await asyncio.sleep(0.3)
                        
                    except PlaywrightTimeout:
                        continue
                    except Exception as e:
                        logger.debug(f"元素点击失败: {e}")
                        continue
                        
            except Exception as e:
                logger.debug(f"交互元素查找失败: {e}")
                continue
