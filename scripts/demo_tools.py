#!/usr/bin/env python3
"""Demo script to test the Tool-Use Framework with Developer Agent."""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Load env FIRST before any other imports
load_dotenv(Path(__file__).parent / ".env", override=True)

import asyncio

# Import the Tool-Use Framework
from src.tools import (
    ToolRegistry,
    ToolExecutor,
    FileReadTool,
    FileWriteTool,
    FileListTool,
    GitStatusTool,
    CodeAnalyzeTool,
)
from src.tools.agent_integration import AgentToolManager, ToolCall


async def demo_basic_tools():
    """Demonstrate basic tool usage."""
    print("=" * 60)
    print("🛠️  Tool-Use Framework Demo")
    print("=" * 60)
    
    # Create a registry
    print("\n📦 Creating Tool Registry...")
    registry = ToolRegistry()
    
    # Register tools
    registry.register(FileReadTool(), category="file")
    registry.register(FileWriteTool(), category="file")
    registry.register(FileListTool(), category="file")
    registry.register(GitStatusTool(), category="git")
    registry.register(CodeAnalyzeTool(), category="code")
    
    print(f"✅ Registered {len(registry)} tools")
    print(f"   Categories: {registry.get_categories()}")
    
    # List available tools
    print("\n📋 Available Tools:")
    for tool in registry.list_available():
        print(f"   - {tool.name}: {tool.description[:50]}...")
    
    # Create executor
    print("\n⚙️  Creating Tool Executor...")
    executor = ToolExecutor(registry)
    
    # Demo: Write a file
    print("\n📝 Demo: Write File")
    result = await executor.execute(
        "file_write",
        {
            "path": "/tmp/mohami_test.txt",
            "content": "Hello from Mohami Tool-Use Framework!\n\nThis was created by the ToolUseDeveloperAgent.",
        },
        agent_id="demo-agent",
        ticket_id="demo-ticket"
    )
    
    print(f"   Success: {result.success}")
    if result.success:
        print(f"   Bytes written: {result.data['bytes_written']}")
    else:
        print(f"   Error: {result.error}")
    
    # Demo: Read the file
    print("\n📖 Demo: Read File")
    result = await executor.execute(
        "file_read",
        {"path": "/tmp/mohami_test.txt"},
        agent_id="demo-agent",
        ticket_id="demo-ticket"
    )
    
    print(f"   Success: {result.success}")
    if result.success:
        print(f"   Content preview: {result.data['content'][:50]}...")
    else:
        print(f"   Error: {result.error}")
    
    # Demo: List directory
    print("\n📁 Demo: List Directory")
    result = await executor.execute(
        "file_list",
        {"path": ".", "recursive": False},
        agent_id="demo-agent",
        ticket_id="demo-ticket"
    )
    
    print(f"   Success: {result.success}")
    if result.success:
        print(f"   Files found: {len(result.data['files'])}")
        print(f"   Directories found: {len(result.data['directories'])}")
    
    # Show execution history
    print("\n📊 Execution History:")
    history = executor.get_history()
    for record in history:
        print(f"   - {record.tool_name}: {'✅' if record.result.success else '❌'}")
    
    print("\n" + "=" * 60)
    print("✅ Basic Tools Demo Complete!")
    print("=" * 60)


async def demo_agent_tool_manager():
    """Demonstrate AgentToolManager."""
    print("\n" + "=" * 60)
    print("🤖 Agent Tool Manager Demo")
    print("=" * 60)
    
    # Create manager
    print("\n📦 Creating AgentToolManager...")
    manager = AgentToolManager()
    manager.register_default_tools()
    
    print(f"✅ Registered {len(manager.tool_manager.registry)} default tools")
    
    # Get tools for LLM
    print("\n📋 Tools in OpenAI Format:")
    schemas = manager.get_tools_for_llm("openai")
    for schema in schemas[:3]:  # Show first 3
        print(f"   - {schema['function']['name']}")
    print(f"   ... and {len(schemas) - 3} more")
    
    # Get formatted prompt
    print("\n📝 Formatted Tools Prompt (excerpt):")
    prompt = manager.get_system_prompt_with_tools()
    lines = prompt.split('\n')[:15]
    for line in lines:
        print(f"   {line}")
    print("   ...")
    
    # Demo: Parse tool call from text
    print("\n🔍 Demo: Parse Tool Call from Text")
    text_response = """
    I'll read the file for you.
    
    ```json
    {"tool": "file_read", "parameters": {"path": "/tmp/mohami_test.txt"}}
    ```
    """
    
    tool_calls = manager.parse_tool_calls(text_response, format="text")
    if tool_calls:
        call = tool_calls[0]
        print(f"   Parsed tool call: {call.tool_name}")
        print(f"   Parameters: {call.parameters}")
        
        # Execute the tool call
        result = await manager.execute_tool_call(call, agent_id="demo-agent")
        print(f"   Execution result: {'✅ Success' if result.success else '❌ Failed'}")
        if result.success:
            print(f"   Data: {result.data}")
    else:
        print("   No tool call found in text")
    
    print("\n" + "=" * 60)
    print("✅ Agent Tool Manager Demo Complete!")
    print("=" * 60)


async def demo_code_analysis():
    """Demonstrate code analysis tool."""
    print("\n" + "=" * 60)
    print("💻 Code Analysis Demo")
    print("=" * 60)
    
    registry = ToolRegistry()
    registry.register(CodeAnalyzeTool())
    executor = ToolExecutor(registry)
    
    # Sample Python code to analyze
    sample_code = '''
def calculate_sum(numbers):
    """Calculate sum of numbers."""
    total = 0
    for n in numbers:
        total += n
    return total

class Calculator:
    def __init__(self):
        self.history = []
    
    def add(self, a, b):
        result = a + b
        self.history.append(f"add({a}, {b}) = {result}")
        return result
'''
    
    print("\n🔍 Analyzing Python code...")
    result = await executor.execute(
        "code_analyze",
        {
            "code": sample_code,
            "language": "python",
            "analysis_type": "general"
        }
    )
    
    if result.success:
        data = result.data
        print(f"   Language: {data['language']}")
        print(f"   Lines: {data['lines']}")
        print(f"   Functions: {data['functions']}")
        print(f"   Classes: {data['classes']}")
        print(f"   Imports: {len(data['imports'])}")
        print(f"   Complexity: {data['complexity_score']}")
    else:
        print(f"   Error: {result.error}")
    
    print("\n" + "=" * 60)
    print("✅ Code Analysis Demo Complete!")
    print("=" * 60)


async def main():
    """Run all demos."""
    try:
        await demo_basic_tools()
        await demo_agent_tool_manager()
        await demo_code_analysis()
        
        print("\n" + "=" * 60)
        print("🎉 All Demos Completed Successfully!")
        print("=" * 60)
        print("\n📚 Next Steps:")
        print("   1. Import ToolUseDeveloperAgent from src.agents")
        print("   2. Use it instead of the basic DeveloperAgent")
        print("   3. The agent will dynamically select tools based on tasks")
        print("\n💡 The Tool-Use Framework replaces hardcoded logic with")
        print("   intelligent tool selection by the LLM!")
        
    except Exception as e:
        print(f"\n❌ Demo failed: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(main())
