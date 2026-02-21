"""AI Agents for automated software development."""

# Legacy agents (old implementations)
from .developer_agent import DeveloperAgent, AgentContext
from .enhanced_developer_agent import ToolUseDeveloperAgent

# New Intelligent Agent with ORPA + Tool-Use
from .agent_types import (
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
from .orpa_states import ORPAStateMachine, ORPAWorkflow
from .intelligent_agent import IntelligentAgent

__all__ = [
    # Legacy
    "DeveloperAgent",
    "AgentContext",
    "ToolUseDeveloperAgent",
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
