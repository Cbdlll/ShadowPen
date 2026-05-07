"""
Intelligent Attack Surface Analyzer

Uses LLM to perform intelligent analysis, filtering, and prioritization of attack surfaces discovered by the crawler
"""
import json
from typing import List, Dict, Any, AsyncGenerator
import httpx
from pathlib import Path
from dotenv import load_dotenv
import os

# Load environment variables
env_path = Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)

BASE_URL = os.getenv("BASE_URL")
API_KEY = os.getenv("API_KEY")
MODEL = os.getenv("MODEL")


class AttackSurfaceAnalyzer:
    """Attack surface analyzer"""
    
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
        Analyze attack surfaces and return results as a stream

        Args:
            surfaces: List of attack surfaces discovered by the crawler

        Yields:
            Dictionaries containing analysis progress and results
        """
        from prompts import ATTACK_SURFACE_ANALYSIS_PROMPT
        
        # Build analysis prompt
        surfaces_json = json.dumps(surfaces, ensure_ascii=False, indent=2)
        
        # Limit input size (to avoid exceeding token limit)
        if len(surfaces) > 100:
            yield {
                "type": "warning",
                "message": f"Too many attack surfaces ({len(surfaces)}), only the first 100 will be analyzed"
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
                "content": "You are a world-class XSS security testing expert, skilled at analyzing attack surfaces and identifying high-value targets."
            },
            {
                "role": "user", 
                "content": prompt
            }
        ]
        
        # Stream call to LLM
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3,  # Lower temperature for more consistent results
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
                    
                    # Collect full response
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
                                    
                                    # Stream content chunks
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
                    
                    # Parse final result
                    yield {
                        "type": "parsing",
                        "message": "Parsing analysis results..."
                    }
                    
                    analysis_result = self._parse_analysis_result(full_content)
                    
                    yield {
                        "type": "done",
                        "result": analysis_result
                    }
                    
        except httpx.HTTPStatusError as e:
            yield {
                "type": "error",
                "error": f"LLM API error: {e.response.status_code}"
            }
        except Exception as e:
            yield {
                "type": "error",
                "error": f"Analysis failed: {str(e)}"
            }
    
    def _parse_analysis_result(self, content: str) -> Dict[str, Any]:
        """
        Parse analysis results returned by LLM

        Args:
            content: Full content returned by LLM

        Returns:
            Parsed analysis results
        """
        try:
            # Clean up Markdown code blocks
            content = content.strip()
            
            # Remove possible Markdown markers
            if content.startswith("```json"):
                content = content[7:]
            elif content.startswith("```"):
                content = content[3:]
            
            if content.endswith("```"):
                content = content[:-3]
            
            content = content.strip()
            
            # Print raw content for debugging
            print(f"=== LLM Raw Response (first 500 chars) ===")
            print(content[:500])
            print(f"=== End of Raw Response ===")
            
            # Parse JSON
            result = json.loads(content)
            
            # Validate result format
            if not isinstance(result, dict):
                raise ValueError("Analysis result must be a dictionary")
            
            # Ensure required fields exist
            if "high_value_surfaces" not in result:
                result["high_value_surfaces"] = []
            if "filtered_out" not in result:
                result["filtered_out"] = []
            if "summary" not in result:
                result["summary"] = "Analysis complete"
            
            # Print parsed result statistics
            print(f"=== Parsed Result Stats ===")
            print(f"High value surfaces: {len(result['high_value_surfaces'])}")
            print(f"Filtered out: {len(result['filtered_out'])}")
            print(f"Summary: {result['summary']}")
            print(f"=== End of Stats ===")
            
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing failed: {e}")
            print(f"Error location: line {e.lineno}, column {e.colno}")
            print(f"First 1000 chars of raw content: {content[:1000]}")

            # Return error info while keeping structure intact
            return {
                "high_value_surfaces": [],
                "filtered_out": [],
                "summary": f"JSON parsing failed: {str(e)}",
                "error": str(e),
                "raw_content": content[:1000]
            }
        except Exception as e:
            print(f"Parsing error: {e}")
            import traceback
            traceback.print_exc()
            
            return {
                "high_value_surfaces": [],
                "filtered_out": [],
                "summary": f"Parsing error: {str(e)}",
                "error": str(e)
            }


async def analyze_attack_surfaces(surfaces: List[Dict[str, Any]]) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Convenience function: analyze attack surfaces

    Args:
        surfaces: List of attack surfaces

    Yields:
        Analysis result stream
    """
    analyzer = AttackSurfaceAnalyzer()
    async for result in analyzer.analyze_surfaces(surfaces):
        yield result
