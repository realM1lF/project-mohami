"""File system tools for reading, writing, and listing files with GitHub integration."""

import os
import time
from pathlib import Path
from typing import Any, List, Optional

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType


class FileReadTool(BaseTool):
    """Tool for reading file contents from local filesystem or GitHub."""
    
    name = "file_read"
    description = "Read the contents of a file from the file system or GitHub repository."
    parameters = [
        ToolParameter(
            name="path",
            description="Path to the file to read (local path or repo-relative path)",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="repo",
            description="Repository name (e.g., 'owner/repo') for GitHub reads",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="branch",
            description="Branch name for GitHub reads (default: 'main')",
            type=ToolParameterType.STRING,
            required=False,
            default="main",
        ),
        ToolParameter(
            name="limit",
            description="Maximum number of lines to read (0 = no limit)",
            type=ToolParameterType.INTEGER,
            required=False,
            default=0,
        ),
        ToolParameter(
            name="use_cache",
            description="Use cache for GitHub reads if available",
            type=ToolParameterType.BOOLEAN,
            required=False,
            default=True,
        ),
    ]
    
    def __init__(
        self, 
        git_provider=None, 
        cache=None,
        default_workspace: Optional[str] = None
    ):
        """Initialize with optional Git provider and cache.
        
        Args:
            git_provider: Git provider instance (e.g., GitHubProvider)
            cache: Cache instance (e.g., GitRepoCache)
            default_workspace: Default local workspace path
        """
        super().__init__()
        self.git_provider = git_provider
        self.cache = cache
        self.default_workspace = default_workspace
    
    async def run(
        self, 
        path: str, 
        repo: Optional[str] = None,
        branch: str = "main",
        limit: int = 0,
        use_cache: bool = True
    ) -> ToolResult:
        """Read file contents from local filesystem or GitHub.
        
        Args:
            path: Path to the file
            repo: Repository name for GitHub reads
            branch: Branch name for GitHub reads
            limit: Maximum lines to read (0 = unlimited)
            use_cache: Whether to use cache
            
        Returns:
            ToolResult with file content or error
        """
        start_time = time.time()
        
        try:
            # Determine if this is a GitHub read
            if repo and self.git_provider:
                return await self._read_from_github(
                    path, repo, branch, limit, use_cache, start_time
                )
            else:
                return await self._read_from_local(path, limit, start_time)
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Failed to read file: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _read_from_github(
        self, 
        path: str, 
        repo: str, 
        branch: str, 
        limit: int,
        use_cache: bool,
        start_time: float
    ) -> ToolResult:
        """Read file from GitHub with caching."""
        # Check cache first if available and enabled
        if use_cache and self.cache:
            cached_content = await self.cache.get_file_content(repo, path)
            if cached_content:
                content = self._apply_line_limit(cached_content, limit)
                execution_time = (time.time() - start_time) * 1000
                
                return ToolResult.success_result(
                    data={
                        "path": path,
                        "repo": repo,
                        "branch": branch,
                        "content": content,
                        "size_bytes": len(content.encode('utf-8')),
                        "lines": content.count('\n') + 1,
                        "source": "cache",
                    },
                    execution_time_ms=execution_time,
                    tool_name=self.name
                )
        
        # Fetch from GitHub
        try:
            content = await self.git_provider.get_file_content(repo, path, branch)
            
            # Cache the content if cache available
            if self.cache:
                await self.cache.set_file_content(repo, path, content)
            
            # Apply line limit
            content = self._apply_line_limit(content, limit)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data={
                    "path": path,
                    "repo": repo,
                    "branch": branch,
                    "content": content,
                    "size_bytes": len(content.encode('utf-8')),
                    "lines": content.count('\n') + 1,
                    "source": "github",
                },
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Failed to read from GitHub: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _read_from_local(self, path: str, limit: int, start_time: float) -> ToolResult:
        """Read file from local filesystem."""
        file_path = Path(path)
        
        # If relative path and default workspace set, resolve it
        if not file_path.is_absolute() and self.default_workspace:
            file_path = Path(self.default_workspace) / file_path
        
        if not file_path.exists():
            return ToolResult.error_result(
                error=f"File not found: {path}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tool_name=self.name
            )
        
        if not file_path.is_file():
            return ToolResult.error_result(
                error=f"Path is not a file: {path}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tool_name=self.name
            )
        
        try:
            content = file_path.read_text(encoding='utf-8')
            content = self._apply_line_limit(content, limit)
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data={
                    "path": str(file_path.resolve()),
                    "content": content,
                    "size_bytes": len(content.encode('utf-8')),
                    "lines": content.count('\n') + 1,
                    "source": "local",
                },
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except UnicodeDecodeError:
            return ToolResult.error_result(
                error=f"File is not a text file (binary): {path}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tool_name=self.name
            )
    
    def _apply_line_limit(self, content: str, limit: int) -> str:
        """Apply line limit to content."""
        if limit > 0:
            lines = content.split('\n')
            if len(lines) > limit:
                content = '\n'.join(lines[:limit])
                content += f"\n\n... ({len(lines) - limit} more lines)"
        return content


