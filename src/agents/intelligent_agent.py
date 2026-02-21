"""IntelligentAgent - Main agent with Tool-Use, Memory, and ORPA workflow.

This agent integrates:
- Tool-Use Pattern (AI decides which tools to use)
- 4-Layer Memory System (Short-term, Session, Long-term, Episodic)
- Workspace/Repository Management
- ORPA Workflow (Observe, Reason, Plan, Act)

Example:
    config = AgentConfig(customer_id="acme-corp")
    agent = IntelligentAgent("dev-agent-1", config)
    
    result = await agent.process_ticket(ticket_id="ABC-123")
"""

import os
import json
import logging
from typing import Dict, List, Optional, Any, Callable
from datetime import datetime
from pathlib import Path

# Import types
from .agent_types import (
    AgentConfig,
    AgentContext,
    AgentResult,
    TicketInfo,
    ORPAState,
    ReasoningResult,
    ToolExecutionPlan,
    ToolExecutionStep,
    ToolExecutionResult,
)
from .orpa_states import ORPAStateMachine, ORPAWorkflow

# Import existing components
try:
    from ..tools.registry import ToolRegistry
    from ..tools.executor import ToolExecutor
    from ..tools.base import ToolResult
    from ..tools.file_tools import FileReadTool, FileWriteTool, FileListTool, FileSearchTool
    from ..tools.code_tools import CodeAnalyzeTool, CodeRefactorTool
    from ..tools.git_tools import GitStatusTool, GitCommitTool, GitPushTool
    TOOLS_AVAILABLE = True
except ImportError:
    TOOLS_AVAILABLE = False

try:
    from ..memory.unified_manager import UnifiedMemoryManager, LearningEpisode
    MEMORY_AVAILABLE = True
except ImportError:
    MEMORY_AVAILABLE = False

try:
    from ..infrastructure.workspace_manager import WorkspaceManager, get_workspace_manager
    from ..infrastructure.repository_manager import RepositoryManager, get_repository_manager
    WORKSPACE_AVAILABLE = True
except ImportError:
    WORKSPACE_AVAILABLE = False

try:
    from ..llm.kimi_client import KimiClient, Message, LLMResponse
    LLM_AVAILABLE = True
except ImportError:
    LLM_AVAILABLE = False

logger = logging.getLogger(__name__)


