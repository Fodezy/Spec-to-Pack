"""Audit logging for pipeline events."""

import json
from pathlib import Path
from typing import List, Optional
from datetime import datetime
from uuid import UUID

from .types import PipelineEvent


class AuditLog:
    """JSONL audit log for pipeline events."""
    
    def __init__(self, log_file: Path = None):
        """Initialize audit log with file path."""
        if log_file is None:
            log_file = Path("audit.jsonl")
        self.log_file = log_file
        self.events: List[PipelineEvent] = []
    
    def append(self, event: PipelineEvent) -> None:
        """Append an event to the audit log."""
        self.events.append(event)
    
    def log_event(
        self, 
        event_type: str, 
        run_id: UUID, 
        note: str, 
        details: dict = None,
        stage: str = "unknown",
        event: str = "",
        duration_ms: Optional[int] = None,
        level: str = "info"
    ) -> None:
        """Log an event with current timestamp."""
        event = PipelineEvent(
            event_type=event_type,
            timestamp=datetime.utcnow(),
            run_id=run_id,
            stage=stage,
            event=event,
            note=note,
            duration_ms=duration_ms,
            level=level,
            details=details or {}
        )
        self.append(event)
    
    def save(self) -> Path:
        """Save audit log to JSONL file."""
        self.log_file.parent.mkdir(parents=True, exist_ok=True)
        
        with open(self.log_file, 'w') as f:
            for event in self.events:
                # Convert to dict and handle datetime serialization
                event_dict = event.model_dump()
                event_dict['timestamp'] = event.timestamp.isoformat() + 'Z'
                event_dict['run_id'] = str(event.run_id)
                
                f.write(json.dumps(event_dict) + '\n')
        
        return self.log_file
    
    def load(self) -> List[PipelineEvent]:
        """Load audit log from JSONL file."""
        events = []
        if self.log_file.exists():
            with open(self.log_file) as f:
                for line in f:
                    if line.strip():
                        event_dict = json.loads(line)
                        # Convert back from serialized format
                        event_dict['timestamp'] = datetime.fromisoformat(
                            event_dict['timestamp'].replace('Z', '+00:00')
                        )
                        event_dict['run_id'] = UUID(event_dict['run_id'])
                        events.append(PipelineEvent(**event_dict))
        
        self.events = events
        return events