class FileWriteTool(BaseTool):
    """Tool for writing file contents to local filesystem or GitHub."""
    
    name = "file_write"
    description = "Write content to a file. Creates directories/branches if needed. Can create PRs for GitHub."
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
            name="repo",
            description="Repository name (e.g., 'owner/repo') for GitHub writes",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="branch",
            description="Branch name for GitHub writes (default: creates new branch)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="create_pr",
            description="Create a Pull Request for GitHub writes",
            type=ToolParameterType.BOOLEAN,
            required=False,
            default=False,
        ),
        ToolParameter(
            name="pr_title",
            description="Title for the PR (if create_pr is true)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="pr_body",
            description="Body/description for the PR",
            type=ToolParameterType.STRING,
            required=False,
            default="",
        ),
        ToolParameter(
            name="commit_message",
            description="Commit message for GitHub writes",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="append",
            description="If true, append to existing file instead of overwriting (local only)",
            type=ToolParameterType.BOOLEAN,
            required=False,
            default=False,
        ),
        ToolParameter(
            name="overwrite",
            description="If false, error when file exists (GitHub only)",
            type=ToolParameterType.BOOLEAN,
            required=False,
            default=True,
        ),
    ]
    
    def __init__(
        self, 
        git_provider=None,
        default_workspace: Optional[str] = None
    ):
        """Initialize with optional Git provider.
        
        Args:
            git_provider: Git provider instance (e.g., GitHubProvider)
            default_workspace: Default local workspace path
        """
        super().__init__()
        self.git_provider = git_provider
        self.default_workspace = default_workspace
    
    async def run(
        self, 
        path: str, 
        content: str, 
        repo: Optional[str] = None,
        branch: Optional[str] = None,
        create_pr: bool = False,
        pr_title: Optional[str] = None,
        pr_body: str = "",
        commit_message: Optional[str] = None,
        append: bool = False,
        overwrite: bool = True
    ) -> ToolResult:
        """Write content to a file.
        
        Args:
            path: Path to the file
            content: Content to write
            repo: Repository name for GitHub writes
            branch: Branch name (creates new if not specified for GitHub)
            create_pr: Whether to create a PR
            pr_title: PR title
            pr_body: PR body
            commit_message: Commit message
            append: Whether to append instead of overwrite (local only)
            overwrite: Whether to overwrite existing files
            
        Returns:
            ToolResult with write result
        """
        start_time = time.time()
        
        try:
            # Determine if this is a GitHub write
            if repo and self.git_provider:
                return await self._write_to_github(
                    path, content, repo, branch, create_pr, pr_title, 
                    pr_body, commit_message, overwrite, start_time
                )
            else:
                return await self._write_to_local(path, content, append, start_time)
                
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Failed to write file: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _write_to_github(
        self,
        path: str,
        content: str,
        repo: str,
        branch: Optional[str],
        create_pr: bool,
        pr_title: Optional[str],
        pr_body: str,
        commit_message: Optional[str],
        overwrite: bool,
        start_time: float
    ) -> ToolResult:
        """Write file to GitHub with branch/PR creation."""
        from .git_tools import GitBranchTool  # Avoid circular import
        
        try:
            # Check if file exists if not overwriting
            if not overwrite:
                try:
                    await self.git_provider.get_file_content(repo, path, branch or "main")
                    return ToolResult.error_result(
                        error=f"File already exists: {path}. Set overwrite=true to replace.",
                        execution_time_ms=(time.time() - start_time) * 1000,
                        tool_name=self.name
                    )
                except Exception:
                    pass  # File doesn't exist, safe to proceed
            
            # Generate branch name if not provided and creating PR
            if create_pr and not branch:
                import datetime
                timestamp = datetime.datetime.now().strftime("%Y%m%d-%H%M%S")
                branch = f"ai-update-{timestamp}"
            elif not branch:
                branch = "main"
            
            # Create branch if it's a new branch for PR
            if create_pr and branch != "main":
                try:
                    await self.git_provider.create_branch(repo, branch, "main")
                except Exception as e:
                    # Branch might already exist, continue
                    pass
            
            # Prepare commit message
            if not commit_message:
                commit_message = f"Update {path}"
            
            # Create commit with the file
            files = {path: content}
            commit_sha = await self.git_provider.create_commit(
                repo=repo,
                branch=branch,
                message=commit_message,
                files=files
            )
            
            result = {
                "path": path,
                "repo": repo,
                "branch": branch,
                "bytes_written": len(content.encode('utf-8')),
                "commit_sha": commit_sha,
                "action": "committed",
            }
            
            # Create PR if requested
            if create_pr:
                pr = await self.git_provider.create_pr(
                    repo=repo,
                    title=pr_title or f"Update {path}",
                    body=pr_body or f"Automated update to {path}",
                    head_branch=branch,
                    base_branch="main"
                )
                result["pr_created"] = True
                result["pr_number"] = pr.number
                result["pr_url"] = pr.url
                result["pr_title"] = pr.title
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data=result,
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"GitHub write failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _write_to_local(
        self, 
        path: str, 
        content: str, 
        append: bool,
        start_time: float
    ) -> ToolResult:
        """Write file to local filesystem."""
        file_path = Path(path)
        
        # If relative path and default workspace set, resolve it
        if not file_path.is_absolute() and self.default_workspace:
            file_path = Path(self.default_workspace) / file_path
        
        # Create parent directories if needed
        file_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Check if file exists
        file_existed = file_path.exists()
        
        # Write file
        mode = 'a' if append else 'w'
        with open(file_path, mode, encoding='utf-8') as f:
            f.write(content)
        
        execution_time = (time.time() - start_time) * 1000
        
        return ToolResult.success_result(
            data={
                "path": str(file_path.resolve()),
                "bytes_written": len(content.encode('utf-8')),
                "action": "appended" if append else "written",
                "file_existed": file_existed,
                "source": "local",
            },
            execution_time_ms=execution_time,
            tool_name=self.name
        )


