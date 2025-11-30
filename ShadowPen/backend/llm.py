import os
import json
import httpx
from typing import List
from pathlib import Path
from dotenv import load_dotenv

# 加载 .env 文件（从父目录）
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

# 强制检查环境变量
BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")

if not all([BASE_URL, API_KEY, MODEL]):
    # 在导入时即警告，但在运行时报错，避免阻断应用启动（允许仅运行主循环）
    print("Warning: LLM environment variables (BASE_URL, API_KEY, MODEL) not set. Shadow mode will fail.")

async def generate_mutations(user_payload: str) -> List[str]:
    """
    调用 LLM 生成变异 Payload。
    严禁 Mock，必须使用真实 API。
    """
    if not all([BASE_URL, API_KEY, MODEL]):
        print("Error: Missing LLM environment variables.")
        return []

    from prompts import MUTATION_PROMPT_TEMPLATE
    prompt = MUTATION_PROMPT_TEMPLATE.format(user_payload=user_payload)

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": MODEL,
        "messages": [
            {"role": "system", "content": "You are a security expert specializing in XSS payload mutation."},
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.7
    }

    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(f"{BASE_URL}/chat/completions", json=data, headers=headers, timeout=30.0)
            response.raise_for_status()
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # 尝试解析 JSON
            # 有时候 LLM 会包裹在 ```json ... ``` 中，需要清理
            if content.startswith("```json"):
                content = content[7:]
            if content.endswith("```"):
                content = content[:-3]
            
            mutations = json.loads(content.strip())
            if isinstance(mutations, list):
                return mutations
            else:
                print(f"LLM returned non-list format: {content}")
                return []
                
    except Exception as e:
        print(f"LLM Call Failed: {e}")
        return []
