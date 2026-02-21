"""Git-related tools for branch management, commits, and status."""

import subprocess
from pathlib import Path
from typing import Any, List, Optional

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType


class GitBranchTool(BaseTool):
    """Tool for managing git branches."""
    
    name = "git_branch"
    description = "List, create, or switch git branches."
    parameters = [
        ToolParameter(
            name="action",
            description="Action to perform: list, create, switch, delete",
            type=ToolParameterType.STRING,
            required=True,
            enum=["list", "create", "switch", "delete"],
        ),
        ToolParameter(
            name="branch_name",
            description="Name of the branch (for create, switch, delete)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="base_branch",
            description="Base branch to create from (for create action)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="path",
            description="Path to git repository (default: current directory)",
            type=ToolParameterType.STRING,
            required=False,
            default=".",
        ),
    ]
    
    async def run(
        self,
        action: str,
        branch_name: Optional[str] = None,
        base_branch: Optional[str] = None,
        path: str = "."
    ) -> ToolResult:
        """Execute git branch operations.
        
        Args:
            action: Operation type
            branch_name: Branch name
            base_branch: Base branch for creation
            path: Repository path
            
        Returns:
            ToolResult with operation result
        """
        try:
            repo_path = Path(path)
            
            if not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            
            if action == "list":
                # List branches
                result = subprocess.run(
                    ["git", "branch", "-a"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return ToolResult.error_result(
                        error=f"Failed to list branches: {result.stderr}",
                        tool_name=self.name
                    )
                
                branches = []
                for line in result.stdout.strip().split('\n'):
                    line = line.strip()
                    if line:
                        current = line.startswith('*')
                        name = line.lstrip('* ')
                        branches.append({
                            "name": name,
                            "current": current,
                        })
                
                return ToolResult.success_result(
                    data={"branches": branches, "count": len(branches)},
                    tool_name=self.name
                )
            
            elif action == "create":
                if not branch_name:
                    return ToolResult.error_result(
                        error="branch_name is required for create action",
                        tool_name=self.name
                    )
                
                cmd = ["git", "checkout", "-b", branch_name]
                if base_branch:
                    cmd.append(base_branch)
                
                result = subprocess.run(
                    cmd,
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return ToolResult.error_result(
                        error=f"Failed to create branch: {result.stderr}",
                        tool_name=self.name
                    )
                
                return ToolResult.success_result(
                    data={
                        "action": "created",
                        "branch": branch_name,
                        "base": base_branch or "current",
                    },
                    tool_name=self.name
                )
            
            elif action == "switch":
                if not branch_name:
                    return ToolResult.error_result(
                        error="branch_name is required for switch action",
                        tool_name=self.name
                    )
                
                result = subprocess.run(
                    ["git", "checkout", branch_name],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return ToolResult.error_result(
                        error=f"Failed to switch branch: {result.stderr}",
                        tool_name=self.name
                    )
                
                return ToolResult.success_result(
                    data={
                        "action": "switched",
                        "branch": branch_name,
                    },
                    tool_name=self.name
                )
            
            elif action == "delete":
                if not branch_name:
                    return ToolResult.error_result(
                        error="branch_name is required for delete action",
                        tool_name=self.name
                    )
                
                result = subprocess.run(
                    ["git", "branch", "-D", branch_name],
                    cwd=repo_path,
                    capture_output=True,
                    text=True
                )
                
                if result.returncode != 0:
                    return ToolResult.error_result(
                        error=f"Failed to delete branch: {result.stderr}",
                        tool_name=self.name
                    )
                
                return ToolResult.success_result(
                    data={
                        "action": "deleted",
                        "branch": branch_name,
                    },
                    tool_name=self.name
                )
            
            else:
                return ToolResult.error_result(
                    error=f"Unknown action: {action}",
                    tool_name=self.name
                )
                
        except Exception as e:
            return ToolResult.error_result(
                error=f"Git branch operation failed: {str(e)}",
                tool_name=self.name
            )


class GitCommitTool(BaseTool):
    """Tool for creating git commits."""
    
    name = "git_commit"
    description = "Stage files and create a git commit."
    parameters = [
        ToolParameter(
            name="message",
            description="Commit message",
            type=ToolParameterType.STRING,
            required=True,
        ),
        ToolParameter(
            name="files",
            description="Specific files to commit (default: all modified)",
            type=ToolParameterType.ARRAY,
            required=False,
            default=None,
        ),
        ToolParameter(
            name="path",
            description="Path to git repository (default: current directory)",
            type=ToolParameterType.STRING,
            required=False,
            default=".",
        ),
        ToolParameter(
            name="author_name",
            description="Commit author name",
            type=ToolParameterType.STRING,
            required=False,
            default="Mohami Agent",
        ),
        ToolParameter(
            name="author_email",
            description="Commit author email",
            type=ToolParameterType.STRING,
            required=False,
            default="mohami@ki-agent.dev",
        ),
    ]
    
    async def run(
        self,
        message: str,
        files: Optional[List[str]] = None,
        path: str = ".",
        author_name: str = "Mohami Agent",
        author_email: str = "mohami@ki-agent.dev"
    ) -> ToolResult:
        """Create a git commit.
        
        Args:
            message: Commit message
            files: Specific files to commit
            path: Repository path
            author_name: Author name
            author_email: Author email
            
        Returns:
            ToolResult with commit result
        """
        try:
            repo_path = Path(path)
            
            if not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            
            # Set author environment
            env = {
                "GIT_AUTHOR_NAME": author_name,
                "GIT_AUTHOR_EMAIL": author_email,
                "GIT_COMMITTER_NAME": author_name,
                "GIT_COMMITTER_EMAIL": author_email,
            }
            
            # Stage files
            if files:
                # Stage specific files
                for file in files:
                    result = subprocess.run(
                        ["git", "add", file],
                        cwd=repo_path,
                        capture_output=True,
                        text=True,
                        env={**subprocess.os.environ, **env}
                    )
                    if result.returncode != 0:
                        return ToolResult.error_result(
                            error=f"Failed to stage {file}: {result.stderr}",
                            tool_name=self.name
                        )
            else:
                # Stage all changes
                result = subprocess.run(
                    ["git", "add", "-A"],
                    cwd=repo_path,
                    capture_output=True,
                    text=True,
                    env={**subprocess.os.environ, **env}
                )
                if result.returncode != 0:
                    return ToolResult.error_result(
                        error=f"Failed to stage files: {result.stderr}",
                        tool_name=self.name
                    )
            
            # Create commit
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env}
            )
            
            if result.returncode != 0:
                # Check if nothing to commit
                if "nothing to commit" in result.stdout.lower():
                    return ToolResult.success_result(
                        data={"status": "no_changes", "message": "Nothing to commit"},
                        tool_name=self.name
                    )
                return ToolResult.error_result(
                    error=f"Failed to commit: {result.stderr}",
                    tool_name=self.name
                )
            
            # Get commit hash
            hash_result = subprocess.run(
                ["git", "rev-parse", "HEAD"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            commit_hash = hash_result.stdout.strip()[:7] if hash_result.returncode == 0 else "unknown"
            
            return ToolResult.success_result(
                data={
                    "commit_hash": commit_hash,
                    "message": message,
                    "files": files or "all staged",
                    "author": f"{author_name} <{author_email}>",
                },
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Git commit failed: {str(e)}",
                tool_name=self.name
            )


class GitStatusTool(BaseTool):
    """Tool for checking git repository status."""
    
    name = "git_status"
    description = "Check git status: modified files, branch, commits ahead/behind."
    parameters = [
        ToolParameter(
            name="path",
            description="Path to git repository (default: current directory)",
            type=ToolParameterType.STRING,
            required=False,
            default=".",
        ),
    ]
    
    async def run(self, path: str = ".") -> ToolResult:
        """Get git status.
        
        Args:
            path: Repository path
            
        Returns:
            ToolResult with status information
        """
        try:
            repo_path = Path(path)
            
            if not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            
            # Get current branch
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
            # Get status
            status_result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if status_result.returncode != 0:
                return ToolResult.error_result(
                    error=f"Failed to get status: {status_result.stderr}",
                    tool_name=self.name
                )
            
            # Parse status
            modified = []
            added = []
            deleted = []
            untracked = []
            
            for line in status_result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                status = line[:2]
                file_path = line[3:]
                
                if status == "??":
                    untracked.append(file_path)
                elif status[0] == "A" or status[1] == "A":
                    added.append(file_path)
                elif status[0] == "D" or status[1] == "D":
                    deleted.append(file_path)
                elif status[0] == "M" or status[1] == "M" or status[0] == " ":
                    modified.append(file_path)
            
            # Get ahead/behind
            sync_result = subprocess.run(
                ["git", "rev-list", "--left-right", "--count", f"HEAD...@{u}"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            ahead = 0
            behind = 0
            if sync_result.returncode == 0:
                parts = sync_result.stdout.strip().split()
                if len(parts) == 2:
                    ahead = int(parts[0])
                    behind = int(parts[1])
            
            return ToolResult.success_result(
                data={
                    "branch": current_branch,
                    "modified": modified,
                    "added": added,
                    "deleted": deleted,
                    "untracked": untracked,
                    "total_changes": len(modified) + len(added) + len(deleted) + len(untracked),
                    "commits_ahead": ahead,
                    "commits_behind": behind,
                },
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Git status failed: {str(e)}",
                tool_name=self.name
            )


class GitLogTool(BaseTool):
    """Tool for viewing git commit history."""
    
    name = "git_log"
    description = "View recent git commit history."
    parameters = [
        ToolParameter(
            name="count",
            description="Number of commits to show",
            type=ToolParameterType.INTEGER,
            required=False,
            default=10,
        ),
        ToolParameter(
            name="path",
            description="Path to git repository or specific file",
            type=ToolParameterType.STRING,
            required=False,
            default=".",
        ),
        ToolParameter(
            name="author",
            description="Filter by author (optional)",
            type=ToolParameterType.STRING,
            required=False,
            default=None,
        ),
    ]
    
    async def run(
        self,
        count: int = 10,
        path: str = ".",
        author: Optional[str] = None
    ) -> ToolResult:
        """Get git log.
        
        Args:
            count: Number of commits
            path: Repository or file path
            author: Optional author filter
            
        Returns:
            ToolResult with commit history
        """
        try:
            repo_path = Path(path)
            
            if repo_path.is_file():
                file_path = repo_path
                repo_path = repo_path.parent
                while not (repo_path / ".git").exists() and repo_path.parent != repo_path:
                    repo_path = repo_path.parent
            elif not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            else:
                file_path = None
            
            # Build command
            cmd = [
                "git", "log",
                f"--max-count={count}",
                "--pretty=format:%H|%h|%an|%ae|%ad|%s",
                "--date=short"
            ]
            
            if author:
                cmd.extend(["--author", author])
            
            if file_path:
                cmd.append("--")
                cmd.append(str(file_path))
            
            result = subprocess.run(
                cmd,
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            
            if result.returncode != 0:
                return ToolResult.error_result(
                    error=f"Failed to get log: {result.stderr}",
                    tool_name=self.name
                )
            
            # Parse commits
            commits = []
            for line in result.stdout.strip().split('\n'):
                if not line:
                    continue
                    
                parts = line.split('|')
                if len(parts) >= 6:
                    commits.append({
                        "hash": parts[0],
                        "short_hash": parts[1],
                        "author": parts[2],
                        "email": parts[3],
                        "date": parts[4],
                        "message": parts[5],
                    })
            
            return ToolResult.success_result(
                data={
                    "commits": commits,
                    "count": len(commits),
                },
                tool_name=self.name
            )
            
        except Exception as e:
            return ToolResult.error_result(
                error=f"Git log failed: {str(e)}",
                tool_name=self.name
            )