class FileListTool(BaseTool):
    """Tool for listing directory contents locally or from GitHub."""
    
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
            name="repo",
            description="Repository name for GitHub listing",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="branch",
            description="Branch for GitHub listing",
            type=ToolParameterType.STRING,
            required=False,
            default="main",
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
    
    def __init__(
        self, 
        git_provider=None,
        default_workspace: Optional[str] = None
    ):
        """Initialize with optional Git provider."""
        super().__init__()
        self.git_provider = git_provider
        self.default_workspace = default_workspace
    
    async def run(
        self,
        path: str = ".",
        repo: Optional[str] = None,
        branch: str = "main",
        recursive: bool = False,
        pattern: Optional[str] = None
    ) -> ToolResult:
        """List directory contents.
        
        Args:
            path: Directory path
            repo: Repository name for GitHub
            branch: Branch for GitHub
            recursive: Whether to list recursively
            pattern: Optional glob pattern
            
        Returns:
            ToolResult with file list
        """
        start_time = time.time()
        
        try:
            # GitHub listing not fully implemented yet, use local for now
            # In future, could use GitHub's tree API
            return await self._list_local(path, recursive, pattern, start_time)
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Failed to list directory: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
    
    async def _list_local(
        self, 
        path: str, 
        recursive: bool, 
        pattern: Optional[str],
        start_time: float
    ) -> ToolResult:
        """List local directory contents."""
        dir_path = Path(path)
        
        # If relative path and default workspace set, resolve it
        if not dir_path.is_absolute() and self.default_workspace:
            dir_path = Path(self.default_workspace) / dir_path
        
        if not dir_path.exists():
            return ToolResult.error_result(
                error=f"Directory not found: {path}",
                execution_time_ms=(time.time() - start_time) * 1000,
                tool_name=self.name
            )
        
        if not dir_path.is_dir():
            return ToolResult.error_result(
                error=f"Path is not a directory: {path}",
                execution_time_ms=(time.time() - start_time) * 1000,
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
                continue
        
        # Sort by name
        files.sort(key=lambda x: x["name"])
        directories.sort(key=lambda x: x["name"])
        
        execution_time = (time.time() - start_time) * 1000
        
        return ToolResult.success_result(
            data={
                "path": str(dir_path.resolve()),
                "directories": directories,
                "files": files,
                "total_count": len(files) + len(directories),
                "source": "local",
            },
            execution_time_ms=execution_time,
            tool_name=self.name
        )


class FileSearchTool(BaseTool):
    """Tool for searching file contents locally."""
    
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
    
    def __init__(self, default_workspace: Optional[str] = None):
        """Initialize with optional default workspace."""
        super().__init__()
        self.default_workspace = default_workspace
    
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
        start_time = time.time()
        
        try:
            import re
            
            search_path = Path(path)
            
            # If relative path and default workspace set, resolve it
            if not search_path.is_absolute() and self.default_workspace:
                search_path = Path(self.default_workspace) / search_path
            
            results = []
            
            # Compile regex
            try:
                regex = re.compile(pattern, re.IGNORECASE)
            except re.error as e:
                return ToolResult.error_result(
                    error=f"Invalid regex pattern: {e}",
                    execution_time_ms=(time.time() - start_time) * 1000,
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
            files_searched = 0
            for file_path in files:
                if len(results) >= max_results:
                    break
                
                files_searched += 1
                
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
            
            execution_time = (time.time() - start_time) * 1000
            
            return ToolResult.success_result(
                data={
                    "pattern": pattern,
                    "files_searched": files_searched,
                    "matches": results,
                    "total_matches": len(results),
                    "truncated": files_searched < len(files) if isinstance(files, list) else False,
                },
                execution_time_ms=execution_time,
                tool_name=self.name
            )
            
        except Exception as e:
            execution_time = (time.time() - start_time) * 1000
            return ToolResult.error_result(
                error=f"Search failed: {str(e)}",
                execution_time_ms=execution_time,
                tool_name=self.name
            )