class IntelligentAgent:
    """Intelligent agent with Tool-Use, Memory, and ORPA workflow.
    
    This is the main agent class that integrates all components:
    - Tool Registry & Executor for tool-use
    - Unified Memory Manager for 4-layer memory
    - Workspace/Repository Manager for code operations
    - ORPA State Machine for workflow management
    - Kimi LLM Client for reasoning
    
    Attributes:
        agent_id: Unique identifier for this agent instance
        config: Agent configuration
        tools: Tool registry with all available tools
        executor: Tool executor with logging
        memory: Unified memory manager (4 layers)
        workspace: Workspace manager for customer repos
        repo_manager: Repository manager for git operations
        llm: LLM client for reasoning
        state_machine: ORPA state machine
    """
    
    def __init__(self, agent_id: str, config: AgentConfig):
        """Initialize the IntelligentAgent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Agent configuration
            
        Raises:
            RuntimeError: If required dependencies are not available
        """
        self.agent_id = agent_id
        self.config = config
        
        # Check dependencies
        if not TOOLS_AVAILABLE:
            raise RuntimeError("Tools module not available")
        if not LLM_AVAILABLE:
            raise RuntimeError("LLM module not available")
        
        # === 1. TOOLS initialisieren ===
        self.tools = ToolRegistry()
        self._register_all_tools()
        self.executor = ToolExecutor(self.tools, log_executions=True)
        
        # === 2. MEMORY initialisieren ===
        if config.enable_memory and MEMORY_AVAILABLE:
            self.memory = UnifiedMemoryManager(
                customer_id=config.customer_id,
                config=None  # Use defaults
            )
        else:
            self.memory = None
            if config.enable_memory:
                logger.warning("Memory enabled but module not available")
        
        # === 3. WORKSPACE initialisieren ===
        if config.enable_workspace and WORKSPACE_AVAILABLE:
            self.workspace = get_workspace_manager()
            self.repo_manager = get_repository_manager()
        else:
            self.workspace = None
            self.repo_manager = None
            if config.enable_workspace:
                logger.warning("Workspace enabled but module not available")
        
        # === 4. LLM Client ===
        self.llm = KimiClient()
        
        # === 5. ORPA State Machine ===
        self.state_machine = ORPAStateMachine(
            max_iterations=config.max_iterations,
            on_transition=self._on_state_transition
        )
        
        # === Callbacks ===
        self._progress_callbacks: List[Callable[[ORPAState, AgentContext], None]] = []
        
        logger.info(f"IntelligentAgent '{agent_id}' initialized for customer '{config.customer_id}'")
    
    def _register_all_tools(self):
        """Register all available tools with the registry."""
        # File tools
        self.tools.register(FileReadTool(), category="file")
        self.tools.register(FileWriteTool(), category="file")
        self.tools.register(FileListTool(), category="file")
        self.tools.register(FileSearchTool(), category="file")
        
        # Code tools (if available)
        try:
            self.tools.register(CodeAnalyzeTool(), category="code")
            self.tools.register(CodeRefactorTool(), category="code")
        except Exception:
            pass
        
        # Git tools (if available)
        try:
            self.tools.register(GitStatusTool(), category="git")
            self.tools.register(GitCommitTool(), category="git")
            self.tools.register(GitPushTool(), category="git")
        except Exception:
            pass
        
        logger.debug(f"Registered {len(self.tools)} tools")
    
    def _on_state_transition(
        self, 
        old_state: ORPAState, 
        new_state: ORPAState, 
        context: Optional[AgentContext]
    ):
        """Callback for state transitions."""
        logger.info(f"ORPA: {old_state.value} → {new_state.value}")
        
        # Notify progress callbacks
        for callback in self._progress_callbacks:
            try:
                callback(new_state, context)
            except Exception as e:
                logger.warning(f"Progress callback failed: {e}")
    
    def on_progress(self, callback: Callable[[ORPAState, AgentContext], None]):
        """Register a progress callback.
        
        Args:
            callback: Function(state, context) called on state changes
        """
        self._progress_callbacks.append(callback)
    
    # ==================================================================
    # MAIN WORKFLOW
    # ==================================================================
    
    async def process_ticket(self, ticket_id: str, ticket_data: Optional[Dict] = None) -> AgentResult:
        """Process a ticket through the complete ORPA workflow.
        
        This is the main entry point for ticket processing.
        
        Args:
            ticket_id: The ticket identifier
            ticket_data: Optional ticket data (fetched if not provided)
            
        Returns:
            AgentResult with the processing outcome
        """
        logger.info(f"Processing ticket {ticket_id}")
        
        try:
            # Create ticket info
            if ticket_data:
                ticket = TicketInfo(
                    ticket_id=ticket_id,
                    title=ticket_data.get("title", ""),
                    description=ticket_data.get("description", ""),
                    customer_id=ticket_data.get("customer_id", self.config.customer_id),
                    repository=ticket_data.get("repository"),
                    branch=ticket_data.get("branch"),
                    labels=ticket_data.get("labels", []),
                    metadata=ticket_data.get("metadata", {}),
                )
            else:
                # Create minimal ticket info
                ticket = TicketInfo(
                    ticket_id=ticket_id,
                    title=f"Ticket {ticket_id}",
                    description="",
                    customer_id=self.config.customer_id,
                )
            
            # Create context
            context = AgentContext(ticket=ticket)
            context.workspace_path = self.config.workspace_path
            
            # Load memory context if available
            if self.memory:
                memory_context = self.memory.build_agent_context(
                    ticket_id=ticket_id,
                    ticket_description=ticket.description
                )
                context.relevant_learnings = memory_context.get("relevant_learnings", [])
                context.similar_tickets = memory_context.get("recent_learnings", [])
                context.chat_history = memory_context.get("chat_history", [])
            
            # Start ORPA workflow
            self.state_machine.start(context)
            
            # Run workflow loop
            while not self.state_machine.is_terminal:
                state = self.state_machine.current_state
                
                if state == ORPAState.OBSERVING:
                    await self._observe(context)
                    
                elif state == ORPAState.REASONING:
                    await self._reason(context)
                    
                elif state == ORPAState.PLANNING:
                    await self._plan(context)
                    
                elif state == ORPAState.ACTING:
                    await self._act(context)
                    
                elif state == ORPAState.NEEDS_CLARIFICATION:
                    # Halt and wait for clarification
                    return self._create_result(context, success=False)
                    
                elif state == ORPAState.ERROR:
                    return self._create_result(context, success=False)
            
            # Workflow completed
            return self._create_result(context, success=True)
            
        except Exception as e:
            logger.exception(f"Error processing ticket {ticket_id}")
            return AgentResult(
                ticket_id=ticket_id,
                success=False,
                message=f"Processing failed: {str(e)}",
                error=str(e),
                final_state=ORPAState.ERROR,
            )
    
    # ==================================================================
    # ORPA PHASES
    # ==================================================================
    
    async def _observe(self, context: AgentContext):
        """ORPA: OBSERVE Phase - Gather information.
        
        Collects:
        - Repository structure
        - Relevant files based on ticket
        - Git status
        - Similar past solutions from memory
        """
        logger.debug("ORPA Phase: OBSERVING")
        context.iteration += 1
        
        try:
            # 1. Get repository info if workspace available
            if self.workspace and context.ticket.customer_id:
                repo_info = self.workspace.get_repo_info(context.ticket.customer_id)
                if repo_info:
                    context.repo_info = repo_info
                    context.add_observation("repo_info", repo_info)
            
            # 2. Get repository structure
            if self.workspace and context.ticket.customer_id:
                workspace_path = self.workspace.get_workspace_path(context.ticket.customer_id)
                if workspace_path and Path(workspace_path).exists():
                    # List top-level structure
                    result = await self.executor.execute(
                        "file_list",
                        {"path": str(workspace_path), "recursive": False},
                        agent_id=self.agent_id,
                        ticket_id=context.ticket.ticket_id
                    )
                    if result.success:
                        context.repository_structure = result.data
                        context.add_observation("repository_structure", result.data)
            
            # 3. Search for relevant files based on ticket
            if context.ticket.description:
                keywords = self._extract_keywords(context.ticket.description)
                for keyword in keywords[:3]:  # Limit to top 3 keywords
                    if self.workspace and context.ticket.customer_id:
                        workspace_path = self.workspace.get_workspace_path(context.ticket.customer_id)
                        if workspace_path:
                            result = await self.executor.execute(
                                "file_search",
                                {
                                    "pattern": keyword,
                                    "path": str(workspace_path),
                                    "max_results": 5
                                },
                                agent_id=self.agent_id,
                                ticket_id=context.ticket.ticket_id
                            )
                            if result.success and result.data.get("matches"):
                                context.relevant_files.extend([
                                    m["file"] for m in result.data["matches"]
                                ])
            
            # 4. Get similar solutions from memory
            if self.memory and context.ticket.description:
                similar = self.memory.find_solutions(context.ticket.description, limit=3)
                if similar:
                    context.relevant_learnings = similar
                    context.add_observation("similar_solutions", similar)
            
            # Transition to REASONING
            self.state_machine.transition_to(ORPAState.REASONING, "Observation complete")
            
        except Exception as e:
            logger.exception("Observation failed")
            self.state_machine.complete(success=False, reason=f"Observation error: {e}")
    
    async def _reason(self, context: AgentContext):
        """ORPA: REASON Phase - Analyze and decide.
        
        The LLM analyzes:
        - What the user wants
        - Which tools are needed
        - The approach to take
        """
        logger.debug("ORPA Phase: REASONING")
        
        try:
            # Get tool schemas for LLM
            tools_schemas = self.tools.get_schemas_for_llm(format="openai")
            
            # Build reasoning prompt
            prompt = self._build_reasoning_prompt(context, tools_schemas)
            
            # Call LLM
            messages = [
                Message(role="system", content=self._get_system_prompt()),
                Message(role="user", content=prompt)
            ]
            
            response = await self.llm.chat(
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens
            )
            
            # Parse reasoning result
            try:
                content = response.content
                # Extract JSON from response (handle markdown code blocks)
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                reasoning_data = json.loads(content.strip())
                reasoning = ReasoningResult.parse(reasoning_data)
                
            except json.JSONDecodeError:
                # Fallback: treat entire response as understanding
                reasoning = ReasoningResult(
                    understanding=response.content,
                    needed_tools=[],
                    approach="Direct implementation based on understanding",
                    needs_clarification=False,
                )
            
            # Update context with reasoning
            context.understanding = reasoning.understanding
            context.approach = reasoning.approach
            context.needed_tools = reasoning.needed_tools
            context.needs_clarification = reasoning.needs_clarification
            context.clarification_question = reasoning.clarification_question
            
            # Check if clarification needed
            if reasoning.needs_clarification:
                self.state_machine.needs_clarification(reasoning.clarification_question or "Clarification needed")
                return
            
            # Transition to PLANNING
            self.state_machine.transition_to(ORPAState.PLANNING, "Reasoning complete")
            
        except Exception as e:
            logger.exception("Reasoning failed")
            self.state_machine.complete(success=False, reason=f"Reasoning error: {e}")
    
    async def _plan(self, context: AgentContext):
        """ORPA: PLAN Phase - Create execution plan.
        
        Creates a detailed plan of which tools to execute
        and in what order.
        """
        logger.debug("ORPA Phase: PLANNING")
        
        try:
            # Build planning prompt
            prompt = self._build_planning_prompt(context)
            
            # Call LLM
            messages = [
                Message(role="system", content=self._get_system_prompt()),
                Message(role="user", content=prompt)
            ]
            
            response = await self.llm.chat(
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens
            )
            
            # Parse execution plan
            try:
                content = response.content
                # Extract JSON
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0]
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0]
                
                plan_data = json.loads(content.strip())
                steps_data = plan_data.get("steps", [])
                
                steps = []
                for i, step_data in enumerate(steps_data, 1):
                    steps.append(ToolExecutionStep(
                        step_number=i,
                        tool_name=step_data.get("tool"),
                        parameters=step_data.get("parameters", {}),
                        description=step_data.get("description", ""),
                        depends_on=step_data.get("depends_on"),
                        condition=step_data.get("condition"),
                    ))
                
                plan = ToolExecutionPlan(
                    steps=steps,
                    estimated_steps=len(steps)
                )
                
            except (json.JSONDecodeError, KeyError) as e:
                logger.warning(f"Failed to parse plan, creating fallback: {e}")
                # Create fallback plan based on understanding
                plan = self._create_fallback_plan(context)
            
            # Update context
            context.execution_plan = plan
            
            # Transition to ACTING
            self.state_machine.transition_to(ORPAState.ACTING, "Planning complete")
            
        except Exception as e:
            logger.exception("Planning failed")
            self.state_machine.complete(success=False, reason=f"Planning error: {e}")
    
    async def _act(self, context: AgentContext):
        """ORPA: ACT Phase - Execute the plan.
        
        Executes tools in sequence, handling errors and
        adapting the plan as needed.
        """
        logger.debug("ORPA Phase: ACTING")
        
        if not context.execution_plan:
            self.state_machine.complete(success=False, reason="No execution plan")
            return
        
        try:
            results = []
            all_success = True
            
            for step in context.execution_plan.steps:
                logger.debug(f"Executing step {step.step_number}: {step.tool_name}")
                
                # Check if tool is allowed
                if not self._is_tool_allowed(step.tool_name):
                    result = ToolExecutionResult(
                        step=step,
                        success=False,
                        error=f"Tool '{step.tool_name}' is not allowed",
                    )
                    results.append(result)
                    all_success = False
                    continue
                
                # Execute tool
                tool_result = await self.executor.execute(
                    tool_name=step.tool_name,
                    parameters=step.parameters,
                    agent_id=self.agent_id,
                    ticket_id=context.ticket.ticket_id
                )
                
                # Record result
                exec_result = ToolExecutionResult(
                    step=step,
                    success=tool_result.success,
                    data=tool_result.data,
                    error=tool_result.error,
                    execution_time_ms=tool_result.execution_time_ms or 0,
                )
                results.append(exec_result)
                
                if not tool_result.success:
                    all_success = False
                    logger.warning(f"Step {step.step_number} failed: {tool_result.error}")
                    
                    # Check if we should continue or abort
                    if step.condition != "continue_on_error":
                        break
            
            # Update context
            context.execution_results = results
            
            # Decide next state
            if all_success:
                self.state_machine.complete(success=True, reason="All steps completed")
            else:
                # Check if we should retry/reason
                if context.iteration < self.config.max_iterations:
                    logger.info("Some steps failed, re-reasoning...")
                    self.state_machine.transition_to(
                        ORPAState.REASONING, 
                        "Some steps failed, re-evaluating"
                    )
                else:
                    self.state_machine.complete(
                        success=False, 
                        reason="Max iterations reached with failures"
                    )
            
        except Exception as e:
            logger.exception("Acting failed")
            self.state_machine.complete(success=False, reason=f"Execution error: {e}")
    
    # ==================================================================
    # PROMPT BUILDERS
    # ==================================================================
    
    def _get_system_prompt(self) -> str:
        """Get the system prompt for the LLM."""
        return f"""Du bist {self.agent_id}, ein KI-Entwickler-Agent für Mohami.

DEINE AUFGABE:
1. Analysiere Tickets und entscheide welche Tools du brauchst
2. Erstelle detaillierte Pläne zur Umsetzung
3. Führe die Pläne aus und adaptiere bei Bedarf

REGELN:
- Antworte auf DEUTSCH
- Sei präzise und technisch korrekt
- Nutze die verfügbaren Tools selbstständig
- Wenn etwas unklar ist, frage nach (needs_clarification: true)

KUNDE: {self.config.customer_id}
AGENT: {self.agent_id}
"""
    
    def _build_reasoning_prompt(
        self, 
        context: AgentContext, 
        tools_schemas: List[Dict]
    ) -> str:
        """Build the prompt for the reasoning phase."""
        
        # Format observations
        observations_text = ""
        if context.repository_structure:
            dirs = context.repository_structure.get("directories", [])[:10]
            files = context.repository_structure.get("files", [])[:10]
            observations_text += f"\nVerzeichnisse: {[d['name'] for d in dirs]}"
            observations_text += f"\nDateien: {[f['name'] for f in files]}"
        
        if context.relevant_files:
            observations_text += f"\nRelevante Dateien: {context.relevant_files[:5]}"
        
        # Format similar learnings
        learnings_text = ""
        if context.relevant_learnings:
            learnings_text = "\n\nÄHNLICHE LÖSUNGEN AUS DER VERGANGENHEIT:\n"
            for learning in context.relevant_learnings[:3]:
                learnings_text += f"- {learning.get('content', '')[:200]}...\n"
        
        prompt = f"""
Analysiere dieses Ticket und entscheide wie du vorgehst.

=== TICKET ===
ID: {context.ticket.ticket_id}
Titel: {context.ticket.title}
Beschreibung:
{context.ticket.description}

=== BEOBACHTUNGEN ===
{observations_text}
{learnings_text}

=== VERFÜGBARE TOOLS ===
{json.dumps(tools_schemas, indent=2, default=str)[:2000]}

=== DEINE AUFGABE ===
1. Analysiere das Ticket: Was will der User?
2. Identifiziere: Welche Tools brauche ich?
3. Entscheide: Was ist der beste Ansatz?

Antworte als JSON:
{{
    "understanding": "Klare Beschreibung was zu tun ist",
    "needed_tools": ["tool_name_1", "tool_name_2"],
    "approach": "Kurze Beschreibung des Vorgehens",
    "needs_clarification": false,
    "clarification_question": null,
    "confidence": 0.9
}}

Wenn etwas unklar ist, setze needs_clarification auf true und stelle eine konkrete Frage.
"""
        return prompt
    
    def _build_planning_prompt(self, context: AgentContext) -> str:
        """Build the prompt for the planning phase."""
        
        prompt = f"""
Erstelle einen detaillierten Ausführungsplan für dieses Ticket.

=== TICKET ===
Titel: {context.ticket.title}
Beschreibung:
{context.ticket.description}

=== DEIN VERSTÄNDNIS ===
{context.understanding}

=== GEPLANTE TOOLS ===
{context.needed_tools}

=== ANSATZ ===
{context.approach}

=== VERFÜGBARE TOOLS ===
{json.dumps(self.tools.get_schemas_for_llm(format="generic"), indent=2, default=str)[:1500]}

=== DEINE AUFGABE ===
Erstelle einen Schritt-für-Schritt Plan mit spezifischen Tool-Aufrufen.

Antworte als JSON:
{{
    "steps": [
        {{
            "step_number": 1,
            "tool": "tool_name",
            "parameters": {{"param1": "value1"}},
            "description": "Was dieser Schritt macht",
            "depends_on": null,
            "condition": null
        }}
    ],
    "estimated_steps": 5
}}

Wichtig:
- Jeder Schritt muss ein verfügbares Tool verwenden
- Parameter müssen zum Tool-Schema passen
- Pfade müssen absolut oder relativ zum Workspace sein
"""
        return prompt
    
    # ==================================================================
    # HELPERS
    # ==================================================================
    
    def _extract_keywords(self, text: str) -> List[str]:
        """Extract keywords from text for file search."""
        # Simple keyword extraction
        # In production, this could use NLP
        words = text.lower().split()
        # Filter common words and technical terms
        tech_terms = [
            w for w in words 
            if len(w) > 3 and 
            w not in ["this", "that", "with", "from", "have", "should", "please"]
        ]
        # Return unique terms
        return list(dict.fromkeys(tech_terms))[:5]
    
    def _is_tool_allowed(self, tool_name: str) -> bool:
        """Check if a tool is allowed for this agent."""
        if self.config.forbidden_tools and tool_name in self.config.forbidden_tools:
            return False
        if self.config.allowed_tools is not None:
            return tool_name in self.config.allowed_tools
        return True
    
    def _create_fallback_plan(self, context: AgentContext) -> ToolExecutionPlan:
        """Create a fallback plan if LLM planning fails."""
        steps = []
        
        # Add basic file exploration steps
        if context.workspace_path:
            steps.append(ToolExecutionStep(
                step_number=1,
                tool_name="file_list",
                parameters={"path": context.workspace_path, "recursive": False},
                description="Explore workspace structure",
            ))
        
        return ToolExecutionPlan(steps=steps)
    
    def _create_result(self, context: AgentContext, success: bool) -> AgentResult:
        """Create the final result."""
        
        # Extract files modified from execution results
        files_modified = []
        for result in context.execution_results:
            if result.success and result.data:
                if isinstance(result.data, dict):
                    path = result.data.get("path")
                    if path:
                        files_modified.append(path)
        
        # Create message based on outcome
        if success:
            message = f"Ticket processed successfully. "
            message += f"Completed in {context.iteration} iterations."
        else:
            if context.needs_clarification:
                message = f"Needs clarification: {context.clarification_question}"
            else:
                message = f"Processing incomplete. Check execution results."
        
        result = AgentResult(
            ticket_id=context.ticket.ticket_id,
            success=success,
            message=message,
            files_modified=files_modified,
            iterations_used=context.iteration,
            final_state=self.state_machine.current_state,
        )
        
        # Record in memory if available
        if self.memory and success:
            episode = LearningEpisode(
                ticket_id=context.ticket.ticket_id,
                problem=context.ticket.description[:200],
                solution=context.understanding[:200],
                success=success,
                episode_type="resolution" if success else "error",
                metadata={
                    "approach": context.approach,
                    "tools_used": context.needed_tools,
                    "iterations": context.iteration,
                }
            )
            self.memory.record_learning(episode)
        
        return result
    
    # ==================================================================
    # UTILITY METHODS
    # ==================================================================
    
    async def execute_tool(
        self, 
        tool_name: str, 
        parameters: Dict[str, Any],
        ticket_id: Optional[str] = None
    ) -> ToolResult:
        """Execute a single tool directly.
        
        This is a convenience method for direct tool execution
        outside of the ORPA workflow.
        
        Args:
            tool_name: Name of the tool to execute
            parameters: Tool parameters
            ticket_id: Optional ticket ID for logging
            
        Returns:
            ToolResult from execution
        """
        return await self.executor.execute(
            tool_name=tool_name,
            parameters=parameters,
            agent_id=self.agent_id,
            ticket_id=ticket_id
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current agent status."""
        return {
            "agent_id": self.agent_id,
            "customer_id": self.config.customer_id,
            "orpa_state": self.state_machine.current_state.value,
            "iteration": self.state_machine.iteration_count,
            "tools_registered": len(self.tools),
            "memory_enabled": self.memory is not None,
            "workspace_enabled": self.workspace is not None,
        }
    
    def __repr__(self) -> str:
        return f"<IntelligentAgent: {self.agent_id}, state={self.state_machine.current_state.value}>"
