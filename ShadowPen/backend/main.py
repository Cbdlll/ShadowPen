from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import asyncio
import uuid
from scanner import verify_payload
from llm import generate_mutations

app = FastAPI()

# 内存存储
VULNERABILITY_QUEUE = []
CONNECTED_CLIENTS: List[WebSocket] = []

class VerifyRequest(BaseModel):
    target_url: str
    payload: str

async def broadcast_log(message: str, type: str = "info"):
    """
    广播日志到所有连接的客户端
    """
    log_entry = {
        "type": "log",
        "data": {
            "message": message,
            "level": type,
            "timestamp": str(uuid.uuid4()) # 简单起见用 UUID 或时间戳
        }
    }
    for client in CONNECTED_CLIENTS:
        try:
            await client.send_json(log_entry)
        except:
            pass

async def shadow_loop(target_url: str, original_payload: str):
    """
    影子循环：变异并验证
    """
    await broadcast_log(f"Starting Shadow Mode for: {target_url}", "info")
    
    # 1. 调用 LLM 生成变异体
    await broadcast_log(f"Requesting LLM mutations for payload: {original_payload}...", "info")
    mutations = await generate_mutations(original_payload)
    
    if not mutations:
        await broadcast_log("LLM failed to generate mutations or returned empty list.", "error")
        return

    await broadcast_log(f"LLM Generated {len(mutations)} mutations: {mutations}", "success")

    # 2. 并行验证变异体
    tasks = []
    for m in mutations:
        await broadcast_log(f"Queuing verification for mutation: {m}", "info")
        # Notify frontend about specific activity
        for client in CONNECTED_CLIENTS:
            try:
                await client.send_json({
                    "type": "shadow_activity",
                    "data": {
                        "target_url": target_url,
                        "payload": m
                    }
                })
            except:
                pass
        tasks.append(verify_payload(target_url, m))
    
    results = await asyncio.gather(*tasks)
    
    # 3. 处理结果
    found_any = False
    for mutation, result in zip(mutations, results):
        if result["success"]:
            found_any = True
            vuln_data = {
                "id": str(uuid.uuid4()),
                "target_url": target_url,
                "payload": mutation,
                "message": result["message"]
            }
            VULNERABILITY_QUEUE.append(vuln_data)
            await broadcast_log(f"VULNERABILITY CONFIRMED: {mutation}", "danger")
            
            # 4. 实时通知前端
            for client in CONNECTED_CLIENTS:
                try:
                    await client.send_json({"type": "vuln_found", "data": vuln_data})
                except:
                    pass
        else:
            await broadcast_log(f"Verification failed for: {mutation}", "warning")
            
    if not found_any:
        await broadcast_log("Shadow cycle completed. No vulnerabilities found in this batch.", "info")

@app.get("/api/llm-status")
async def check_llm_status():
    """
    检查 LLM 环境变量配置状态
    """
    from llm import BASE_URL, API_KEY, MODEL
    is_configured = all([BASE_URL, API_KEY, MODEL])
    return {
        "configured": is_configured,
        "model": MODEL if is_configured else None,
        "base_url": BASE_URL if is_configured else None
    }

@app.post("/api/verify")
async def verify_endpoint(req: VerifyRequest, background_tasks: BackgroundTasks):
    # 主循环：同步验证
    result = await verify_payload(req.target_url, req.payload)
    
    # 如果失败，触发影子循环
    if not result["success"]:
        background_tasks.add_task(shadow_loop, req.target_url, req.payload)
        
    return result


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 10

@app.post("/api/crawl")
async def crawl_endpoint(req: CrawlRequest):
    """爬虫功能 - 使用完整的 XSSScanner"""
    try:
        from crawler import XSSScanner, ScannerConfig
        import json
        
        # 配置扫描器
        config = ScannerConfig(
            MAX_DEPTH=2,
            MAX_ACTIONS_PER_PAGE=50,
            MAX_URLS=req.max_pages,
            CONCURRENT_PAGES=3
        )
        
        scanner = XSSScanner(config)
        
        # 执行扫描
        result_file = await scanner.scan(req.url)
        
        # 读取结果文件
        with open(result_file, 'r', encoding='utf-8') as f:
            surfaces = json.load(f)
        
        return {
            "success": True,
            "surfaces": surfaces,
            "total_count": len(surfaces)
        }
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return {
            "success": False,
            "error": str(e),
            "surfaces": []
        }

