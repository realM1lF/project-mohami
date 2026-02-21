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
    from ..tools.code_tools import CodeAnalyzeTool, CodeRefactorTool, CodeGenerateTool
    from ..tools.git_tools import (
        GitStatusTool, GitCommitTool,
        GitHubReadFileTool, GitHubWriteFileTool, GitHubListFilesTool,
        GitHubCreateBranchTool, GitHubGetRepoInfoTool, GitHubCreatePRTool,
    )
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
    from ..agent_config import AgentConfigLoader
    IDENTITY_AVAILABLE = True
except ImportError:
    IDENTITY_AVAILABLE = False

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
    
    def __init__(self, agent_id: str, config: AgentConfig, ticket_crud=None, comment_crud=None, git_provider=None):
        """Initialize the IntelligentAgent.
        
        Args:
            agent_id: Unique identifier for this agent
            config: Agent configuration
            ticket_crud: Optional TicketCRUD for status updates
            comment_crud: Optional CommentCRUD for posting comments
            git_provider: Optional GitProvider for GitHub API operations
            
        Raises:
            RuntimeError: If required dependencies are not available
        """
        self.agent_id = agent_id
        self.config = config
        self.ticket_crud = ticket_crud
        self.comment_crud = comment_crud
        self.git_provider = git_provider
        
        # === 0. IDENTITY laden (aus agents/{agent_id}/) ===
        self.identity_prompt = None
        self.knowledge = ""
        self.memories = ""
        self._config_loader = None
        
        if IDENTITY_AVAILABLE:
            try:
                loader = AgentConfigLoader("./agents")
                identity = loader.load_config(agent_id)
                self.identity_prompt = identity.system_prompt
                self.knowledge = identity.knowledge
                self.memories = identity.memories
                self._config_loader = loader
                print(f"   🧬 Identity loaded: soul + rules + knowledge ({len(self.knowledge)} chars) + memories ({len(self.memories)} chars)")
            except Exception as e:
                logger.warning(f"Could not load agent identity from agents/{agent_id}/: {e}")
        else:
            logger.warning("agent_config module not available, using default identity")
        
        # Check dependencies
        if not TOOLS_AVAILABLE:
            raise RuntimeError("Tools module not available")
        if not LLM_AVAILABLE:
            raise RuntimeError("LLM module not available")
        
        # === 1. LLM Client (before tools, since CodeGenerateTool needs it) ===
        self.llm = KimiClient()
        
        # === 2. TOOLS initialisieren ===
        self.tools = ToolRegistry()
        self._register_all_tools()
        self.executor = ToolExecutor(self.tools, log_executions=True)
        
        # === 3. MEMORY initialisieren ===
        if config.enable_memory and MEMORY_AVAILABLE:
            self.memory = UnifiedMemoryManager(
                customer_id=config.customer_id,
                config=None  # Use defaults
            )
        else:
            self.memory = None
            if config.enable_memory:
                logger.warning("Memory enabled but module not available")
        
        # === 4. WORKSPACE initialisieren ===
        if config.enable_workspace and WORKSPACE_AVAILABLE:
            self.workspace = get_workspace_manager()
            self.repo_manager = get_repository_manager()
        else:
            self.workspace = None
            self.repo_manager = None
            if config.enable_workspace:
                logger.warning("Workspace enabled but module not available")
        
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
        # File tools (core -- must succeed)
        self.tools.register(FileReadTool(), category="file")
        self.tools.register(FileWriteTool(), category="file")
        self.tools.register(FileListTool(), category="file")
        self.tools.register(FileSearchTool(), category="file")
        
        # Code tools (each registered individually so one failure doesn't block others)
        for tool_factory, name in [
            (lambda: CodeAnalyzeTool(), "CodeAnalyzeTool"),
            (lambda: CodeRefactorTool(), "CodeRefactorTool"),
            (lambda: CodeGenerateTool(llm_client=self.llm), "CodeGenerateTool"),
        ]:
            try:
                self.tools.register(tool_factory(), category="code")
            except Exception as e:
                logger.warning(f"Failed to register {name}: {e}")
        
        # Local git tools
        for tool_factory, name in [
            (lambda: GitStatusTool(), "GitStatusTool"),
            (lambda: GitCommitTool(), "GitCommitTool"),
        ]:
            try:
                self.tools.register(tool_factory(), category="git")
            except Exception as e:
                logger.warning(f"Failed to register {name}: {e}")
        
        # GitHub API tools (remote operations via git_provider)
        if self.git_provider:
            gp = self.git_provider
            for tool_factory, name in [
                (lambda: GitHubReadFileTool(git_provider=gp), "GitHubReadFileTool"),
                (lambda: GitHubWriteFileTool(git_provider=gp), "GitHubWriteFileTool"),
                (lambda: GitHubListFilesTool(git_provider=gp), "GitHubListFilesTool"),
                (lambda: GitHubCreateBranchTool(git_provider=gp), "GitHubCreateBranchTool"),
                (lambda: GitHubGetRepoInfoTool(git_provider=gp), "GitHubGetRepoInfoTool"),
                (lambda: GitHubCreatePRTool(git_provider=gp), "GitHubCreatePRTool"),
            ]:
                try:
                    self.tools.register(tool_factory(), category="github")
                except Exception as e:
                    logger.warning(f"Failed to register {name}: {e}")
        else:
            logger.warning("No git_provider - GitHub API tools not available")
        
        logger.info(f"Registered {len(self.tools)} tools")
    
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
                print("   📝 Loading memory context...")
                try:
                    memory_context = self.memory.build_agent_context(
                        ticket_id=ticket_id,
                        ticket_description=ticket.description
                    )
                    context.relevant_learnings = memory_context.get("relevant_learnings", [])
                    context.similar_tickets = memory_context.get("recent_learnings", [])
                    context.chat_history = memory_context.get("chat_history", [])
                    print(f"   📝 Memory loaded: {len(context.relevant_learnings)} learnings, {len(context.similar_tickets)} similar")
                except Exception as e:
                    print(f"   ⚠️  Memory load failed (continuing): {e}")
            
            # Start ORPA workflow
            print("   🔄 Starting ORPA state machine...")
            self.state_machine.reset()
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
                    return self._create_result(context, success=False)
                    
                elif state == ORPAState.ERROR:
                    await self._post_comment(
                        context.ticket.ticket_id,
                        f"❌ Fehler bei der Verarbeitung. Ich schaue mir das nochmal an."
                    )
                    return self._create_result(context, success=False)
            
            # Workflow completed successfully
            files = [r.data.get("path", "") for r in context.execution_results if r.success and r.data and isinstance(r.data, dict)]
            files_text = "\n".join(f"- `{f}`" for f in files if f) if files else "- (keine Dateien geändert)"
            await self._post_comment(
                context.ticket.ticket_id,
                f"✅ **Fertig!**\n\n"
                f"**Verständnis:** {context.understanding[:200]}\n\n"
                f"**Geänderte Dateien:**\n{files_text}"
            )
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
        print("   👁️  ORPA Phase: OBSERVING")
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
                workspace_path = self.repo_manager.get_workspace_path(context.ticket.customer_id)
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
                        workspace_path = self.repo_manager.get_workspace_path(context.ticket.customer_id)
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
                print("      Memory: searching similar solutions...")
                similar = self.memory.find_solutions(context.ticket.description, limit=3)
                if similar:
                    context.relevant_learnings = similar
                    context.add_observation("similar_solutions", similar)
                    print(f"      Memory: found {len(similar)} similar solutions")
                else:
                    print("      Memory: no similar solutions found")
            
            # Transition to REASONING
            print("   👁️  OBSERVE complete")
            self.state_machine.transition_to(ORPAState.REASONING, "Observation complete")
            
        except Exception as e:
            print(f"   ❌ Observation failed: {e}")
            logger.exception("Observation failed")
            self.state_machine.complete(success=False, reason=f"Observation error: {e}")
    
    async def _reason(self, context: AgentContext):
        """ORPA: REASON Phase - Analyze and decide.
        
        The LLM analyzes:
        - What the user wants
        - Which tools are needed
        - The approach to take
        """
        print("   🧠 ORPA Phase: REASONING")
        logger.debug("ORPA Phase: REASONING")
        
        try:
            # Get tool schemas for LLM
            tools_schemas = self.tools.get_schemas_for_llm(format="openai")
            
            # Build reasoning prompt
            prompt = self._build_reasoning_prompt(context, tools_schemas)
            
            # Call LLM
            system_prompt = self._get_system_prompt(context)
            print(f"      System prompt: {len(system_prompt)} chars")
            print(f"      User prompt: {len(prompt)} chars")
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=prompt)
            ]
            
            print("      Calling LLM (Kimi 2.5)...")
            response = await self.llm.chat(
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens
            )
            print(f"      LLM response: {len(response.content)} chars, tokens: {response.usage}")
            
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
                question = reasoning.clarification_question or "Ich habe eine Rückfrage zu diesem Ticket."
                await self._post_comment(
                    context.ticket.ticket_id,
                    f"❓ {question}\n\nBitte antworte hier, dann mache ich weiter."
                )
                self.state_machine.needs_clarification(question)
                return
            
            # Transition to PLANNING
            print(f"   🧠 REASON complete: {context.understanding[:100]}")
            self.state_machine.transition_to(ORPAState.PLANNING, "Reasoning complete")
            
        except Exception as e:
            print(f"   ❌ Reasoning failed: {e}")
            logger.exception("Reasoning failed")
            self.state_machine.complete(success=False, reason=f"Reasoning error: {e}")
    
    async def _plan(self, context: AgentContext):
        """ORPA: PLAN Phase - Create execution plan.
        
        Creates a detailed plan of which tools to execute
        and in what order.
        """
        print("   📋 ORPA Phase: PLANNING")
        logger.debug("ORPA Phase: PLANNING")
        
        try:
            # Build planning prompt
            prompt = self._build_planning_prompt(context)
            
            # Call LLM
            system_prompt = self._get_system_prompt(context)
            messages = [
                Message(role="system", content=system_prompt),
                Message(role="user", content=prompt)
            ]
            
            print(f"      Calling LLM for plan ({len(prompt)} chars prompt)...")
            response = await self.llm.chat(
                messages=messages,
                temperature=self.config.llm_temperature,
                max_tokens=self.config.llm_max_tokens
            )
            print(f"      LLM plan response: {len(response.content)} chars")
            
            # Parse execution plan
            plan = self._parse_plan_response(response.content, context)
            
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
        logger.warning("ORPA Phase: ACTING - %d steps planned", 
                       len(context.execution_plan.steps) if context.execution_plan else 0)
        
        if not context.execution_plan or not context.execution_plan.steps:
            print("   ⚠️  No execution plan or 0 steps - failing")
            self.state_machine.complete(success=False, reason="No execution plan or empty plan")
            return
        
        try:
            results = []
            all_success = True
            
            for step in context.execution_plan.steps:
                print(f"   🔧 Step {step.step_number}: {step.tool_name} ({step.description})")
                
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
                
                # Resolve __GENERATE__ placeholders in parameters
                params = dict(step.parameters)
                for key, value in params.items():
                    if value == "__GENERATE__":
                        print(f"      Generating content for '{key}'...")
                        params[key] = await self._generate_content(context, step)
                        print(f"      Generated {len(params[key])} chars")
                
                # Execute tool
                tool_result = await self.executor.execute(
                    tool_name=step.tool_name,
                    parameters=params,
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
                
                if tool_result.success:
                    print(f"      ✓ Success: {str(tool_result.data)[:150]}")
                else:
                    all_success = False
                    print(f"      ✗ Failed: {tool_result.error}")
                    
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
    
    def _get_system_prompt(self, context: Optional[AgentContext] = None) -> str:
        """Build the system prompt from identity files + operational rules.
        
        Layers (in order of LLM weight):
        1. Identity (soul.md + rules.md) -- who am I, what are my constraints
        2. Operational workflow -- how to use tools, PR workflow
        3. Knowledge (knowledge.md) -- what do I know about my tech stack
        4. Memories (memories/*.md) -- curated learnings from the operator
        5. Customer context (customers/{id}/) -- per-customer specifics
        6. Session metadata -- customer_id, agent_id
        """
        customer_id = (
            context.ticket.customer_id if context and context.ticket.customer_id
            else self.config.customer_id
        )
        
        parts = []
        
        # --- Layer 1: Identity (from soul.md + rules.md) ---
        if self.identity_prompt:
            parts.append(self.identity_prompt)
        else:
            parts.append(f"Du bist {self.agent_id}, ein KI-Entwickler-Agent.")
        
        # --- Layer 2: Operational workflow (hardcoded system logic) ---
        parts.append("""DEINE AUFGABE:
1. Analysiere Tickets und entscheide welche Tools du brauchst
2. Erstelle detaillierte Pläne zur Umsetzung
3. Führe die Pläne aus und adaptiere bei Bedarf

PFLICHT-WORKFLOW FÜR CODE-ÄNDERUNGEN:
Jede Code-Änderung MUSS über einen Pull Request laufen. Folge IMMER diesem Workflow:
1. github_get_repo_info → Default-Branch ermitteln
2. github_create_branch → Feature-Branch erstellen (Name: "mohami/ticket-<kurzer-name>")
3. github_write_file → Dateien auf den Feature-Branch schreiben (jeweils mit commit message)
4. github_create_pr → Pull Request vom Feature-Branch zum Default-Branch erstellen

Nutze NIEMALS file_write für Änderungen an Kunden-Repositories. file_write ist NUR für temporäre lokale Dateien.
Wenn etwas unklar ist, frage nach (needs_clarification: true).""")
        
        # --- Layer 3: Knowledge (from knowledge.md) ---
        if self.knowledge:
            parts.append(f"## DEIN WISSEN\n{self.knowledge[:3000]}")
        
        # --- Layer 4: Memories (from memories/*.md) ---
        if self.memories:
            parts.append(f"## DEINE ERINNERUNGEN\n{self.memories[:2000]}")
        
        # --- Layer 5: Customer context (from customers/{id}/) ---
        if context and context.ticket.customer_id and self._config_loader:
            try:
                customer_ctx = self._config_loader.load_customer_context(
                    self.agent_id, context.ticket.customer_id
                )
                if customer_ctx:
                    parts.append(f"## KUNDENKONTEXT ({context.ticket.customer_id})\n{customer_ctx[:1500]}")
            except Exception as e:
                logger.debug(f"Could not load customer context: {e}")
        
        # --- Layer 6: Session metadata ---
        parts.append(f"KUNDE: {customer_id}\nAGENT: {self.agent_id}")
        
        return "\n\n".join(parts)
    
    def _build_reasoning_prompt(
        self, 
        context: AgentContext, 
        tools_schemas: Optional[List[Dict]] = None
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
        
        repo_text = f"Repository: {context.ticket.repository}" if context.ticket.repository else "Repository: (nicht angegeben)"
        
        prompt = f"""
Analysiere dieses Ticket und entscheide wie du vorgehst.

=== TICKET ===
ID: {context.ticket.ticket_id}
Titel: {context.ticket.title}
{repo_text}
Kunde: {context.ticket.customer_id or "unbekannt"}
Beschreibung:
{context.ticket.description}

=== BEOBACHTUNGEN ===
{observations_text}
{learnings_text}

=== VERFÜGBARE TOOLS ===
{self.tools.get_formatted_tools_prompt()}

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
Erstelle einen Ausführungsplan für dieses Ticket.

=== TICKET ===
Titel: {context.ticket.title}
Beschreibung: {context.ticket.description}

=== VERSTÄNDNIS ===
{context.understanding}

=== ANSATZ ===
{context.approach}

=== VERFÜGBARE TOOLS ===
{self.tools.get_formatted_tools_prompt()}

=== AUFGABE ===
Erstelle einen JSON-Plan mit Tool-Aufrufen.

PFLICHT-WORKFLOW für Code-Änderungen:
1. github_get_repo_info → Default-Branch ermitteln
2. github_create_branch → Feature-Branch "mohami/ticket-<name>"
3. github_write_file → Dateien schreiben (EINE Datei pro Step)
4. github_create_pr → Pull Request erstellen

KRITISCHE JSON-REGELN:
- Für "content" Parameter (Dateiinhalte): Nutze den Platzhalter "__GENERATE__"
- Beschreibe in "description" WAS der Inhalt sein soll
- Der tatsächliche Inhalt wird automatisch generiert
- Nutze github_write_file (NICHT file_write) für Repository-Änderungen
- Repository: {context.ticket.repository}

Antworte NUR mit diesem JSON (keine Erklärung):
```json
{{
    "steps": [
        {{
            "step_number": 1,
            "tool": "github_get_repo_info",
            "parameters": {{"repo": "{context.ticket.repository}"}},
            "description": "Default-Branch ermitteln"
        }},
        {{
            "step_number": 2,
            "tool": "github_create_branch",
            "parameters": {{"repo": "{context.ticket.repository}", "branch_name": "mohami/ticket-beispiel", "from_branch": "main"}},
            "description": "Feature-Branch erstellen"
        }},
        {{
            "step_number": 3,
            "tool": "github_write_file",
            "parameters": {{"repo": "{context.ticket.repository}", "path": "datei.md", "content": "__GENERATE__", "branch": "mohami/ticket-beispiel", "message": "Add datei.md"}},
            "description": "Datei mit XYZ Inhalt erstellen"
        }},
        {{
            "step_number": 4,
            "tool": "github_create_pr",
            "parameters": {{"repo": "{context.ticket.repository}", "title": "Ticket: Beschreibung", "body": "...", "head_branch": "mohami/ticket-beispiel", "base_branch": "main"}},
            "description": "Pull Request erstellen"
        }}
    ]
}}
```
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
    
    async def _generate_content(self, context: AgentContext, step: ToolExecutionStep) -> str:
        """Generate file content via LLM for __GENERATE__ placeholders.
        
        Reads existing file from GitHub first (if it exists) so the LLM
        can modify rather than replace.
        """
        file_path = step.parameters.get("path", "unknown")
        repo = step.parameters.get("repo", context.ticket.repository)
        branch = step.parameters.get("branch", "main")
        
        existing_content = ""
        if repo:
            try:
                read_result = await self.executor.execute(
                    "github_read_file",
                    {"repo": repo, "path": file_path, "branch": branch},
                    agent_id=self.agent_id,
                    ticket_id=context.ticket.ticket_id,
                )
                if read_result.success and read_result.data:
                    existing_content = read_result.data.get("content", "")
                    print(f"      Read existing file: {len(existing_content)} chars")
            except Exception:
                pass
        
        existing_section = ""
        if existing_content:
            existing_section = f"""
BESTEHENDER INHALT der Datei (MUSS beibehalten werden, nur ergänzen/anpassen):
---
{existing_content}
---
WICHTIG: Behalte den bestehenden Inhalt bei und passe ihn nur gemäß der Aufgabe an."""
        else:
            existing_section = "\nDie Datei existiert noch nicht. Erstelle sie komplett neu."
        
        prompt = f"""Generiere den KOMPLETTEN Inhalt für die Datei '{file_path}'.

Ticket: {context.ticket.title}
Beschreibung: {context.ticket.description}
Repository: {context.ticket.repository}
Step-Beschreibung: {step.description}

Verständnis: {context.understanding[:300] if context.understanding else ''}
{existing_section}

Antworte NUR mit dem Dateiinhalt. Keine Erklärung, kein Markdown-Code-Block, nur den reinen Inhalt der Datei."""
        
        try:
            messages = [
                Message(role="system", content="Du bist ein Entwickler. Generiere NUR den angeforderten Dateiinhalt. Keine Erklärungen. Wenn eine bestehende Datei angegeben ist, behalte deren Inhalt bei und ergänze/ändere nur was nötig ist."),
                Message(role="user", content=prompt),
            ]
            response = await self.llm.chat(messages=messages, temperature=0.3, max_tokens=4096)
            content = response.content.strip()
            if content.startswith("```"):
                lines = content.split("\n")
                content = "\n".join(lines[1:])
                if content.endswith("```"):
                    content = content[:-3].rstrip()
            return content
        except Exception as e:
            print(f"      ⚠️  Content generation failed: {e}")
            return f"# {context.ticket.title}\n\nContent generation failed. Please edit manually."
    
    def _parse_plan_response(self, raw_response: str, context: AgentContext) -> ToolExecutionPlan:
        """Parse the LLM plan response with robust JSON handling."""
        import re
        
        content = raw_response
        
        # Extract JSON from markdown code blocks
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0]
        elif "```" in content:
            parts = content.split("```")
            if len(parts) >= 3:
                content = parts[1]
        
        # Try direct parse first
        try:
            plan_data = json.loads(content.strip())
            return self._build_plan_from_data(plan_data)
        except json.JSONDecodeError:
            pass
        
        # Try to repair: replace unescaped newlines inside strings
        try:
            repaired = re.sub(r'(?<=": ")([^"]*?)(?=")', 
                            lambda m: m.group(0).replace('\n', '\\n'), 
                            content)
            plan_data = json.loads(repaired.strip())
            print("      JSON repaired successfully")
            return self._build_plan_from_data(plan_data)
        except (json.JSONDecodeError, re.error):
            pass
        
        # Try to extract individual step objects via regex
        try:
            step_pattern = r'\{[^{}]*"tool"\s*:\s*"([^"]+)"[^{}]*"parameters"\s*:\s*(\{[^{}]*\})[^{}]*"description"\s*:\s*"([^"]*)"[^{}]*\}'
            matches = re.findall(step_pattern, raw_response, re.DOTALL)
            if matches:
                steps = []
                for i, (tool, params_str, desc) in enumerate(matches, 1):
                    try:
                        params = json.loads(params_str)
                    except json.JSONDecodeError:
                        params = {}
                    steps.append(ToolExecutionStep(
                        step_number=i, tool_name=tool,
                        parameters=params, description=desc,
                    ))
                print(f"      Extracted {len(steps)} steps via regex")
                return ToolExecutionPlan(steps=steps, estimated_steps=len(steps))
        except Exception:
            pass
        
        # Last resort: build a standard GitHub workflow plan from context
        print("      ⚠️  All parsing failed, creating standard GitHub workflow plan")
        return self._create_standard_github_plan(context)
    
    def _build_plan_from_data(self, plan_data: dict) -> ToolExecutionPlan:
        """Build a ToolExecutionPlan from parsed JSON data."""
        steps_data = plan_data.get("steps", [])
        print(f"   📋 Plan: {len(steps_data)} steps")
        for s in steps_data:
            print(f"      → {s.get('tool', '?')}: {s.get('description', '')[:80]}")
        
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
        return ToolExecutionPlan(steps=steps, estimated_steps=len(steps))
    
    def _create_standard_github_plan(self, context: AgentContext) -> ToolExecutionPlan:
        """Create a standard GitHub workflow plan as last-resort fallback."""
        repo = context.ticket.repository
        if not repo:
            return ToolExecutionPlan(steps=[])
        
        branch_name = f"mohami/ticket-{context.ticket.ticket_id[:8]}"
        title_slug = context.ticket.title.lower().replace(" ", "-")[:30]
        
        steps = [
            ToolExecutionStep(
                step_number=1, tool_name="github_get_repo_info",
                parameters={"repo": repo},
                description="Default-Branch ermitteln",
            ),
            ToolExecutionStep(
                step_number=2, tool_name="github_create_branch",
                parameters={"repo": repo, "branch_name": branch_name, "from_branch": "main"},
                description="Feature-Branch erstellen",
            ),
            ToolExecutionStep(
                step_number=3, tool_name="github_write_file",
                parameters={
                    "repo": repo, "path": f"{title_slug}.md",
                    "content": "__GENERATE__", "branch": branch_name,
                    "message": f"Add {context.ticket.title}",
                },
                description=f"Datei erstellen: {context.ticket.title}",
            ),
            ToolExecutionStep(
                step_number=4, tool_name="github_create_pr",
                parameters={
                    "repo": repo, "title": f"Mohami: {context.ticket.title}",
                    "body": context.understanding[:500] if context.understanding else context.ticket.description,
                    "head_branch": branch_name, "base_branch": "main",
                },
                description="Pull Request erstellen",
            ),
        ]
        print(f"   📋 Fallback Plan: {len(steps)} steps (standard GitHub workflow)")
        return ToolExecutionPlan(steps=steps, estimated_steps=len(steps))
    
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
                    "tools_used": ",".join(context.needed_tools) if context.needed_tools else "",
                    "iterations": context.iteration,
                }
            )
            self.memory.record_learning(episode)
        
        return result
    
    # ==================================================================
    # KANBAN INTEGRATION
    # ==================================================================
    
    async def _post_comment(self, ticket_id: str, content: str):
        """Post a comment to a ticket if CommentCRUD is available."""
        if not self.comment_crud:
            logger.debug(f"No comment_crud, skipping comment on {ticket_id}")
            return
        try:
            from ..kanban.schemas import CommentCreate
            comment = CommentCreate(author=self.agent_id, content=content)
            await self.comment_crud.create(ticket_id, comment)
        except Exception as e:
            logger.warning(f"Failed to post comment: {e}")
    
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
