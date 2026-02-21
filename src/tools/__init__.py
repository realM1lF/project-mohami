"""Tool-Use Framework for Mohami AI Agents.

This module provides the infrastructure for tool-based AI interactions,
following the OpenAI Function Calling pattern.
"""

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType

# Local file system tools (existing)
from .file_tools import (
    FileReadTool,
    FileWriteTool,
    FileListTool,
    FileSearchTool,
)

# Git repository tools (new implementation)
from .git_file_tools import (
    ReadFileTool,
    WriteFileTool, 
    ListFilesTool,
    CreateBranchTool,
    GetRepoInfoTool,
    # Aliases for backward compatibility
    GitReadFileTool,
    GitWriteFileTool,
    GitListFilesTool,
    GitCreateBranchTool,
    GitGetRepoInfoTool,
)

# Infrastructure components
from .registry import ToolRegistry
from .executor import ToolExecutor

# Additional Git tools (from git_tools.py)
try:
    from .git_tools import GitBranchTool, GitCommitTool, GitStatusTool
except ImportError:
    GitBranchTool = None
    GitCommitTool = None
    GitStatusTool = None

# Code tools (from code_tools.py)
try:
    from .code_tools import CodeGenerateTool, CodeAnalyzeTool
except ImportError:
    CodeGenerateTool = None
    CodeAnalyzeTool = None

__all__ = [
    # Base classes
    "BaseTool",
    "ToolResult", 
    "ToolParameter",
    "ToolParameterType",
    # Local File Tools
    "FileReadTool",
    "FileWriteTool",
    "FileListTool",
    "FileSearchTool",
    # Git Repository File Tools
    "ReadFileTool",
    "WriteFileTool",
    "ListFilesTool", 
    "CreateBranchTool",
    "GetRepoInfoTool",
    # Git Tools aliases
    "GitReadFileTool",
    "GitWriteFileTool",
    "GitListFilesTool",
    "GitCreateBranchTool",
    "GitGetRepoInfoTool",
    # Infrastructure
    "ToolRegistry",
    "ToolExecutor",
    # Optional components
    "GitBranchTool",
    "GitCommitTool",
    "GitStatusTool",
    "CodeGenerateTool",
    "CodeAnalyzeTool",
]