class AnalyzeSurfacesRequest(BaseModel):
    surfaces: List[dict]

@app.post("/api/analyze-surfaces")
async def analyze_surfaces_endpoint(req: AnalyzeSurfacesRequest):
    """
    LLM 分析攻击面 - SSE 流式输出
    """
    from fastapi.responses import StreamingResponse
    from attack_surface_analyzer import analyze_attack_surfaces
    import json
    
    # 检查 LLM 配置
    from llm import BASE_URL, API_KEY, MODEL
    if not all([BASE_URL, API_KEY, MODEL]):
        return {"error": "LLM not configured"}
    
    async def generate_stream():
        """生成 SSE 流"""
        try:
            async for chunk in analyze_attack_surfaces(req.surfaces):
                yield f"data: {json.dumps(chunk, ensure_ascii=False)}\n\n"
                
        except Exception as e:
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)}, ensure_ascii=False)}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )


class ChatMessage(BaseModel):
    role: str  # 'user' or 'assistant'
    content: str
    thinking: str = ""  # Optional thinking field

class ChatRequest(BaseModel):
    message: str
    history: List[ChatMessage] = []

@app.post("/api/chat")
async def chat_endpoint(req: ChatRequest):
    """
    LLM 聊天端点 - SSE 流式输出
    """
    from fastapi.responses import StreamingResponse
    import httpx
    import json
    from prompts import CHAT_SYSTEM_PROMPT
    
    # 检查 LLM 配置
    from llm import BASE_URL, API_KEY, MODEL
    if not all([BASE_URL, API_KEY, MODEL]):
        return {"error": "LLM not configured"}
    
    # 构建消息列表
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    
    # 添加历史消息
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # 添加当前用户消息
    messages.append({"role": "user", "content": req.message})
    
    async def generate_stream():
        """生成 SSE 流"""
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{BASE_URL}/chat/completions",
                    json={
                        "model": MODEL,
                        "messages": messages,
                        "temperature": 0.7,
                        "stream": True
                    },
                    headers={
                        "Authorization": f"Bearer {API_KEY}",
                        "Content-Type": "application/json"
                    }
                ) as response:
                    response.raise_for_status()
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]  # Remove "data: " prefix
                            
                            if data_str == "[DONE]":
                                yield f"data: {json.dumps({'type': 'done'})}\n\n"
                                break
                            
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                
                                # 检查 choices 是否为空
                                if not choices:
                                    print(f"Warning: Empty choices in chunk: {chunk}")
                                    continue
                                
                                # 检查 choices[0] 是否存在
                                if len(choices) == 0:
                                    print(f"Warning: choices list is empty")
                                    continue
                                    
                                delta = choices[0].get("delta", {})
                                
                                # 处理 thinking (如果模型支持)
                                if "thinking" in delta:
                                    yield f"data: {json.dumps({'type': 'thinking', 'content': delta['thinking']})}\n\n"
                                
                                # 处理 content
                                if "content" in delta:
                                    yield f"data: {json.dumps({'type': 'content', 'content': delta['content']})}\n\n"
                                    
                            except json.JSONDecodeError as e:
                                print(f"JSON decode error: {e}, data: {data_str}")
                                continue
                            except IndexError as e:
                                print(f"Index error: {e}, choices: {choices}")
                                continue
                            except Exception as e:
                                print(f"Unexpected error in chunk processing: {e}")
                                import traceback
                                traceback.print_exc()
                                continue
                                
        except httpx.HTTPStatusError as e:
            print(f"Chat HTTP Error: {e.response.status_code} - {e.response.text}")
            yield f"data: {json.dumps({'type': 'error', 'error': f'LLM API error: {e.response.status_code}'})}\n\n"
        except Exception as e:
            print(f"Chat Error: {str(e)}")
            import traceback
            traceback.print_exc()
            yield f"data: {json.dumps({'type': 'error', 'error': str(e)})}\n\n"
    
    return StreamingResponse(
        generate_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        }
    )

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    CONNECTED_CLIENTS.append(websocket)
    try:
        while True:
            # 保持连接，也可以接收前端的心跳
            await websocket.receive_text()
    except WebSocketDisconnect:
        CONNECTED_CLIENTS.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
