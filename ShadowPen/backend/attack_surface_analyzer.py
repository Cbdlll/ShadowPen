"""
攻击面智能分析器

使用 LLM 对爬虫发现的攻击面进行智能分析、过滤和优先级排序
"""
import json
from typing import List, Dict, Any, AsyncGenerator
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os

# 加载环境变量
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")


class AttackSurfaceAnalyzer:
    """攻击面分析器"""
    
    def __init__(self):
        if not all([BASE_URL, API_KEY, MODEL]):
            raise ValueError("LLM environment variables not configured")
        
        self.base_url = BASE_URL
        self.api_key = API_KEY
        self.model = MODEL
    
    async def analyze_surfaces(
        self, 
        surfaces: List[Dict[str, Any]]
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        分析攻击面并流式返回结果
        
        Args:
            surfaces: 爬虫发现的攻击面列表
            
        Yields:
            分析进度和结果的字典
        """
        from prompts import ATTACK_SURFACE_ANALYSIS_PROMPT
        
        # 构建分析提示词
        surfaces_json = json.dumps(surfaces, ensure_ascii=False, indent=2)
        
        # 限制输入大小（避免超过 token 限制）
        if len(surfaces) > 100:
            yield {
                "type": "warning",
                "message": f"攻击面数量过多（{len(surfaces)}），将只分析前 100 个"
            }
            surfaces = surfaces[:100]
            surfaces_json = json.dumps(surfaces, ensure_ascii=False, indent=2)
        
        prompt = ATTACK_SURFACE_ANALYSIS_PROMPT.format(
            surfaces_json=surfaces_json,
            total_count=len(surfaces)
        )
        
        messages = [
            {
                "role": "system", 
                "content": "你是一位世界顶级的 XSS 安全测试专家，擅长分析攻击面并识别高价值目标。"
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        # 流式调用 LLM
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # 降低温度以获得更一致的结果
            "stream": True
        }
        
        try:
            async with httpx.AsyncClient(timeout=300.0) as client:
                async with client.stream(
                    "POST",
                    f"{self.base_url}/chat/completions",
                    json=data,
                    headers=headers
                ) as response:
                    response.raise_for_status()
                    
                    # 收集完整响应
                    full_content = ""
                    
                    async for line in response.aiter_lines():
                        if line.startswith("data: "):
                            data_str = line[6:]
                            
                            if data_str == "[DONE]":
                                break
                            
                            try:
                                chunk = json.loads(data_str)
                                choices = chunk.get("choices", [])
                                
                                if choices and len(choices) > 0:
                                    delta = choices[0].get("delta", {})
                                    
                                    # 流式输出内容片段
                                    if "content" in delta:
                                        content_chunk = delta["content"]
                                        full_content += content_chunk
                                        
                                        yield {
                                            "type": "content",
                                            "content": content_chunk
                                        }
                                        
                            except json.JSONDecodeError:
                                continue
                            except Exception as e:
                                print(f"Chunk processing error: {e}")
                                continue
                    
                    # 解析最终结果
                    yield {
                        "type": "parsing",
                        "message": "正在解析分析结果..."
                    }
                    
                    analysis_result = self._parse_analysis_result(full_content)
                    
                    yield {
                        "type": "done",
                        "result": analysis_result
                    }
                    
        except httpx.HTTPStatusError as e:
            yield {
                "type": "error",
                "error": f"LLM API 错误: {e.response.status_code}"
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": f"分析失败: {str(e)}"
            }
    
    def _parse_analysis_result(self, content: str) -> Dict[str, Any]:
        """
        解析 LLM 返回的分析结果
        
        Args:
            content: LLM 返回的完整内容
            
        Returns:
            解析后的分析结果
        """
        try:
            # 清理 Markdown 代码块
            content = content.strip()
            
            # 移除可能的 Markdown 标记
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # 打印原始内容用于调试
            print(f"=== LLM Raw Response (first 500 chars) ===")
            print(content[:500])
            print(f"=== End of Raw Response ===")
            
            # 解析 JSON
            result = json.loads(content)
            
            # 验证结果格式
            if not isinstance(result, dict):
                raise ValueError("分析结果必须是字典格式")
            
            # 确保必需字段存在
            if "high_value_surfaces" not in result:
                result["high_value_surfaces"] = []
            if "filtered_out" not in result:
                result["filtered_out"] = []
            if "summary" not in result:
                result["summary"] = "分析完成"
            
            # 打印解析结果统计
            print(f"=== Parsed Result Stats ===")
            print(f"High value surfaces: {len(result['high_value_surfaces'])}")
            print(f"Filtered out: {len(result['filtered_out'])}")
            print(f"Summary: {result['summary']}")
            print(f"=== End of Stats ===")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON 解析失败: {e}")
            print(f"错误位置: line {e.lineno}, column {e.colno}")
            print(f"原始内容前1000字符: {content[:1000]}")
            
            # 返回错误信息，但保持结构完整
            return {
                "high_value_surfaces": [],
                "filtered_out": [],
                "summary": f"JSON解析失败: {str(e)}",
                "error": str(e),
                "raw_content": content[:1000]
            }
        except Exception as e:
            print(f"解析错误: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "high_value_surfaces": [],
                "filtered_out": [],
                "summary": f"解析错误: {str(e)}",
                "error": str(e)
            }


async def analyze_attack_surfaces(surfaces: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    便捷函数：分析攻击面
    
    Args:
        surfaces: 攻击面列表
        
    Yields:
        分析结果流
    """
    analyzer = AttackSurfaceAnalyzer()
    async for result in analyzer.analyze_surfaces(surfaces):
        yield result
