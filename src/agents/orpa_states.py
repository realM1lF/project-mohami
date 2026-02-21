"""ORPA State Machine - Manages the ORPA workflow lifecycle.

ORPA = Observe, Reason, Plan, Act

The state machine handles transitions between states and ensures
the proper flow of the agent's decision-making process.
"""

import logging
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from datetime import datetime

from .agent_types import (
    ORPAState, 
    AgentContext, 
    ReasoningResult, 
    ToolExecutionPlan,
    StateTransitionCallback
)

logger = logging.getLogger(__name__)


class ORPAStateMachine:
    """State machine for ORPA workflow management.
    
    States:
        IDLE → OBSERVING → REASONING → PLANNING → ACTING → COMPLETED
                              ↑__________________________|
                              
    The loop from ACTING can go back to OBSERVING if more information
    is needed, or to REASONING if the plan needs adjustment.
    
    Example:
        machine = ORPAStateMachine()
        machine.start(context)
        
        while machine.is_running:
            state = machine.get_current_state()
            
            if state == ORPAState.OBSERVING:
                # Perform observations
                machine.transition_to(ORPAState.REASONING)
                
            elif state == ORPAState.REASONING:
                # Do reasoning
                machine.transition_to(ORPAState.PLANNING)
                
            # ... etc
    """
    
    # Valid state transitions
    VALID_TRANSITIONS: Dict[ORPAState, List[ORPAState]] = {
        ORPAState.IDLE: [ORPAState.OBSERVING, ORPAState.ERROR],
        ORPAState.OBSERVING: [ORPAState.REASONING, ORPAState.NEEDS_CLARIFICATION, ORPAState.ERROR],
        ORPAState.REASONING: [ORPAState.PLANNING, ORPAState.NEEDS_CLARIFICATION, ORPAState.ERROR],
        ORPAState.PLANNING: [ORPAState.ACTING, ORPAState.REASONING, ORPAState.ERROR],
        ORPAState.ACTING: [
            ORPAState.COMPLETED, 
            ORPAState.OBSERVING,  # Need more info
            ORPAState.REASONING,  # Plan needs adjustment
            ORPAState.PLANNING,   # Create new plan
            ORPAState.ERROR
        ],
        ORPAState.NEEDS_CLARIFICATION: [ORPAState.OBSERVING, ORPAState.ERROR],
        ORPAState.COMPLETED: [ORPAState.IDLE],  # Can restart
        ORPAState.ERROR: [ORPAState.IDLE, ORPAState.OBSERVING],  # Can restart
    }
    
    def __init__(
        self,
        max_iterations: int = 10,
        on_transition: Optional[StateTransitionCallback] = None
    ):
        """Initialize the state machine.
        
        Args:
            max_iterations: Maximum number of ORPA loops before forcing completion
            on_transition: Optional callback for state transitions
        """
        self.max_iterations = max_iterations
        self.on_transition = on_transition
        self._current_state = ORPAState.IDLE
        self._context: Optional[AgentContext] = None
        self._history: List[Dict[str, Any]] = []
        self._iteration_count = 0
        self._state_entry_time: Optional[datetime] = None
        
    @property
    def current_state(self) -> ORPAState:
        """Get the current state."""
        return self._current_state
    
    @property
    def is_running(self) -> bool:
        """Check if the state machine is actively running (not terminal)."""
        return self._current_state not in [
            ORPAState.IDLE, 
            ORPAState.COMPLETED, 
            ORPAState.ERROR
        ]
    
    @property
    def is_terminal(self) -> bool:
        """Check if the state machine is in a terminal state."""
        return self._current_state in [ORPAState.COMPLETED, ORPAState.ERROR]
    
    @property
    def iteration_count(self) -> int:
        """Get the number of completed iterations."""
        return self._iteration_count
    
    def start(self, context: AgentContext) -> bool:
        """Start the ORPA workflow.
        
        Args:
            context: The agent context for this workflow
            
        Returns:
            True if started successfully
        """
        if self._current_state != ORPAState.IDLE:
            logger.warning(f"Cannot start from state {self._current_state}")
            return False
        
        self._context = context
        self._iteration_count = 0
        self._history = []
        
        return self.transition_to(ORPAState.OBSERVING)
    
    def transition_to(self, new_state: ORPAState, reason: str = "") -> bool:
        """Transition to a new state.
        
        Args:
            new_state: The state to transition to
            reason: Optional reason for the transition
            
        Returns:
            True if transition was successful
        """
        old_state = self._current_state
        
        # Validate transition
        if new_state not in self.VALID_TRANSITIONS.get(old_state, []):
            logger.error(
                f"Invalid transition from {old_state.value} to {new_state.value}"
            )
            return False
        
        # Check iteration limit (when looping back to OBSERVING)
        if new_state == ORPAState.OBSERVING and old_state == ORPAState.ACTING:
            self._iteration_count += 1
            if self._iteration_count >= self.max_iterations:
                logger.warning(
                    f"Max iterations ({self.max_iterations}) reached, forcing completion"
                )
                new_state = ORPAState.COMPLETED
        
        # Record history
        self._history.append({
            "from": old_state.value,
            "to": new_state.value,
            "reason": reason,
            "timestamp": datetime.utcnow().isoformat(),
            "iteration": self._iteration_count,
        })
        
        # Perform transition
        self._current_state = new_state
        self._state_entry_time = datetime.utcnow()
        
        # Update context
        if self._context:
            self._context.update_state(new_state)
        
        # Call callback
        if self.on_transition:
            try:
                self.on_transition(old_state, new_state, self._context)
            except Exception as e:
                logger.warning(f"Transition callback failed: {e}")
        
        logger.debug(f"ORPA: {old_state.value} → {new_state.value} ({reason})")
        return True
    
    def get_state_duration(self) -> float:
        """Get the duration in the current state in seconds."""
        if self._state_entry_time is None:
            return 0.0
        return (datetime.utcnow() - self._state_entry_time).total_seconds()
    
    def get_history(self) -> List[Dict[str, Any]]:
        """Get the transition history."""
        return self._history.copy()
    
    def can_transition_to(self, state: ORPAState) -> bool:
        """Check if a transition to the given state is valid."""
        return state in self.VALID_TRANSITIONS.get(self._current_state, [])
    
    def get_valid_next_states(self) -> List[ORPAState]:
        """Get list of valid next states."""
        return self.VALID_TRANSITIONS.get(self._current_state, []).copy()
    
    def complete(self, success: bool = True, reason: str = "") -> bool:
        """Complete the workflow.
        
        Args:
            success: Whether the workflow completed successfully
            reason: Reason for completion
            
        Returns:
            True if transition was successful
        """
        target_state = ORPAState.COMPLETED if success else ORPAState.ERROR
        return self.transition_to(target_state, reason)
    
    def needs_clarification(self, question: str) -> bool:
        """Signal that clarification is needed.
        
        Args:
            question: The clarification question
            
        Returns:
            True if transition was successful
        """
        if self._context:
            self._context.needs_clarification = True
            self._context.clarification_question = question
        
        return self.transition_to(
            ORPAState.NEEDS_CLARIFICATION, 
            f"Needs clarification: {question[:50]}..."
        )
    
    def reset(self):
        """Reset the state machine to idle."""
        self._current_state = ORPAState.IDLE
        self._context = None
        self._history = []
        self._iteration_count = 0
        self._state_entry_time = None
        logger.debug("ORPA state machine reset")
    
    def __repr__(self) -> str:
        return f"<ORPAStateMachine: {self._current_state.value}, iter={self._iteration_count}>"


