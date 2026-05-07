"""
Result Persistence Module

Real-time append writing of scan results to JSON files
"""
import json
import asyncio
import os
from typing import Dict, Any, List
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class ResultWriter:
    """Result Writer

    Features:
    - Real-time append writing of JSON
    - File lock protection (prevents concurrent write conflicts)
    - Resume from breakpoint (continues appending when file already exists)
    """
    
    def __init__(self, output_file: str = "result.json"):
        """
        Args:
            output_file: Output file path
        """
        self.output_file = Path(output_file)
        self.lock = asyncio.Lock()
        self._init_file()
    
    def _init_file(self):
        """Initialize output file"""
        if not self.output_file.exists():
            # Create empty JSON array
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump([], f)
            logger.info(f"Created output file: {self.output_file}")
        else:
            logger.info(f"Output file already exists, will append: {self.output_file}")
    
    async def append_surface(self, surface: Dict[str, Any]):
        """Append a single attack surface record

        Args:
            surface: Attack surface dictionary
        """
        async with self.lock:
            try:
                # Read existing data
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                
                # Append new record
                data.append(surface)
                
                # Write back to file
                with open(self.output_file, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                    
            except Exception as e:
                logger.error(f"Failed to write result: {e}")
    
    def _surface_to_dict(self, surface: Any) -> Dict[str, Any]:
        """Convert an AttackSurface object to a dictionary"""
        if hasattr(surface, 'to_dict') and callable(surface.to_dict):
            return surface.to_dict()
        elif isinstance(surface, dict):
            return surface
        else:
            # Fallback for objects without a to_dict method, attempting to convert attributes
            return {k: v for k, v in surface.__dict__.items() if not k.startswith('_')}

    def write_surfaces(self, surfaces: List[Any]) -> None:
        """Write attack surfaces to file (append mode, with deduplication)

        Deduplication strategy: based on (request_url, method, param_name) combination
        """
        if not surfaces:
            return
        
        # Read existing data
        existing_data = []
        if self.output_file.exists():
            try:
                with open(self.output_file, 'r', encoding='utf-8') as f:
                    existing_data = json.load(f)
            except (json.JSONDecodeError, FileNotFoundError):
                logger.warning(f"Cannot read existing file {self.output_file}, will create new or overwrite")
                existing_data = []
        
        # Build deduplication set (based on request_url + method + param_name)
        seen_keys = set()
        for item in existing_data:
            key = f"{item.get('request_url', '')}|{item.get('method', '')}|{item.get('param_name', '')}"
            seen_keys.add(key)
        
        # Convert new attack surfaces to dictionaries
        new_data = []
        duplicates_count = 0
        for surface in surfaces:
            surface_dict = self._surface_to_dict(surface)
            key = f"{surface_dict.get('request_url', '')}|{surface_dict.get('method', '')}|{surface_dict.get('param_name', '')}"
            
            # Deduplication check
            if key not in seen_keys:
                new_data.append(surface_dict)
                seen_keys.add(key)
            else:
                duplicates_count += 1
        
        if duplicates_count > 0:
            logger.debug(f"Deduplication: skipped {duplicates_count} duplicate attack surfaces")
        
        # Merge data
        all_data = existing_data + new_data
        
        # Write to file
        try:
            with open(self.output_file, 'w', encoding='utf-8') as f:
                json.dump(all_data, f, ensure_ascii=False, indent=2)
            
            logger.debug(f"Wrote {len(new_data)} new attack surfaces to {self.output_file} (total {len(all_data)})")
        except Exception as e:
            logger.error(f"Failed to write result: {e}")
    
    def read_all(self) -> List[Dict[str, Any]]:
        """Read all records

        Returns:
            All attack surface records
        """
        try:
            with open(self.output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read results: {e}")
            return []
    
    def get_count(self) -> int:
        """Get record count"""
        return len(self.read_all())
    
    def clear(self):
        """Clear the file"""
        with open(self.output_file, 'w', encoding='utf-8') as f:
            json.dump([], f)
        logger.info("Output file cleared")
