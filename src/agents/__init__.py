"""AI Agents for automated software development."""

# New Intelligent Agent with ORPA + Tool-Use (imported first, no legacy deps)
from src.agents.agent_types import (
    AgentConfig,
    AgentContext as IntelligentAgentContext,
    AgentResult,
    TicketInfo,
    ORPAState,
    ReasoningResult,
    ToolExecutionPlan,
    ToolExecutionStep,
    ToolExecutionResult,
)
from src.agents.orpa_states import ORPAStateMachine, ORPAWorkflow
from src.agents.intelligent_agent import IntelligentAgent

__all__ = [
    # New Intelligent Agent
    "IntelligentAgent",
    "IntelligentAgentContext",
    "AgentConfig",
    "AgentResult",
    "TicketInfo",
    "ORPAState",
    "ORPAStateMachine",
    "ORPAWorkflow",
    "ReasoningResult",
    "ToolExecutionPlan",
    "ToolExecutionStep",
    "ToolExecutionResult",
]

# Legacy agents (optional, only if dependencies available)
try:
    from src.agents.developer_agent import DeveloperAgent, AgentContext
    from src.agents.enhanced_developer_agent import ToolUseDeveloperAgent
    __all__.extend(["DeveloperAgent", "AgentContext", "ToolUseDeveloperAgent"])
except ImportError:
    pass  # Legacy agents require additional dependencies
