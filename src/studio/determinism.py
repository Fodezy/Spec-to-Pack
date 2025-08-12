"""Determinism utilities for consistent outputs."""

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict


class DeterminismUtils:
    """Utilities to ensure deterministic outputs."""
    
    @staticmethod
    def normalize_json(data: Dict[str, Any], exclude_keys: set = None) -> str:
        """Normalize JSON output with sorted keys and consistent formatting."""
        if exclude_keys is None:
            exclude_keys = {"generated_at"}
        
        # Remove timestamp keys for comparison
        normalized_data = {
            k: v for k, v in data.items() 
            if k not in exclude_keys
        }
        
        return json.dumps(normalized_data, sort_keys=True, indent=2, ensure_ascii=False)
    
    @staticmethod
    def ensure_lf_newlines(content: str) -> str:
        """Ensure LF newlines (Unix style) regardless of platform."""
        return content.replace('\r\n', '\n').replace('\r', '\n')
    
    @staticmethod
    def utc_timestamp() -> str:
        """Generate UTC timestamp in ISO format."""
        return datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z')
    
    @staticmethod
    def normalize_file_for_comparison(file_path: Path, exclude_patterns: list = None) -> str:
        """Normalize a file's content for deterministic comparison."""
        if exclude_patterns is None:
            exclude_patterns = [
                "generated_at",
                "run_id", 
                "timestamp"
            ]
        
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Normalize newlines
        content = DeterminismUtils.ensure_lf_newlines(content)
        
        # Handle JSON files
        if file_path.suffix == '.json':
            try:
                data = json.loads(content)
                data = DeterminismUtils._remove_nested_patterns(data, exclude_patterns)
                content = DeterminismUtils.normalize_json(data, exclude_patterns)
            except json.JSONDecodeError:
                pass  # Not valid JSON, keep as is
        
        # Handle JSONL files (JSON Lines)
        elif file_path.suffix == '.jsonl':
            try:
                lines = content.strip().split('\n')
                normalized_lines = []
                for line in lines:
                    if line.strip():  # Skip empty lines
                        data = json.loads(line)
                        data = DeterminismUtils._remove_nested_patterns(data, exclude_patterns)
                        normalized_lines.append(json.dumps(data, sort_keys=True, ensure_ascii=False))
                content = '\n'.join(normalized_lines)
            except json.JSONDecodeError:
                pass  # Not valid JSONL, keep as is
        
        return content
    
    @staticmethod
    def _remove_nested_patterns(data: Any, exclude_patterns: list) -> Any:
        """Recursively remove patterns from nested data structures."""
        if isinstance(data, dict):
            return {
                k: DeterminismUtils._remove_nested_patterns(v, exclude_patterns)
                for k, v in data.items()
                if k not in exclude_patterns
            }
        elif isinstance(data, list):
            return [DeterminismUtils._remove_nested_patterns(item, exclude_patterns) for item in data]
        else:
            return data