"""Type definitions for the Intelligent Agent.

Contains all dataclasses and type definitions for:
- AgentContext: Context information for agent processing
- ReasoningResult: Result from LLM reasoning phase
- ToolExecutionPlan: Plan for executing tools
- AgentConfig: Configuration for the agent
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Callable


class ORPAState(Enum):
    """ORPA Workflow States.
    
    OBSERVE → REASON → PLAN → ACT → (loop or complete)
    """
    IDLE = "idle"
    OBSERVING = "observing"
    REASONING = "reasoning"
    PLANNING = "planning"
    ACTING = "acting"
    COMPLETED = "completed"
    ERROR = "error"
    NEEDS_CLARIFICATION = "needs_clarification"


@dataclass
class AgentConfig:
    """Configuration for the IntelligentAgent.
    
    Attributes:
        customer_id: Customer identifier for workspace/memory
        max_iterations: Maximum ORPA iterations per ticket
        auto_execute: Whether to auto-execute tools or ask for confirmation
        tool_timeout: Timeout for tool execution in seconds
        llm_temperature: Temperature for LLM responses
        enable_memory: Whether to use memory systems
        enable_workspace: Whether to use workspace management
    """
    customer_id: str
    max_iterations: int = 10
    auto_execute: bool = True
    tool_timeout: int = 300
    llm_temperature: float = 0.3
    enable_memory: bool = True
    enable_workspace: bool = True
    workspace_path: Optional[str] = None
    
    # LLM Configuration
    llm_model: str = "moonshotai/kimi-k2.5"
    llm_max_tokens: int = 4096
    
    # Tool Configuration
    allowed_tools: Optional[List[str]] = None  # None = all tools
    forbidden_tools: List[str] = field(default_factory=list)
    
    # Memory Configuration
    memory_tier: str = "auto"  # auto, short_term, session, long_term, episodic
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert config to dictionary."""
        return {
            "customer_id": self.customer_id,
            "max_iterations": self.max_iterations,
            "auto_execute": self.auto_execute,
            "tool_timeout": self.tool_timeout,
            "llm_temperature": self.llm_temperature,
            "enable_memory": self.enable_memory,
            "enable_workspace": self.enable_workspace,
            "llm_model": self.llm_model,
        }


@dataclass
class TicketInfo:
    """Information about a ticket/issue to process."""
    ticket_id: str
    title: str
    description: str
    customer_id: Optional[str] = None
    repository: Optional[str] = None
    branch: Optional[str] = None
    labels: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticket_id": self.ticket_id,
            "title": self.title,
            "description": self.description,
            "customer_id": self.customer_id,
            "repository": self.repository,
            "branch": self.branch,
            "labels": self.labels,
            "metadata": self.metadata,
        }


