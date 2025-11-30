"""
GoSpider 封装模块

封装 GoSpider 命令行工具，用于广度 URL 发现
"""
import asyncio
import subprocess
import json
import logging
from typing import List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class GoSpiderWrapper:
    """GoSpider 工具封装类
    
    功能：
    - 调用 GoSpider 进行 URL 发现
    - 解析 GoSpider 输出
    - 降级策略（未安装时返回单 URL）
    """
    
    def __init__(self, gospider_path: str = None, timeout: int = 120):
        """
        Args:
            gospiper_path: GoSpider 可执行文件路径（默认优先使用 bin/gospider）
            timeout: 执行超时时间（秒）
        """
        # 优先使用项目 bin 目录中的 gospider
        if gospider_path is None:
            import os
            project_gospider = os.path.join(os.path.dirname(__file__), '../../bin/gospider')
            if os.path.exists(project_gospider):
                gospider_path = project_gospider
            else:
                gospider_path = "gospider"  # 降级到系统路径
        
        self.gospider_path = gospider_path
        self.timeout = timeout
        self._is_available = None
    
    async def check_availability(self) -> bool:
        """检查 GoSpider 是否可用"""
        if self._is_available is not None:
            return self._is_available
        
        try:
            proc = await asyncio.create_subprocess_exec(
                self.gospider_path,
                "--help",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            await asyncio.wait_for(proc.communicate(), timeout=5)
            self._is_available = True
            logger.info(f"GoSpider 可用: {self.gospider_path}")
            return True
        except (FileNotFoundError, asyncio.TimeoutError):
            self._is_available = False
            logger.warning(
                f"GoSpider 未找到或不可用: {self.gospider_path}\n"
                "提示：安装命令 'GO111MODULE=on go install github.com/jaeles-project/gospider@latest'"
            )
            return False
    
    async def discover_urls(
        self,
        target: str,
        concurrency: int = 10,
        depth: int = 3,
        timeout: Optional[int] = None
    ) -> List[str]:
        """使用 GoSpider 发现 URL
        
        Args:
            target: 目标 URL
            concurrency: 并发数
            depth: 爬取深度
            timeout: 超时时间（覆盖默认值）
            
        Returns:
            发现的 URL 列表
        """
        # 检查可用性
        if not await self.check_availability():
            logger.info("降级模式：仅返回目标 URL")
            return [target]
        
        timeout = timeout or self.timeout
        
        try:
            # 构建命令
            cmd = [
                self.gospider_path,
                "-s", target,
                "-c", str(concurrency),
                "-d", str(depth),
                "--json",  # JSON 输出
                "--no-redirect",  # 不跟随重定向
            ]
            
            logger.info(f"执行 GoSpider: {' '.join(cmd)}")
            
            # 执行命令
            proc = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    proc.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                proc.kill()
                logger.error(f"GoSpider 执行超时 ({timeout}s)")
                return [target]
            
            # 解析输出
            urls = self._parse_output(stdout.decode('utf-8', errors='ignore'))
            
            if stderr:
                logger.debug(f"GoSpider stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
            
            logger.info(f"GoSpider 发现 {len(urls)} 个 URL")
            return urls if urls else [target]
            
        except Exception as e:
            logger.error(f"GoSpider 执行失败: {e}")
            return [target]
    
    def _parse_output(self, output: str) -> List[str]:
        """解析 GoSpider 输出
        
        Args:
            output: GoSpider 标准输出
            
        Returns:
            URL 列表
        """
        urls = set()
        
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            try:
                # GoSpider 以 JSON 格式输出
                data = json.loads(line)
                
                # 提取 URL
                if "url" in data:
                    urls.add(data["url"])
                elif "output" in data:
                    urls.add(data["output"])
                    
            except json.JSONDecodeError:
                # 非 JSON 格式，尝试直接提取 URL
                if line.startswith('http://') or line.startswith('https://'):
                    urls.add(line)
        
        return sorted(list(urls))
    
    @staticmethod
    def install_hint() -> str:
        """返回安装提示"""
        return (
            "GoSpider 未安装。安装方法：\n"
            "  GO111MODULE=on go install github.com/jaeles-project/gospider@latest\n"
            "或者使用降级模式仅扫描单个 URL。"
        )
