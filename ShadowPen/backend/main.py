from fastapi import FastAPI, BackgroundTasks, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List
import asyncio
import uuid
from scanner import verify_payload
from llm import generate_mutations

app = FastAPI()

# In-memory storage
VULNERABILITY_QUEUE = []
CONNECTED_CLIENTS: List[WebSocket] = []

class VerifyRequest(BaseModel):
    target_url: str
    payload: str

async def broadcast_log(message: str, type: str = "info"):
    """
    Broadcast log to all connected clients
    """
    log_entry = {
        "type": "log",
        "data": {
            "message": message,
            "level": type,
            "timestamp": str(uuid.uuid4()) # Use UUID or timestamp for simplicity
        }
    }
    for client in CONNECTED_CLIENTS:
        try:
            await client.send_json(log_entry)
        except:
            pass

async def shadow_loop(target_url: str, original_payload: str):
    """
    Shadow loop: mutate and verify
    """
    await broadcast_log(f"Starting Shadow Mode for: {target_url}", "info")
    
    # 1. Call LLM to generate mutations
    await broadcast_log(f"Requesting LLM mutations for payload: {original_payload}...", "info")
    mutations = await generate_mutations(original_payload)
    
    if not mutations:
        await broadcast_log("LLM failed to generate mutations or returned empty list.", "error")
        return

    await broadcast_log(f"LLM Generated {len(mutations)} mutations: {mutations}", "success")

    # 2. Verify mutations in parallel
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
    
    # 3. Process results
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
            
            # 4. Notify frontend in real-time
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
    Check LLM environment variable configuration status
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
    # Main loop: synchronous verification
    result = await verify_payload(req.target_url, req.payload)
    
    # If failed, trigger shadow loop
    if not result["success"]:
        background_tasks.add_task(shadow_loop, req.target_url, req.payload)
        
    return result


class CrawlRequest(BaseModel):
    url: str
    max_pages: int = 10

def normalize_target_url(url: str) -> str:
    """Normalize common target URL input mistakes before crawling."""
    normalized = url.strip()
    lower = normalized.lower()

    for scheme in ("http://", "https://"):
        if lower.startswith(scheme):
            rest = normalized[len(scheme):]
            if rest.lower().startswith(("http://", "https://")):
                return normalize_target_url(rest)
            return normalized

    if "://" not in normalized:
        return f"http://{normalized}"

    return normalized

@app.post("/api/crawl")
async def crawl_endpoint(req: CrawlRequest):
    """Crawling functionality - uses full XSSScanner"""
    try:
        from crawler import XSSScanner, ScannerConfig
        import json
        
        # Configure scanner
        config = ScannerConfig(
            MAX_DEPTH=2,
            MAX_ACTIONS_PER_PAGE=50,
            MAX_URLS=req.max_pages,
            CONCURRENT_PAGES=3
        )
        
        scanner = XSSScanner(config)
        
        # Execute scan
        target_url = normalize_target_url(req.url)
        result_file = await scanner.scan(target_url)
        
        # Read result file
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
    LLM attack surface analysis - SSE streaming output
    """
    from fastapi.responses import StreamingResponse
    from attack_surface_analyzer import analyze_attack_surfaces
    import json
    
    # Check LLM configuration
    from llm import BASE_URL, API_KEY, MODEL
    if not all([BASE_URL, API_KEY, MODEL]):
        return {"error": "LLM not configured"}

    async def generate_stream():
        """Generate SSE stream"""
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
    LLM chat endpoint - SSE streaming output
    """
    from fastapi.responses import StreamingResponse
    import httpx
    import json
    from prompts import CHAT_SYSTEM_PROMPT
    
    # Check LLM configuration
    from llm import BASE_URL, API_KEY, MODEL
    if not all([BASE_URL, API_KEY, MODEL]):
        return {"error": "LLM not configured"}

    # Build message list
    messages = [{"role": "system", "content": CHAT_SYSTEM_PROMPT}]
    
    # Add historical messages
    for msg in req.history:
        messages.append({"role": msg.role, "content": msg.content})
    
    # Add current user message
    messages.append({"role": "user", "content": req.message})
    
    async def generate_stream():
        """Generate SSE stream"""
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
                                
                                # Check if choices is empty
                                if not choices:
                                    print(f"Warning: Empty choices in chunk: {chunk}")
                                    continue
                                
                                # Check if choices[0] exists
                                if len(choices) == 0:
                                    print(f"Warning: choices list is empty")
                                    continue
                                    
                                delta = choices[0].get("delta", {})
                                
                                # Handle thinking (if model supports it)
                                if "thinking" in delta:
                                    yield f"data: {json.dumps({'type': 'thinking', 'content': delta['thinking']})}\n\n"
                                
                                # Handle content
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
            # Keep connection alive; can also receive frontend heartbeats
            await websocket.receive_text()
    except WebSocketDisconnect:
        CONNECTED_CLIENTS.remove(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