@dataclass
class AgentContext:
    """Complete context for agent processing.
    
    This is passed through all ORPA phases and contains:
    - Ticket information
    - Memory context (relevant past learnings)
    - Workspace information
    - Current ORPA state
    """
    # Ticket Information
    ticket: TicketInfo
    
    # ORPA State
    current_state: ORPAState = ORPAState.IDLE
    iteration: int = 0
    
    # Observations (gathered in OBSERVE phase)
    observations: Dict[str, Any] = field(default_factory=dict)
    repository_structure: Optional[Dict] = None
    relevant_files: List[str] = field(default_factory=list)
    
    # Reasoning (from REASON phase)
    understanding: str = ""
    approach: str = ""
    needed_tools: List[str] = field(default_factory=list)
    needs_clarification: bool = False
    clarification_question: Optional[str] = None
    
    # Planning (from PLAN phase)
    execution_plan: Optional["ToolExecutionPlan"] = None
    
    # Acting (from ACT phase)
    execution_results: List["ToolExecutionResult"] = field(default_factory=list)
    
    # Memory Context
    relevant_learnings: List[Dict] = field(default_factory=list)
    similar_tickets: List[Dict] = field(default_factory=list)
    chat_history: List[Dict] = field(default_factory=list)
    
    # Workspace Context
    workspace_path: Optional[str] = None
    repo_info: Optional[Dict] = None
    
    # Metadata
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def update_state(self, new_state: ORPAState):
        """Update the ORPA state."""
        self.current_state = new_state
        self.updated_at = datetime.utcnow().isoformat()
    
    def add_observation(self, key: str, value: Any):
        """Add an observation."""
        self.observations[key] = value
        self.updated_at = datetime.utcnow().isoformat()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert context to dictionary."""
        return {
            "ticket": self.ticket.to_dict(),
            "current_state": self.current_state.value,
            "iteration": self.iteration,
            "observations": self.observations,
            "repository_structure": self.repository_structure,
            "relevant_files": self.relevant_files,
            "understanding": self.understanding,
            "approach": self.approach,
            "needed_tools": self.needed_tools,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "relevant_learnings": self.relevant_learnings,
            "similar_tickets": self.similar_tickets,
            "workspace_path": self.workspace_path,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }


@dataclass
class ReasoningResult:
    """Result from the LLM reasoning phase.
    
    This is what the LLM returns after analyzing the ticket
    and available tools.
    """
    understanding: str
    """What the LLM understood about the ticket."""
    
    needed_tools: List[str]
    """List of tool names that will be needed."""
    
    approach: str
    """High-level approach to solving the ticket."""
    
    needs_clarification: bool = False
    """Whether the LLM needs more information."""
    
    clarification_question: Optional[str] = None
    """Question to ask if clarification is needed."""
    
    confidence: float = 0.0
    """Confidence score (0-1) in the understanding."""
    
    @classmethod
    def parse(cls, response: Dict[str, Any]) -> "ReasoningResult":
        """Parse LLM response into ReasoningResult."""
        return cls(
            understanding=response.get("understanding", ""),
            needed_tools=response.get("needed_tools", []),
            approach=response.get("approach", ""),
            needs_clarification=response.get("needs_clarification", False),
            clarification_question=response.get("clarification_question"),
            confidence=response.get("confidence", 0.0),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "understanding": self.understanding,
            "needed_tools": self.needed_tools,
            "approach": self.approach,
            "needs_clarification": self.needs_clarification,
            "clarification_question": self.clarification_question,
            "confidence": self.confidence,
        }


@dataclass
class ToolExecutionStep:
    """A single step in a tool execution plan."""
    step_number: int
    tool_name: str
    parameters: Dict[str, Any]
    description: str
    depends_on: Optional[int] = None  # Step number this depends on
    condition: Optional[str] = None  # Condition to execute (e.g., "if previous success")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step_number": self.step_number,
            "tool_name": self.tool_name,
            "parameters": self.parameters,
            "description": self.description,
            "depends_on": self.depends_on,
            "condition": self.condition,
        }


@dataclass
class ToolExecutionPlan:
    """Complete plan for executing tools.
    
    Created in the PLAN phase and executed in the ACT phase.
    """
    steps: List[ToolExecutionStep]
    estimated_steps: int = 0
    rollback_steps: List[ToolExecutionStep] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.estimated_steps:
            self.estimated_steps = len(self.steps)
    
    def get_next_step(self, current_step: int) -> Optional[ToolExecutionStep]:
        """Get the next step to execute."""
        for step in self.steps:
            if step.step_number == current_step + 1:
                return step
        return None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "steps": [s.to_dict() for s in self.steps],
            "estimated_steps": self.estimated_steps,
            "rollback_steps": [s.to_dict() for s in self.rollback_steps],
        }


@dataclass
class ToolExecutionResult:
    """Result of executing a tool step."""
    step: ToolExecutionStep
    success: bool
    data: Any = None
    error: Optional[str] = None
    execution_time_ms: float = 0.0
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "step": self.step.to_dict(),
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "execution_time_ms": self.execution_time_ms,
            "timestamp": self.timestamp,
        }


@dataclass
class AgentResult:
    """Final result from agent processing a ticket."""
    ticket_id: str
    success: bool
    message: str
    changes_made: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    iterations_used: int = 0
    final_state: ORPAState = ORPAState.IDLE
    error: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "ticket_id": self.ticket_id,
            "success": self.success,
            "message": self.message,
            "changes_made": self.changes_made,
            "files_modified": self.files_modified,
            "iterations_used": self.iterations_used,
            "final_state": self.final_state.value,
            "error": self.error,
            "metadata": self.metadata,
            "timestamp": self.timestamp,
        }


# Type aliases for callbacks
StateTransitionCallback = Callable[[ORPAState, ORPAState, AgentContext], None]
ToolExecutionCallback = Callable[[ToolExecutionStep, ToolExecutionResult], None]
ObservationCallback = Callable[[str, Any, AgentContext], None]
