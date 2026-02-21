"""Example usage of the IntelligentAgent.

This file demonstrates how to use the new IntelligentAgent
with Tool-Use, Memory, and ORPA workflow.
"""

import asyncio
from .intelligent_agent import IntelligentAgent
from .agent_types import AgentConfig, TicketInfo


async def example_basic_usage():
    """Basic usage example."""
    
    # 1. Create configuration
    config = AgentConfig(
        customer_id="acme-corp",
        max_iterations=5,
        auto_execute=True,
        enable_memory=True,
        enable_workspace=True,
    )
    
    # 2. Create agent
    agent = IntelligentAgent(
        agent_id="dev-agent-001",
        config=config
    )
    
    # 3. Process a ticket
    ticket_data = {
        "title": "Add user authentication",
        "description": "Implement JWT-based authentication for the API endpoints",
        "repository": "acme-api",
        "branch": "feature/auth",
    }
    
    result = await agent.process_ticket(
        ticket_id="ACM-123",
        ticket_data=ticket_data
    )
    
    # 4. Check result
    print(f"Success: {result.success}")
    print(f"Message: {result.message}")
    print(f"Files modified: {result.files_modified}")
    print(f"Iterations: {result.iterations_used}")
    
    return result


async def example_with_progress_callback():
    """Example with progress tracking."""
    
    config = AgentConfig(customer_id="test-corp")
    agent = IntelligentAgent("agent-002", config)
    
    # Register progress callback
    def on_progress(state, context):
        print(f"[{state.value}] Processing {context.ticket.ticket_id}...")
    
    agent.on_progress(on_progress)
    
    # Process ticket
    result = await agent.process_ticket("TEST-456")
    return result


async def example_direct_tool_execution():
    """Example of direct tool execution."""
    
    config = AgentConfig(customer_id="demo-corp")
    agent = IntelligentAgent("agent-003", config)
    
    # Execute a tool directly (outside ORPA workflow)
    result = await agent.execute_tool(
        tool_name="file_list",
        parameters={"path": ".", "recursive": False},
        ticket_id="DEMO-001"
    )
    
    if result.success:
        print(f"Files found: {result.data}")
    else:
        print(f"Error: {result.error}")
    
    return result


async def example_custom_workflow():
    """Example of custom ORPA workflow control."""
    
    from .orpa_states import ORPAStateMachine, ORPAWorkflow, ORPAState
    from .agent_types import AgentContext, TicketInfo
    
    config = AgentConfig(customer_id="custom-corp")
    agent = IntelligentAgent("agent-004", config)
    
    # Create custom workflow
    workflow = ORPAWorkflow(agent.state_machine)
    
    # Register custom handlers
    async def handle_observing(context: AgentContext):
        print("Custom observation logic...")
        # Custom logic here
        agent.state_machine.transition_to(ORPAState.REASONING)
    
    async def handle_reasoning(context: AgentContext):
        print("Custom reasoning logic...")
        # Custom logic here
        agent.state_machine.transition_to(ORPAState.COMPLETED)
    
    workflow.register_handler(ORPAState.OBSERVING, handle_observing)
    workflow.register_handler(ORPAState.REASONING, handle_reasoning)
    
    # Create context
    ticket = TicketInfo(
        ticket_id="CUST-789",
        title="Custom workflow test",
        description="Testing custom workflow handlers",
    )
    context = AgentContext(ticket=ticket)
    
    # Run workflow
    final_state = await workflow.run(context)
    print(f"Workflow completed with state: {final_state}")


# Run examples
if __name__ == "__main__":
    print("=" * 50)
    print("IntelligentAgent Examples")
    print("=" * 50)
    
    # Note: These examples require the full infrastructure to be running
    # (Redis, ChromaDB, LLM API access, etc.)
    
    # asyncio.run(example_basic_usage())
    # asyncio.run(example_with_progress_callback())
    # asyncio.run(example_direct_tool_execution())
    # asyncio.run(example_custom_workflow())
    
    print("\nUncomment the example you want to run.")
    print("Make sure all dependencies are available.")
