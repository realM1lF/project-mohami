"""Base classes for Tool Framework.

Provides the foundation for tool-based AI interactions,
following the OpenAI Function Calling pattern.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Type
import json


class ToolParameterType(Enum):
    """Supported parameter types for tools."""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


@dataclass
class ToolParameter:
    """Definition of a tool parameter."""
    name: str
    description: str
    type: ToolParameterType
    required: bool = True
    enum: Optional[List[str]] = None
    default: Any = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to OpenAI function parameter format."""
        result = {
            "type": self.type.value,
            "description": self.description,
        }
        if self.enum:
            result["enum"] = self.enum
        if self.default is not None:
            result["default"] = self.default
        return result


@dataclass
class ToolResult:
    """Result of a tool execution."""
    success: bool
    data: Any = None
    error: Optional[str] = None
    message: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format."""
        return {
            "success": self.success,
            "data": self.data,
            "error": self.error,
            "message": self.message
        }
    
    def to_json(self) -> str:
        """Convert to JSON string."""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)
    
    @classmethod
    def success_result(cls, data: Any = None, message: Optional[str] = None) -> "ToolResult":
        """Create a successful result."""
        return cls(success=True, data=data, message=message)
    
    @classmethod
    def error_result(cls, error: str, data: Any = None) -> "ToolResult":
        """Create an error result."""
        return cls(success=False, error=error, data=data)


class BaseTool(ABC):
    """Abstract base class for all tools.
    
    Tools are the primary way for AI agents to interact with external systems.
    Each tool has a name, description, parameters, and an async run method.
    
    Example:
        class MyTool(BaseTool):
            name = "my_tool"
            description = "Does something useful"
            parameters = [
                ToolParameter("input", "The input", ToolParameterType.STRING)
            ]
            
            async def run(self, input: str) -> ToolResult:
                return ToolResult.success_result(data={"output": input.upper()})
    """
    
    # Tool metadata - override in subclass
    name: str = ""
    description: str = ""
    parameters: List[ToolParameter] = field(default_factory=list)
    
    def __init__(self, git_provider=None):
        """Initialize the tool with optional git provider."""
        self.git = git_provider
    
    @abstractmethod
    async def run(self, **kwargs) -> ToolResult:
        """Execute the tool with the given parameters.
        
        Args:
            **kwargs: Parameters as defined in self.parameters
            
        Returns:
            ToolResult with success/failure status and data
        """
        pass
    
    def validate_params(self, params: Dict[str, Any]) -> Optional[str]:
        """Validate parameters against the tool's parameter definitions.
        
        Args:
            params: Dictionary of parameter names to values
            
        Returns:
            Error message if validation fails, None if valid
        """
        for param in self.parameters:
            if param.required and param.name not in params:
                return f"Required parameter '{param.name}' is missing"
            
            if param.name in params and param.enum:
                value = params[param.name]
                if value not in param.enum:
                    return f"Parameter '{param.name}' must be one of: {param.enum}"
        
        return None
    
    def to_openai_function(self) -> Dict[str, Any]:
        """Convert tool to OpenAI function format.
        
        Returns:
            Dictionary in OpenAI function calling format
        """
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = param.to_dict()
            if param.required:
                required.append(param.name)
        
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": {
                    "type": "object",
                    "properties": properties,
                    "required": required
                }
            }
        }
    
    def get_parameter_dict(self) -> Dict[str, ToolParameter]:
        """Get parameters as a dictionary for easy lookup."""
        return {p.name: p for p in self.parameters}
