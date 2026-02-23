"""Iteration Tracker for Agent Learning System.

Tracks each ORPA iteration for later analysis and learning.
"""
import uuid
import json
from typing import Dict, List, Any, Optional
from datetime import datetime
from dataclasses import dataclass, field


@dataclass
class IterationData:
    """Data for a single ORPA iteration."""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    ticket_id: str = ""
    iteration_number: int = 0
    orpa_state: str = ""  # "observing", "reasoning", "planning", "acting"
    
    # Intent
    intended_action: str = ""
    tools_planned: List[str] = field(default_factory=list)
    
    # Execution
    tools_executed: List[Dict[str, Any]] = field(default_factory=list)
    execution_success: bool = False
    execution_output: str = ""
    
    # Errors
    error_occurred: bool = False
    error_message: str = ""
    error_type: str = ""
    
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "ticket_id": self.ticket_id,
            "iteration_number": self.iteration_number,
            "orpa_state": self.orpa_state,
            "intended_action": self.intended_action,
            "tools_planned": self.tools_planned,
            "tools_executed": self.tools_executed,
            "execution_success": self.execution_success,
            "execution_output": self.execution_output,
            "error_occurred": self.error_occurred,
            "error_message": self.error_message,
            "error_type": self.error_type,
            "created_at": self.created_at,
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "IterationData":
        """Create from dictionary."""
        return cls(**data)


class IterationTracker:
    """Tracks iterations for a single ticket processing session."""
    
    def __init__(self, ticket_id: str):
        self.ticket_id = ticket_id
        self.iterations: List[IterationData] = []
        self.current_iteration: Optional[IterationData] = None
    
    def start_iteration(self, iteration_number: int, orpa_state: str, intended_action: str = "") -> IterationData:
        """Start tracking a new iteration."""
        self.current_iteration = IterationData(
            ticket_id=self.ticket_id,
            iteration_number=iteration_number,
            orpa_state=orpa_state,
            intended_action=intended_action,
        )
        return self.current_iteration
    
    def add_tools_planned(self, tools: List[str]):
        """Add tools that were planned for this iteration."""
        if self.current_iteration:
            self.current_iteration.tools_planned = tools
    
    def record_execution(
        self, 
        tools_executed: List[Dict[str, Any]], 
        success: bool,
        output: str = ""
    ):
        """Record the execution results."""
        if self.current_iteration:
            self.current_iteration.tools_executed = tools_executed
            self.current_iteration.execution_success = success
            self.current_iteration.execution_output = output
    
    def record_error(self, message: str, error_type: str = "unknown"):
        """Record an error that occurred."""
        if self.current_iteration:
            self.current_iteration.error_occurred = True
            self.current_iteration.error_message = message
            self.current_iteration.error_type = error_type
    
    def finish_iteration(self):
        """Finish the current iteration and add to list."""
        if self.current_iteration:
            self.iterations.append(self.current_iteration)
            self.current_iteration = None
    
    def get_all_iterations(self) -> List[IterationData]:
        """Get all completed iterations."""
        return self.iterations
    
    def get_failed_attempts(self) -> List[IterationData]:
        """Get iterations that had errors or were not successful."""
        return [
            it for it in self.iterations 
            if it.error_occurred or not it.execution_success
        ]
    
    def to_json(self) -> str:
        """Serialize all iterations to JSON."""
        return json.dumps([it.to_dict() for it in self.iterations], indent=2)
    
    @classmethod
    def classify_error(cls, error: Exception) -> str:
        """Classify an error type."""
        error_msg = str(error).lower()
        
        if "file not found" in error_msg or "no such file" in error_msg:
            return "file_not_found"
        elif "permission" in error_msg or "access denied" in error_msg:
            return "permission_denied"
        elif "syntax" in error_msg or "parse" in error_msg:
            return "syntax_error"
        elif "timeout" in error_msg:
            return "timeout"
        elif "rate limit" in error_msg:
            return "rate_limited"
        elif "connection" in error_msg:
            return "connection_error"
        elif "validation" in error_msg:
            return "validation_error"
        else:
            return "unknown"
