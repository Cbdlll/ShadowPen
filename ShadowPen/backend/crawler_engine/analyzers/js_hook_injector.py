"""
JavaScript Hook 注入器

运行时拦截危险函数调用,发现基于 JS 的 XSS 漏洞
"""
from typing import List, Dict, Any
from playwright.async_api import Page
from ..models import AttackSurface, ParamType, SourceType
import logging
import re

logger = logging.getLogger(__name__)


# Hook 注入脚本
HOOK_SCRIPT = """
(function() {
    // 保存原始函数
    const original = {
        eval: window.eval,
        setTimeout: window.setTimeout,
        setInterval: window.setInterval,
        documentWrite: document.write,
        Function: window.Function
    };
    
    // 结果存储
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
    
    // Hook setTimeout (仅字符串形式)
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
    
    // Hook setInterval (仅字符串形式)
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
    
    // Hook Function 构造函数
    window.Function = function() {
        const args = Array.from(arguments);
        window.__xss_hook_results.push({
            function: 'Function',
            argument: args.join(', '),
            timestamp: Date.now()
        });
        return original.Function.apply(this, arguments);
    };
    
    // Hook 动态 script 创建
    const originalCreateElement = document.createElement;
    document.createElement = function(tagName) {
        const element = originalCreateElement.apply(this, arguments);
        
        if (tagName && tagName.toLowerCase() === 'script') {
            // Hook src 属性
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
            
            // Hook textContent 属性
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
    
    console.log('[XSS Hook] JavaScript Hook 已注入');
})();
"""


class JSHookInjector:
    """JavaScript Hook 注入器
    
    功能:
    - 在页面加载前注入 Hook 脚本
    - 拦截 eval, setTimeout, setInterval, document.write, Function
    - 拦截动态 script 标签创建
    - 提取参数引用,识别 XSS 风险
    """
    
    async def inject_hooks(self, page: Page):
        """在页面加载前注入 Hook
        
        Args:
            page: Playwright 页面对象
        """
        try:
            await page.add_init_script(HOOK_SCRIPT)
            logger.debug("JS Hook 脚本已注入")
        except Exception as e:
            logger.error(f"Hook 注入失败: {e}")
    
    async def collect_results(self, page: Page, current_url: str) -> List[AttackSurface]:
        """收集 Hook 结果并转换为攻击面
        
        Args:
            page: Playwright 页面对象
            current_url: 当前页面 URL
            
        Returns:
            攻击面列表
        """
        surfaces = []
        
        try:
            # 获取 Hook 结果
            results = await page.evaluate("() => window.__xss_hook_results || []")
            
            if not results:
                logger.debug("未捕获到危险函数调用")
                return surfaces
            
            logger.info(f"捕获到 {len(results)} 次危险函数调用")
            
            # 处理每个结果
            for result in results:
                func_name = result.get('function', 'unknown')
                argument = result.get('argument', '')
                
                # 提取参数引用
                params = self._extract_params_from_code(argument)
                
                if params:
                    # 发现参数引用,创建攻击面
                    for param in params:
                        surfaces.append(AttackSurface(
                            url=current_url,
                            method="GET",  # 通常是客户端处理
                            param_name=param,
                            param_type=ParamType.JS_DYNAMIC,
                            source=SourceType.JS_STATIC_ANALYSIS,
                            dangerous_function=func_name,
                            sample_payload=argument[:200],  # 截断以避免过长
                            element_type=func_name
                        ))
                else:
                    # 即使没有参数引用,也记录危险函数调用
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
            
            logger.info(f"JS Hook 分析完成,发现 {len(surfaces)} 个攻击面")
            
        except Exception as e:
            logger.error(f"Hook 结果收集失败: {e}")
        
        return surfaces
    
    def _extract_params_from_code(self, code: str) -> List[str]:
        """从 JS 代码中提取 URL 参数引用
        
        Args:
            code: JavaScript 代码字符串
            
        Returns:
            参数名列表
        """
        params = set()
        
        # 模式 1: URLSearchParams.get('param')
        pattern1 = r"\.get\(['\"](\w+)['\"]\)"
        params.update(re.findall(pattern1, code))
        
        # 模式 2: params.param 或 query.param
        pattern2 = r"(?:params|query|search)\.(\w+)"
        params.update(re.findall(pattern2, code))
        
        # 模式 3: query['param'] 或 query["param"]
        pattern3 = r"(?:params|query|search)\[['\"](\w+)['\"]\]"
        params.update(re.findall(pattern3, code))
        
        # 模式 4: location.search (通用)
        if 'location.search' in code or 'window.location.search' in code:
            params.add('_url_search_')
        
        # 模式 5: location.hash
        if 'location.hash' in code or 'window.location.hash' in code:
            params.add('_url_hash_')
        
        # 模式 6: document.URL
        if 'document.URL' in code or 'document.url' in code:
            params.add('_document_url_')
        
        return list(params)
    
    async def clear_results(self, page: Page):
        """清空 Hook 结果
        
        Args:
            page: Playwright 页面对象
        """
        try:
            await page.evaluate("() => { window.__xss_hook_results = []; }")
        except Exception as e:
            logger.debug(f"清空 Hook 结果失败: {e}")
