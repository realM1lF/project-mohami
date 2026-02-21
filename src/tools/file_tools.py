"""File system tools for reading, writing, and listing files."""

import os
from pathlib import Path
from typing import Any, List, Optional

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType


class FileReadTool(BaseTool):
    """Tool for reading file contents."""
    
    name = "file_read"
    description = "Read the contents of a file from the file system."
    parameters = [
        ToolParameter(
            name="path",
            description="Path to the file to read (relative or absolute)",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="limit",
            description="Maximum number of lines to read (0 = no limit)",
            type=ToolParameterType.INTEGER,
            required=False,
            default=0,
        ),
    ]
    
    async def run(self, path: str, limit: int = 0) -> ToolResult:
        """Read file contents.
        
        Args:
            path: Path to the file
            limit: Maximum lines to read (0 = unlimited)
            
        Returns:
            ToolResult with file content or error
        """
        try:
            file_path = Path(path)
            
            if not file_path.exists():
                return ToolResult.error_result(
                    error=f"File not found: {path}",
                    tool_name=self.name
                )
            
            if not file_path.is_file():
                return ToolResult.error_result(
                    error=f"Path is not a file: {path}",
                    tool_name=self.name
                )
            
            # Read file
            content = file_path.read_text(encoding='utf-8')
            
            # Apply line limit if specified
            if limit > 0:
                lines = content.split('\n')
                content = '\n'.join(lines[:limit])
                if len(lines) > limit:
                    content += f"\n... ({len(lines) - limit} more lines)"
            
            return ToolResult.success_result(
                data={
                    "path": str(file_path.resolve()),
                    "content": content,
                    "size_bytes": len(content.encode('utf-8')),
                    "lines": content.count('\n') + 1,
                },
                tool_name=self.name
            )
            
        except UnicodeDecodeError:
            return ToolResult.error_result(
                error=f"File is not a text file (binary): {path}",
                tool_name=self.name
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to read file: {str(e)}",
                tool_name=self.name
            )


class FileWriteTool(BaseTool):
    """Tool for writing file contents."""
    
    name = "file_write"
    description = "Write content to a file. Creates directories if needed."
    parameters = [
        ToolParameter(
            name="path",
            description="Path to the file to write",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="content",
            description="Content to write to the file",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="append",
            description="If true, append to existing file instead of overwriting",
            type=ToolParameterType.BOOLEAN,
            required=False,
            default=False,
        ),
    ]
    
    async def run(self, path: str, content: str, append: bool = False) -> ToolResult:
        """Write content to a file.
        
        Args:
            path: Path to the file
            content: Content to write
            append: Whether to append instead of overwrite
            
        Returns:
            ToolResult with write result
        """
        try:
            file_path = Path(path)
            
            # Create parent directories if needed
            file_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Check if file exists and we're not appending
            file_existed = file_path.exists()
            
            # Write file
            mode = 'a' if append else 'w'
            with open(file_path, mode, encoding='utf-8') as f:
                f.write(content)
            
            return ToolResult.success_result(
                data={
                    "path": str(file_path.resolve()),
                    "bytes_written": len(content.encode('utf-8')),
                    "action": "appended" if append else "written",
                    "file_existed": file_existed,
                },
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to write file: {str(e)}",
                tool_name=self.name
            )


