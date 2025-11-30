"""
XSS Payload 验证器

用于验证 XSS Payload 是否有效
"""
import asyncio
from typing import Dict, Any
import httpx
from playwright.async_api import async_playwright


async def verify_payload(target_url: str, payload: str) -> Dict[str, Any]:
    """
    验证 XSS Payload 是否有效
    
    Args:
        target_url: 目标 URL
        payload: XSS Payload
        
    Returns:
        验证结果字典
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # 检测 alert 弹窗
            alert_triggered = False
            
            def handle_dialog(dialog):
                nonlocal alert_triggered
                alert_triggered = True
                asyncio.create_task(dialog.dismiss())
            
            page.on("dialog", handle_dialog)
            
            try:
                # 尝试注入 payload
                test_url = f"{target_url}?test={payload}"
                await page.goto(test_url, timeout=10000, wait_until="networkidle")
                
                # 等待一下，看是否触发
                await asyncio.sleep(1)
                
                if alert_triggered:
                    return {
                        "success": True,
                        "message": f"XSS 漏洞确认！Payload: {payload}",
                        "payload": payload,
                        "url": test_url
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Payload 未触发 XSS",
                        "payload": payload
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "message": f"验证失败: {str(e)}",
                    "payload": payload
                }
            finally:
                await browser.close()
                
    except Exception as e:
        return {
            "success": False,
            "message": f"浏览器启动失败: {str(e)}",
            "payload": payload
        }
