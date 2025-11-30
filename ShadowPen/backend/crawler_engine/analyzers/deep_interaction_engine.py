"""
深度交互引擎 (Depth=2 BFS 算法)

实现智能交互探索，发现隐藏在 Modal、Tab、Drawer 等动态组件中的输入点。
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
    """交互节点（BFS 队列元素）"""
    element_selector: str              # 元素选择器
    element_fingerprint: str           # 元素指纹（去重用）
    element_text: str                  # 元素文本
    depth: int                         # 当前深度 (0, 1, 2)
    trigger_chain: List[str]           # 触发链
    element_handle: Optional[ElementHandle] = None  # Playwright 元素句柄


class DeepInteractionEngine:
    """深度交互引擎
    
    核心算法：BFS 广度优先探索
    - Depth 0: 页面初始状态
    - Depth 1: 首次交互触发（如点击按钮）
    - Depth 2: 二次交互触发（如在弹窗中点击提交）
    """
    
    def __init__(
        self,
        max_depth: int = 2,
        max_actions: int = 50,
        interaction_timeout: int = 3000,
        wait_after_click: float = 0.5,
        global_dedup=None  # GlobalDeduplicationManager 实例
    ):
        """
        Args:
            max_depth: 最大交互深度
            max_actions: 单页面最大操作数（熔断）
            interaction_timeout: 单次交互超时（毫秒）
            wait_after_click: 点击后等待时间（秒）
            global_dedup: 全局去重管理器
        """
        self.max_depth = max_depth
        self.max_actions = max_actions
        self.interaction_timeout = interaction_timeout
        self.wait_after_click = wait_after_click
        self.global_dedup = global_dedup  # 全局去重器
        
        # 状态追踪（页面级去重，作为全局去重的补充）
        self._visited_fingerprints: Set[str] = set()
        self._known_element_fingerprints: Set[str] = set()  # **P2-A: 维护已知元素指纹**
        self._action_count = 0
        self._captured_surfaces: List[AttackSurface] = []
    
    async def explore_page(
        self,
        page: Page,
        traffic_interceptor,  # TrafficInterceptor 实例
        base_url: str
    ) -> List[AttackSurface]:
        """BFS 探索页面
        
        Args:
            page: Playwright 页面对象
            traffic_interceptor: 流量拦截器（用于同步深度信息）
            base_url: 基础 URL
            
        Returns:
            发现的攻击面列表
        """
        logger.info(f"开始深度交互探索（max_depth={self.max_depth}）")
        
        # 初始化队列
        queue: Deque[InteractionNode] = deque()
        
        # Depth 0: 扫描初始页面元素
        initial_elements = await self._find_interactive_elements(page)
        for elem in initial_elements:
            node = await self._create_interaction_node(page, elem, depth=0, trigger_chain=["page_load"])
            if node:
                queue.append(node)
        
        logger.info(f"初始化队列: {len(queue)} 个可交互元素")
        
        # BFS 遍历
        while queue and self._action_count < self.max_actions:
            node = queue.popleft()
            
            # 页面级去重检查（快速过滤）
            if node.element_fingerprint in self._visited_fingerprints:
                continue
            
            self._visited_fingerprints.add(node.element_fingerprint)
            
            # 全局去重检查（跨页面去重）
            if self.global_dedup and not await self._should_interact_with_element(page, node):
                logger.debug(f"全局去重跳过: {node.element_text[:30]}")
                continue
            
            # **BUG FIX: 主动提交页面上的所有表单**
            # 仅在初始深度(depth=0)时提交,避免重复
            # 3. 主动提交表单 (P1: 关键修复)
            current_url = page.url # 获取当前页面的URL
            await self._submit_all_forms(page, traffic_interceptor, current_url)
            
            # 4. 主动触发搜索框 (P2: 导航栏搜索优化)
            await self._trigger_search_inputs(page, traffic_interceptor)
            
            # 执行交互
            success = await self._perform_interaction(page, node, traffic_interceptor)
            self._action_count += 1
            
            if not success:
                continue
            
            # 等待 DOM 稳定
            await asyncio.sleep(0.2)
            
            # 如果未达深度限制，扫描新元素
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
            f"交互探索完成: 执行了 {self._action_count} 次操作, "
            f"访问了 {len(self._visited_fingerprints)} 个唯一元素"
        )
        
        # 合并流量拦截器捕获的结果
        all_surfaces = self._captured_surfaces + traffic_interceptor.get_captured_surfaces()
        return all_surfaces
    
    async def _find_interactive_elements(self, page: Page) -> List[ElementHandle]:
        """查找所有可交互元素 (**P2-B: 扩展版**)"""
        # **P2-B: 扩展选择器,包括事件触发器**
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
            # 过滤不可见元素
            visible_elements = []
            for elem in elements:
                is_visible = await elem.is_visible()
                if is_visible:
                    visible_elements.append(elem)
            return visible_elements
        except Exception as e:
            logger.debug(f"查找交互元素失败: {e}")
            return []
    
    async def _create_interaction_node(
        self,
        page: Page,
        element: ElementHandle,
        depth: int,
        trigger_chain: List[str]
    ) -> Optional[InteractionNode]:
        """创建交互节点"""
        try:
            # 获取元素信息
            text = await element.text_content() or ""
            text = text.strip()[:50]
            
            # 生成选择器
            selector = await element.evaluate("""
                el => {
                    if (el.id) return '#' + el.id;
                    const classes = Array.from(el.classList).join('.');
                    return el.tagName.toLowerCase() + (classes ? '.' + classes : '');
                }
            """)
            
            # 生成指纹
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
            logger.debug(f"创建交互节点失败: {e}")
            return None
    
    async def _should_interact_with_element(
        self,
        page: Page,
        node: InteractionNode
    ) -> bool:
        """判断是否应该与元素交互（全局去重检查）
        
        Returns:
            True 表示应该交互，False 表示跳过
        """
        if not self.global_dedup:
            return True
        
        try:
            # 1. 检查是否是链接
            tag_name = await node.element_handle.evaluate('el => el.tagName')
            if tag_name and tag_name.lower() == 'a':
                href = await node.element_handle.get_attribute('href')
                if href:
                    from urllib.parse import urljoin
                    absolute_url = urljoin(page.url, href)
                    if not self.global_dedup.should_visit_url(absolute_url):
                        return False
            
            # 2. 检查元素指纹（全局去重）
            if not self.global_dedup.should_click_element(
                element_text=node.element_text,
                element_selector=node.element_selector,
                page_url=page.url,
                is_navigation=None  # 自动判断
            ):
                return False
            
            return True
            
        except Exception as e:
            logger.debug(f"全局去重检查失败: {e}")
            return True  # 失败时允许交互
    
    async def _perform_interaction(
        self,
        page: Page,
        node: InteractionNode,
        traffic_interceptor
    ) -> bool:
        """执行交互 (**P2-B: 支持多种触发方式**)
        
        Returns:
            成功返回 True,失败返回 False
        """
        try:
            # 填表预处理
            await self._pre_fill_forms(page, node.element_handle)
            
            # 更新流量拦截器的深度和触发链
            traffic_interceptor.depth_level = node.depth
            traffic_interceptor.trigger_chain = node.trigger_chain
            traffic_interceptor.action_trigger = f"click_{node.element_text[:20]}"
            
            # **P2-B: 判断交互类型**
            elem = node.element_handle
            tag_name = await elem.evaluate("el => el.tagName.toLowerCase()")
            
            # 检查是否有特殊事件处理器
            has_onmouseover = await elem.evaluate("el => !!el.onmouseover")
            has_onchange = await elem.evaluate("el => !!el.onchange")
            
            if has_onmouseover:
                # 触发 mouseover 事件
                logger.debug(
                    f"[Depth {node.depth}] 触发 onmouseover: {node.element_selector} "
                    f"({node.element_text[:30]})"
                )
                await elem.hover(timeout=self.interaction_timeout)
            
            elif tag_name == 'select' or has_onchange:
                # 选择下拉框或触发 change 事件
                logger.debug(
                    f"[Depth {node.depth}] 触发 onchange: {node.element_selector}"
                )
                if tag_name == 'select':
                    # 选择第二个选项 (跳过默认值)
                    try:
                        await elem.select_option(index=1)
                    except:
                        await elem.select_option(index=0)
                else:
                    # 对于 input,修改值以触发 change
                    await elem.fill("XSS_Probe_Change")
            
            else:
                # 默认点击
                logger.debug(
                    f"[Depth {node.depth}] 点击元素: {node.element_selector} "
                    f"({node.element_text[:30]})"
                )
                await elem.click(timeout=self.interaction_timeout)
            
            # **BUG FIX: 增加等待时间,确保异步请求(如表单提交)完成**
            await asyncio.sleep(self.wait_after_click + 1.0)  # 额外增加 1 秒
            
            # 尝试等待网络空闲
            try:
                await page.wait_for_load_state("networkidle", timeout=3000)
            except:
                pass  # 忽略超时
            
            return True
            
        except PlaywrightTimeout:
            logger.debug(f"交互超时: {node.element_selector}")
            return False
        except Exception as e:
            logger.debug(f"交互失败: {e}")
            return False
    
    async def _pre_fill_forms(self, page: Page, element: ElementHandle):
        """填表预处理：自动填充附近的输入框"""
        try:
            # 查找附近的表单或全局输入框（包括 select）
            nearby_elements = await element.evaluate("""
                el => {
                    // 1. 尝试查找所属表单
                    const form = el.closest('form');
                    let elements = [];
                    
                    if (form) {
                        // 包括 input, textarea, select
                        elements = Array.from(form.querySelectorAll('input:not([type="submit"]):not([type="button"]), textarea, select'));
                    } else {
                        // 2. 如果没有表单（SPA 常见），查找页面上所有可见元素
                        elements = Array.from(document.querySelectorAll('input:not([type="submit"]):not([type="button"]), textarea, select'));
                        
                        // 过滤掉隐藏的
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
            
            # 填充表单
            for elem_info in nearby_elements:
                try:
                    selector = elem_info.get('selector')
                    if not selector and elem_info.get('className'):
                        # 尝试构建 class 选择器
                        classes = elem_info['className'].split()
                        if classes:
                            selector = '.' + '.'.join(classes)
                            
                    if not selector:
                        continue

                    form_elem = await page.query_selector(selector)
                    if not form_elem:
                        continue
                    
                    # 处理 select 元素
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
                    
                    # 处理 input 和 textarea
                    try:
                        # 检查是否已填充
                        value = await form_elem.input_value()
                        if value:
                            continue
                    except:
                        pass
                        
                    # 根据类型填充不同的值
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
                    
                    # 手动触发事件以兼容 React/Vue
                    await form_elem.evaluate("""el => {
                        el.dispatchEvent(new Event('input', { bubbles: true }));
                        el.dispatchEvent(new Event('change', { bubbles: true }));
                    }""")
                except Exception:
                    pass
                    
        except Exception as e:
            logger.debug(f"填表预处理失败: {e}")
    
    async def _detect_new_elements(self, page: Page) -> List[ElementHandle]:
        """检测新出现的元素 (**P2-A: 真实 DOM 差异对比**)
        
        对比交互前后的元素集合,仅返回新增元素
        """
        # 等待动画/渲染完成
        await asyncio.sleep(0.3)
        
        # 获取当前所有可交互元素
        current_elements = await self._find_interactive_elements(page)
        
        # 提取新元素
        new_elements = []
        
        for elem in current_elements:
            try:
                # 生成元素指纹
                fingerprint = await self._generate_element_fingerprint(page, elem)
                
                if not fingerprint:
                    continue
                
                # 检查是否为新元素
                if fingerprint not in self._known_element_fingerprints:
                    new_elements.append(elem)
                    self._known_element_fingerprints.add(fingerprint)
                    
            except Exception as e:
                logger.debug(f"元素指纹生成失败: {e}")
                continue
        
        if new_elements:
            logger.debug(f"检测到 {len(new_elements)} 个新元素（总共 {len(current_elements)}）")
        
        return new_elements
    
    async def _generate_element_fingerprint(self, page: Page, element: ElementHandle) -> Optional[str]:
        """生成元素指纹 (**P2-A: 新增方法**)
        
        基于元素的标签、id、class、位置生成唯一标识
        
        Args:
            page: 页面对象
            element: 元素句柄
            
        Returns:
            指纹字符串,失败返回 None
        """
        try:
            fingerprint_data = await element.evaluate("""
                el => {
                    // 获取标签名
                    const tag = el.tagName.toLowerCase();
                    
                    // 获取 id 和 class
                    const id = el.id || '';
                    const classes = Array.from(el.classList).sort().join('.');
                    
                    // 获取位置 (用于区分相同元素的不同实例)
                    const bounds = el.getBoundingClientRect();
                    const position = `${Math.round(bounds.x)},${Math.round(bounds.y)}`;
                    
                    // 获取文本内容 (截断,避免过长)
                    const text = (el.textContent || '').trim().slice(0, 30);
                    
                    // 组合指纹
                    return `${tag}|${id}|${classes}|${position}|${text}`;
                }
            """)
            
            # 生成 hash 以缩短指纹长度
            import hashlib
            return hashlib.md5(fingerprint_data.encode()).hexdigest()[:16]
            
        except Exception as e:
            logger.debug(f"指纹生成失败: {e}")
            return None
    
    async def _submit_all_forms(self, page: Page, traffic_interceptor, base_url: str):
        """主动提交页面表单 - 极简健壮版本
        
        策略:
        1. 仅填充基本输入(text/email) - 避免复杂元素
        2. 跳过select/radio/checkbox - 防止崩溃
        3. 快速失败 - 所有操作都有超时
        4. 容错优先 - 任何错误都不影响后续表单
        """
        try:
            # 智能等待表单出现
            try:
                await page.wait_for_selector('form', timeout=3000, state='attached')
            except:
                return  # 无表单,直接返回
            
            forms = await page.query_selector_all('form')
            if not forms:
                return
            
            logger.info(f"检测到 {len(forms)} 个表单,开始处理")
            
            for idx, form in enumerate(forms):
                try:
                    # 快速填充 - 仅处理安全的输入类型
                    filled = await self._fill_form_safely(form, idx)
                    
                    if not filled:
                        logger.debug(f"表单{idx}无可填充输入,跳过")
                        continue
                    
                    # 尝试提交
                    success = await self._submit_form_safely(form, idx, traffic_interceptor)
                    
                    if success:
                        # 等待网络请求
                        await asyncio.sleep(1.5)
                        try:
                            await page.wait_for_load_state("networkidle", timeout=2000)
                        except:
                            pass
                    
                except Exception as e:
                    logger.debug(f"表单{idx}处理失败(已忽略): {e}")
                    continue  # 继续处理下一个表单
            
        except Exception as e:
            logger.debug(f"表单提交处理异常: {e}")
    
    async def _fill_form_safely(self, form, form_idx: int) -> bool:
        """安全填充表单 - 仅处理基本输入类型
        
        Returns:
            bool: 是否成功填充了至少一个字段
        """
        try:
            # 仅查找安全的输入类型
            inputs = await form.query_selector_all(
                'input[type="text"], input[type="email"], input[type="password"], '
                'input:not([type]), textarea'
            )
            
            if not inputs:
                logger.debug(f"表单{form_idx}无可填充输入")
                return False
            
            filled_count = 0
            filled_fields = []
            for input_elem in inputs[:5]:  # 限制最多填充5个,加快速度
                try:
                    input_type = await input_elem.get_attribute('type') or 'text'
                    input_name = await input_elem.get_attribute('name') or 'input'
                    
                    # 检查是否可见且可编辑
                    is_visible = await input_elem.is_visible()
                    is_enabled = await input_elem.is_enabled()
                    
                    if not (is_visible and is_enabled):
                        continue
                    
                    # 快速填充
                    if input_type == 'email':
                        await input_elem.fill('test@xss.com', timeout=1000)
                    elif input_type == 'password':
                        await input_elem.fill('Pass123', timeout=1000)
                    else:
                        await input_elem.fill(f'test_{input_name}', timeout=1000)
                    
                    filled_count += 1
                    filled_fields.append(input_name)
                    
                except:
                    continue  # 忽略单个输入的错误
            
            if filled_count > 0:
                logger.info(f"表单{form_idx}已填充{filled_count}个字段: {', '.join(filled_fields[:3])}")
            return filled_count > 0
            
        except:
            return False
    
    async def _submit_form_safely(self, form, form_idx: int, traffic_interceptor) -> bool:
        """安全提交表单
        
        Returns:
            bool: 是否成功触发提交
        """
        try:
            # 更新拦截器上下文
            traffic_interceptor.action_trigger = f"form_{form_idx}"
            
            # 查找提交按钮
            logger.debug(f"表单{form_idx}查找提交按钮...")
            submit_btn = await form.query_selector(
                'button[type="submit"], input[type="submit"]'
            )
            
            if submit_btn:
                # 检查按钮是否可点击
                is_visible = await submit_btn.is_visible()
                is_enabled = await submit_btn.is_enabled()
                logger.debug(f"表单{form_idx}按钮状态: visible={is_visible}, enabled={is_enabled}")
                
                if is_visible and is_enabled:
                    logger.info(f"表单{form_idx}点击提交按钮...")
                    await submit_btn.click(timeout=2000)
                    logger.info(f"✓ 表单{form_idx}已提交(按钮点击)")
                    return True
                else:
                    logger.debug(f"表单{form_idx}按钮不可点击")
            else:
                logger.debug(f"表单{form_idx}未找到提交按钮")
            
            # 降级: 尝试直接submit
            logger.debug(f"表单{form_idx}尝试直接submit()...")
            try:
                await form.evaluate('f => f.submit()', timeout=1000)
                logger.info(f"✓ 表单{form_idx}已提交(直接submit)")
                return True
            except Exception as e2:
                logger.debug(f"表单{form_idx}直接submit失败: {e2}")
            
            logger.warning(f"表单{form_idx}无法提交")
            return False
            
        except Exception as e:
            logger.warning(f"表单{form_idx}提交异常: {e}")
            return False

    async def _trigger_search_inputs(self, page: Page, traffic_interceptor):
        """主动触发搜索框交互
        
        针对导航栏等位置的独立搜索框:
        1. 识别: type="search", placeholder="search", name="q" 等
        2. 交互: 输入关键词 -> 回车 -> 点击搜索图标
        """
        try:
            # 1. 查找潜在的搜索输入框
            search_inputs = await page.query_selector_all(
                'input[type="search"], '
                'input[name*="search" i], input[name="q" i], '
                'input[placeholder*="search" i], input[placeholder*="搜索" i], '
                'input[aria-label*="search" i]'
            )
            
            if not search_inputs:
                return
            
            logger.info(f"检测到 {len(search_inputs)} 个潜在搜索框,开始尝试交互")
            
            for idx, input_el in enumerate(search_inputs):
                try:
                    if not await input_el.is_visible():
                        continue
                        
                    # 更新拦截器上下文
                    traffic_interceptor.action_trigger = f"search_input_{idx}"
                    
                    # 1. 聚焦并输入
                    await input_el.fill("XSS_SEARCH_TEST", timeout=1000)
                    
                    # 2. 模拟回车 (最常见的搜索触发方式)
                    logger.info(f"搜索框{idx}: 模拟回车键提交")
                    await input_el.press("Enter", timeout=1000)
                    
                    # 等待可能的导航或请求
                    await asyncio.sleep(1)
                    
                    # 3. 尝试查找并点击相邻的搜索按钮 (如果回车没反应)
                    # 查找逻辑: 附近的 button 或 icon
                    # 这里简单尝试: 如果页面没有发生导航/请求,尝试点击父元素内的 button
                    
                    # 恢复上下文 (以便后续操作)
                    traffic_interceptor.action_trigger = "page_load"
                    
                except Exception as e:
                    logger.debug(f"搜索框{idx}交互失败: {e}")
                    continue
                    
        except Exception as e:
            logger.debug(f"搜索框触发逻辑异常: {e}")

        """主动提交页面上的所有表单 (**BUG FIX: 主动触发网络请求**)
        
        识别页面上的表单,填充测试数据并提交,以触发POST请求供流量拦截器捕获
        支持React/Vue/Angular等SPA框架的动态渲染
        
        Args:
            page: Playwright页面对象
            traffic_interceptor: 流量拦截器实例
            base_url: 当前页面URL
        """
        try:
            # **智能等待 SPA 框架渲染 (React/Vue/Angular/Svelte等)**
            # 等待form元素出现,最多3秒
            try:
                await page.wait_for_selector('form', timeout=3000, state='attached')
                logger.debug("检测到表单元素已渲染")
            except:
                logger.debug("未检测到<form>标签 (可能不是表单页面或使用自定义提交)")
                return
            
            # 查找所有表单
            forms = await page.query_selector_all('form')
            
            if not forms:
                return
            
            logger.info(f"发现 {len(forms)} 个表单,准备主动提交")
            
            for idx, form in enumerate(forms):
                try:
                    # 获取表单属性
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
                        try:
                            input_type = await input_elem.get_attribute('type') or 'text'
                            input_name = await input_elem.get_attribute('name')
                            tag_name = await input_elem.evaluate('el => el.tagName.toLowerCase()')
                            
                            if not input_name:
                                continue
                            
                            # 根据类型填充测试数据
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
                                # 选择第一个非空选项
                                try:
                                    await input_elem.select_option(index=1)
                                except:
                                    await input_elem.select_option(index=0)
                            else:
                                await input_elem.fill("test_value")
                            
                            filled_count += 1
                        except Exception as e:
                            logger.debug(f"填充输入框失败: {input_name} - {e}")
                            continue
                    
                    if filled_count == 0:
                        logger.debug(f"表单 {idx} 无法填充任何字段,跳过")
                        continue
                    
                    # 更新流量拦截器上下文
                    traffic_interceptor.action_trigger = f"form_submit_{idx}"
                    
                    # 查找提交按钮
                    submit_btn = await form.query_selector('button[type="submit"], input[type="submit"], button:not([type="button"])')
                    
                    if submit_btn:
                        logger.info(f"提交表单 {idx} (action={action}, method={method})")
                        try:
                            await submit_btn.click(timeout=3000)
                            logger.info(f"✓ 表单 {idx} 提交按钮点击成功")
                        except Exception as e:
                            logger.warning(f"表单 {idx} 提交失败: {e}")
                            # 继续等待,可能有部分效果
                    else:
                        # 没有提交按钮,尝试直接提交表单
                        logger.info(f"直接提交表单 {idx} (无提交按钮)")
                        try:
                            await form.evaluate("form => form.submit()")
                            logger.info(f"✓ 表单 {idx} 直接提交成功")
                        except Exception as e:
                            logger.warning(f"表单 {idx} 直接提交失败: {e}")
                            # 继续等待
                    
                    # 等待请求完成
                    await asyncio.sleep(2)
                    try:
                        await page.wait_for_load_state("networkidle", timeout=3000)
                    except:
                        pass  # 忽略超时
                    
                except Exception as e:
                    logger.debug(f"表单 {idx} 提交失败: {e}")
                    continue
            
        except Exception as e:
            logger.debug(f"表单提交处理失败: {e}")