class ORPAWorkflow:
    """High-level ORPA workflow manager.
    
    Combines the state machine with the actual processing logic.
    This class provides the glue between states and actions.
    """
    
    def __init__(
        self,
        state_machine: Optional[ORPAStateMachine] = None,
        max_iterations: int = 10
    ):
        """Initialize the workflow.
        
        Args:
            state_machine: Optional pre-configured state machine
            max_iterations: Max iterations if creating new state machine
        """
        self.state_machine = state_machine or ORPAStateMachine(max_iterations=max_iterations)
        self._handlers: Dict[ORPAState, Callable[[AgentContext], Any]] = {}
        
    def register_handler(
        self, 
        state: ORPAState, 
        handler: Callable[[AgentContext], Any]
    ):
        """Register a handler for a state.
        
        Args:
            state: The state to handle
            handler: Function(context) -> result
        """
        self._handlers[state] = handler
        
    async def run(self, context: AgentContext) -> ORPAState:
        """Run the complete ORPA workflow.
        
        This runs the workflow until a terminal state is reached.
        
        Args:
            context: The agent context
            
        Returns:
            The final state (COMPLETED or ERROR)
        """
        self.state_machine.start(context)
        
        while not self.state_machine.is_terminal:
            current_state = self.state_machine.current_state
            
            # Get handler for current state
            handler = self._handlers.get(current_state)
            if handler is None:
                logger.error(f"No handler registered for state {current_state}")
                self.state_machine.complete(success=False, reason="No handler for state")
                break
            
            # Execute handler
            try:
                result = await handler(context)
                
                # Handler should determine next state
                # Default transitions if handler returns nothing
                if result is None:
                    await self._default_transition(current_state, context)
                    
            except Exception as e:
                logger.exception(f"Handler for {current_state} failed")
                self.state_machine.complete(success=False, reason=f"Handler error: {e}")
                break
        
        return self.state_machine.current_state
    
    async def _default_transition(self, state: ORPAState, context: AgentContext):
        """Default state transitions if handler returns nothing."""
        transitions = {
            ORPAState.OBSERVING: ORPAState.REASONING,
            ORPAState.REASONING: ORPAState.PLANNING,
            ORPAState.PLANNING: ORPAState.ACTING,
            ORPAState.ACTING: ORPAState.COMPLETED,
        }
        
        if state in transitions:
            self.state_machine.transition_to(
                transitions[state], 
                "Default transition"
            )
    
    def get_state(self) -> ORPAState:
        """Get current workflow state."""
        return self.state_machine.current_state