class FileListTool(BaseTool):
    """Tool for listing directory contents."""
    
    name = "file_list"
    description = "List files and directories at a given path."
    parameters = [
        ToolParameter(
            name="path",
            description="Directory path to list (default: current directory)",
            type=ToolParameterType.STRING,
            required=False,
            default=".",
        ),
        ToolParameter(
            name="recursive",
            description="List recursively (includes subdirectories)",
            type=ToolParameterType.BOOLEAN,
            required=False,
            default=False,
        ),
        ToolParameter(
            name="pattern",
            description="Optional glob pattern to filter files (e.g., '*.py')",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
    ]
    
    async def run(
        self,
        path: str = ".",
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> ToolResult:
        """List directory contents.
        
        Args:
            path: Directory path
            recursive: Whether to list recursively
            pattern: Optional glob pattern
            
        Returns:
            ToolResult with file list
        """
        try:
            dir_path = Path(path)
            
            if not dir_path.exists():
                return ToolResult.error_result(
                    error=f"Directory not found: {path}",
                    tool_name=self.name
                )
            
            if not dir_path.is_dir():
                return ToolResult.error_result(
                    error=f"Path is not a directory: {path}",
                    tool_name=self.name
                )
            
            # Collect files
            files = []
            directories = []
            
            if recursive:
                if pattern:
                    items = list(dir_path.rglob(pattern))
                else:
                    items = list(dir_path.rglob("*"))
            else:
                if pattern:
                    items = list(dir_path.glob(pattern))
                else:
                    items = list(dir_path.iterdir())
            
            for item in items:
                try:
                    stat = item.stat()
                    info = {
                        "name": item.name,
                        "path": str(item.relative_to(dir_path)),
                        "size": stat.st_size,
                        "modified": stat.st_mtime,
                    }
                    if item.is_dir():
                        directories.append(info)
                    else:
                        files.append(info)
                except (OSError, PermissionError):
                    # Skip files we can't stat
                    continue
            
            # Sort by name
            files.sort(key=lambda x: x["name"])
            directories.sort(key=lambda x: x["name"])
            
            return ToolResult.success_result(
                data={
                    "path": str(dir_path.resolve()),
                    "directories": directories,
                    "files": files,
                    "total_count": len(files) + len(directories),
                },
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to list directory: {str(e)}",
                tool_name=self.name
            )


class FileSearchTool(BaseTool):
    """Tool for searching file contents."""
    
    name = "file_search"
    description = "Search for text patterns in files."
    parameters = [
        ToolParameter(
            name="pattern",
            description="Text pattern to search for (supports regex)",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="path",
            description="Directory or file to search in",
            type=ToolParameterType.STRING,
            required=False,
            default=".",
        ),
        ToolParameter(
            name="file_pattern",
            description="Only search files matching this pattern (e.g., '*.py')",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="max_results",
            description="Maximum number of results to return",
            type=ToolParameterType.INTEGER,
            required=False,
            default=20,
        ),
    ]
    
    async def run(
        self,
        pattern: str,
        path: str = ".",
        file_pattern: Optional[str] = None,
        max_results: int = 20
    ) -> ToolResult:
        """Search for text in files.
        
        Args:
            pattern: Search pattern
            path: Directory or file to search
            file_pattern: Optional file filter
            max_results: Maximum results
            
        Returns:
            ToolResult with search results
        """
        try:
            import re
            
            search_path = Path(path)
            results = []
            
            # Compile regex
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                return ToolResult.error_result(
                    error=f"Invalid regex pattern: {e}",
                    tool_name=self.name
                )
            
            # Determine files to search
            if search_path.is_file():
                files = [search_path]
            else:
                if file_pattern:
                    files = list(search_path.rglob(file_pattern))
                else:
                    files = [f for f in search_path.rglob("*") if f.is_file()]
            
            # Search in files
            for file_path in files:
                if len(results) >= max_results:
                    break
                
                try:
                    content = file_path.read_text(encoding='utf-8', errors='ignore')
                    lines = content.split('\n')
                    
                    for line_num, line in enumerate(lines, 1):
                        if regex.search(line):
                            results.append({
                                "file": str(file_path),
                                "line": line_num,
                                "content": line.strip(),
                            })
                            
                            if len(results) >= max_results:
                                break
                                
                except (UnicodeDecodeError, PermissionError, OSError):
                    continue
            
            return ToolResult.success_result(
                data={
                    "pattern": pattern,
                    "files_searched": len(files),
                    "matches": results,
                    "total_matches": len(results),
                    "truncated": len(files) > max_results,
                },
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Search failed: {str(e)}",
                tool_name=self.name
            )
