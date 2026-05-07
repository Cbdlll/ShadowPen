"""
XSS Payload Validator

Used to verify whether an XSS payload is effective
"""
import asyncio
from typing import Dict, Any
import httpx
from playwright.async_api import async_playwright


async def verify_payload(target_url: str, payload: str) -> Dict[str, Any]:
    """
    Verify whether an XSS payload is effective

    Args:
        target_url: Target URL
        payload: XSS Payload

    Returns:
        Verification result dictionary
    """
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            
            # Detect alert dialogs
            alert_triggered = False
            
            def handle_dialog(dialog):
                nonlocal alert_triggered
                alert_triggered = True
                asyncio.create_task(dialog.dismiss())
            
            page.on("dialog", handle_dialog)
            
            try:
                # Try to inject payload
                test_url = f"{target_url}?test={payload}"
                await page.goto(test_url, timeout=10000, wait_until="networkidle")
                
                # Wait to see if it triggers
                await asyncio.sleep(1)
                
                if alert_triggered:
                    return {
                        "success": True,
                        "message": f"XSS vulnerability confirmed! Payload: {payload}",
                        "payload": payload,
                        "url": test_url
                    }
                else:
                    return {
                        "success": False,
                        "message": f"Payload did not trigger XSS",
                        "payload": payload
                    }
                    
            except Exception as e:
                return {
                    "success": False,
                    "message": f"Verification failed: {str(e)}",
                    "payload": payload
                }
            finally:
                await browser.close()
                
    except Exception as e:
        return {
            "success": False,
            "message": f"Browser launch failed: {str(e)}",
            "payload": payload
        }
