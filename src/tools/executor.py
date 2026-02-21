"""Tool Executor for running tools with validation.

Provides execution logic with parameter validation and error handling.
"""

from typing import Any, Dict, Optional

from .base import BaseTool, ToolResult
from .registry import ToolRegistry


class ToolExecutor:
    """Executor for running tools with validation.
    
    The executor handles tool invocation, parameter validation,
    and error handling. It works with a ToolRegistry to find
    and execute tools.
    
    Example:
        registry = ToolRegistry()
        registry.register(ReadFileTool(git_provider))
        
        executor = ToolExecutor(registry)
        result = await executor.execute("read_file", {
            "repo": "owner/repo",
            "path": "README.md"
        })
    """
    
    def __init__(self, registry: Optional[ToolRegistry] = None):
        """Initialize with optional registry.
        
        Args:
            registry: Tool registry to use (creates empty one if None)
        """
        self.registry = registry or ToolRegistry()
    
    async def execute(self, tool_name: str, params: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name with parameters.
        
        Args:
            tool_name: Name of the tool to execute
            params: Parameters to pass to the tool
            
        Returns:
            ToolResult from tool execution
        """
        # Find tool
        tool = self.registry.get(tool_name)
        if not tool:
            return ToolResult.error_result(
                error=f"Tool '{tool_name}' not found",
                data={"available_tools": self.registry.list_tools()}
            )
        
        # Validate parameters
        validation_error = tool.validate_params(params)
        if validation_error:
            return ToolResult.error_result(
                error=validation_error,
                data={
                    "tool": tool_name,
                    "provided_params": list(params.keys()),
                    "expected_params": [p.name for p in tool.parameters]
                }
            )
        
        # Execute tool
        try:
            result = await tool.run(**params)
            return result
        except Exception as e:
            return ToolResult.error_result(
                error=f"Tool execution failed: {str(e)}",
                data={"tool": tool_name, "params": params}
            )
    
    def get_tool_schema(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get OpenAI function schema for a tool.
        
        Args:
            tool_name: Name of the tool
            
        Returns:
            OpenAI function schema dict or None if tool not found
        """
        tool = self.registry.get(tool_name)
        if tool:
            return tool.to_openai_function()
        return None
    
    def get_all_schemas(self) -> list:
        """Get OpenAI function schemas for all tools.
        
        Returns:
            List of OpenAI function schema dicts
        """
        schemas = []
        for tool_name in self.registry.list_tools():
            tool = self.registry.get(tool_name)
            if tool:
                schemas.append(tool.to_openai_function())
        return schemas
