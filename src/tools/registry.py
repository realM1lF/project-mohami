"""Tool Registry for managing and accessing tools.

Provides a central registry for all available tools.
"""

from typing import Dict, List, Optional, Type

from .base import BaseTool


class ToolRegistry:
    """Registry for managing available tools.
    
    The registry maintains a collection of tools that can be accessed
    by name. It supports registration, lookup, and listing of tools.
    
    Example:
        registry = ToolRegistry()
        registry.register(ReadFileTool(git_provider))
        
        tool = registry.get("read_file")
        tools = registry.list_tools()
    """
    
    def __init__(self):
        """Initialize empty tool registry."""
        self._tools: Dict[str, BaseTool] = {}
    
    def register(self, tool: BaseTool) -> None:
        """Register a tool instance.
        
        Args:
            tool: Tool instance to register
            
        Raises:
            ValueError: If tool with same name already registered
        """
        if tool.name in self._tools:
            raise ValueError(f"Tool '{tool.name}' is already registered")
        
        self._tools[tool.name] = tool
    
    def unregister(self, name: str) -> None:
        """Unregister a tool by name.
        
        Args:
            name: Name of the tool to unregister
        """
        if name in self._tools:
            del self._tools[name]
    
    def get(self, name: str) -> Optional[BaseTool]:
        """Get a tool by name.
        
        Args:
            name: Tool name
            
        Returns:
            Tool instance or None if not found
        """
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all registered tool names.
        
        Returns:
            List of tool names
        """
        return list(self._tools.keys())
    
    def get_all_tools(self) -> List[BaseTool]:
        """Get all registered tool instances.
        
        Returns:
            List of tool instances
        """
        return list(self._tools.values())
    
    def clear(self) -> None:
        """Clear all registered tools."""
        self._tools.clear()
    
    def __contains__(self, name: str) -> bool:
        """Check if a tool is registered.
        
        Args:
            name: Tool name
            
        Returns:
            True if tool is registered
        """
        return name in self._tools
    
    def __len__(self) -> int:
        """Get number of registered tools."""
        return len(self._tools)
