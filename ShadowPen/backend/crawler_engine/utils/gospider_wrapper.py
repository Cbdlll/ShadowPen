"""
GoSpider Wrapper Module

Wraps the GoSpider command-line tool for broad URL discovery
"""
import asyncio
import json
import logging
import os
import shutil
from typing import List, Optional

logger = logging.getLogger(__name__)


class GoSpiderWrapper:
    """GoSpider tool wrapper class

    Features:
    - Call GoSpider for URL discovery
    - Parse GoSpider output
    - Fallback strategy (returns single URL when not installed)
    """
    
    def __init__(self, gospider_path: str = None, timeout: int = 120):
        """
        Args:
            gospiper_path: GoSpider executable path (defaults to bin/gospider)
            timeout: Execution timeout in seconds
        """
        # Prefer the binary installed in the image/system PATH. The checked-in
        # bin/gospider may be built for a different CPU architecture.
        if gospider_path is None:
            system_gospider = shutil.which("gospider")
            if system_gospider:
                gospider_path = system_gospider
            else:
                project_gospider = os.path.join(os.path.dirname(__file__), '../../bin/gospider')
                if os.path.exists(project_gospider) and os.access(project_gospider, os.X_OK) and os.path.getsize(project_gospider) > 1000:
                    gospider_path = project_gospider
                else:
                    gospider_path = "gospider"  # Fall back to system PATH
        
        self.gospider_path = gospider_path
        self.timeout = timeout
        self._is_available = None
    
    async def check_availability(self) -> bool:
        """Check whether GoSpider is available"""
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
            logger.info(f"GoSpider available: {self.gospider_path}")
            return True
        except (FileNotFoundError, OSError, asyncio.TimeoutError) as e:
            self._is_available = False
            logger.warning(
                f"GoSpider not found or unavailable: {self.gospider_path} ({e})\n"
                "Hint: install with 'GO111MODULE=on go install github.com/jaeles-project/gospider@latest'"
            )
            return False
    
    async def discover_urls(
        self,
        target: str,
        concurrency: int = 10,
        depth: int = 3,
        timeout: Optional[int] = None
    ) -> List[str]:
        """Use GoSpider to discover URLs

        Args:
            target: Target URL
            concurrency: Concurrency level
            depth: Crawling depth
            timeout: Timeout in seconds (overrides default)

        Returns:
            List of discovered URLs
        """
        # Check availability
        if not await self.check_availability():
            logger.info("Fallback mode: returning target URL only")
            return [target]
        
        timeout = timeout or self.timeout
        
        try:
            # Build command
            cmd = [
                self.gospider_path,
                "-s", target,
                "-c", str(concurrency),
                "-d", str(depth),
                "--json",  # JSON output
                "--no-redirect",  # Do not follow redirects
            ]
            
            logger.info(f"Executing GoSpider: {' '.join(cmd)}")
            
            # Execute command
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
                logger.error(f"GoSpider execution timed out ({timeout}s)")
                return [target]
            
            # Parse output
            urls = self._parse_output(stdout.decode('utf-8', errors='ignore'))
            
            if stderr:
                logger.debug(f"GoSpider stderr: {stderr.decode('utf-8', errors='ignore')[:200]}")
            
            logger.info(f"GoSpider discovered {len(urls)} URLs")
            return urls if urls else [target]
            
        except Exception as e:
            logger.error(f"GoSpider execution failed: {e}")
            return [target]
    
    def _parse_output(self, output: str) -> List[str]:
        """Parse GoSpider output

        Args:
            output: GoSpider standard output

        Returns:
            List of URLs
        """
        urls = set()
        
        for line in output.splitlines():
            line = line.strip()
            if not line:
                continue
            
            try:
                # GoSpider outputs in JSON format
                data = json.loads(line)
                
                # Extract URL
                if "url" in data:
                    urls.add(data["url"])
                elif "output" in data:
                    urls.add(data["output"])
                    
            except json.JSONDecodeError:
                # Non-JSON format, try to extract URL directly
                if line.startswith('http://') or line.startswith('https://'):
                    urls.add(line)
        
        return sorted(list(urls))
    
    @staticmethod
    def install_hint() -> str:
        """Return installation hint"""
        return (
            "GoSpider is not installed. Installation method:\n"
            "  GO111MODULE=on go install github.com/jaeles-project/gospider@latest\n"
            "Or use fallback mode to scan a single URL only."
        )
