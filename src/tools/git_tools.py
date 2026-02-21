"""Git-related tools for local and remote repository operations.

This module provides two categories of Git tools:
1. Local Git Tools: Operate on local git repositories via subprocess
2. Remote Git Tools: Operate on remote repositories via Git provider API (GitHub)
"""

import subprocess
from pathlib import Path
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from .base import BaseTool, ToolResult, ToolParameter, ToolParameterType


# =============================================================================
# LOCAL GIT TOOLS (via subprocess)
# =============================================================================

class GitBranchTool(BaseTool):
    """Tool for managing local git branches."""
    
    name = "git_branch"
    description = "List, create, or switch git branches in a local repository."
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
        """Execute git branch operations."""
        try:
            repo_path = Path(path)
            
            if not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            
            if action == "list":
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
                for line in result.stdout.strip().split("\n"):
                    line = line.strip()
                    if line:
                        current = line.startswith("*")
                        name = line.lstrip("* ")
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
    """Tool for creating git commits in local repositories."""
    
    name = "git_commit"
    description = "Stage files and create a git commit in a local repository."
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
        """Create a git commit."""
        try:
            repo_path = Path(path)
            
            if not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            
            env = {
                "GIT_AUTHOR_NAME": author_name,
                "GIT_AUTHOR_EMAIL": author_email,
                "GIT_COMMITTER_NAME": author_name,
                "GIT_COMMITTER_EMAIL": author_email,
            }
            
            if files:
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
            
            result = subprocess.run(
                ["git", "commit", "-m", message],
                cwd=repo_path,
                capture_output=True,
                text=True,
                env={**subprocess.os.environ, **env}
            )
            
            if result.returncode != 0:
                if "nothing to commit" in result.stdout.lower():
                    return ToolResult.success_result(
                        data={"status": "no_changes", "message": "Nothing to commit"},
                        tool_name=self.name
                    )
                return ToolResult.error_result(
                    error=f"Failed to commit: {result.stderr}",
                    tool_name=self.name
                )
            
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
    """Tool for checking local git repository status."""
    
    name = "git_status"
    description = "Check git status: modified files, branch, commits ahead/behind in a local repository."
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
        """Get git status."""
        try:
            repo_path = Path(path)
            
            if not (repo_path / ".git").exists():
                return ToolResult.error_result(
                    error=f"Not a git repository: {path}",
                    tool_name=self.name
                )
            
            branch_result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=repo_path,
                capture_output=True,
                text=True
            )
            current_branch = branch_result.stdout.strip() if branch_result.returncode == 0 else "unknown"
            
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
            
            modified = []
            added = []
            deleted = []
            untracked = []
            
            for line in status_result.stdout.strip().split("\n"):
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
                ["git", "rev-list", "--left-right", "--count", "HEAD...@{u}"],
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
    """Tool for viewing git commit history in local repositories."""
    
    name = "git_log"
    description = "View recent git commit history in a local repository."
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
        """Get git log."""
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
            
            commits = []
            for line in result.stdout.strip().split("\n"):
                if not line:
                    continue
                    
                parts = line.split("|")
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


# =============================================================================
# REMOTE GIT TOOLS (via Git Provider API - GitHub/Bitbucket)
# =============================================================================

class GitHubReadFileTool(BaseTool):
    """Tool to read file content from a remote Git repository via GitHub API."""
    
    name = "github_read_file"
    description = "Liest den Inhalt einer Datei aus einem GitHub Repository"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="path",
            description="Path to the file within the repository",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="branch",
            description="Branch name (default: main)",
            type=ToolParameterType.STRING,
            required=False,
            default="main"
        )
    ]
    
    def __init__(self, git_provider=None):
        super().__init__()
        self.git = git_provider
    
    async def run(self, repo: str, path: str, branch: str = "main") -> ToolResult:
        """Read file content from repository."""
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                tool_name=self.name
            )
        
        try:
            from ..git_provider.base import FileNotFoundError, RepositoryNotFoundError
            
            content = await self.git.get_file_content(repo, path, branch)
            return ToolResult.success_result(
                data={
                    "content": content,
                    "path": path,
                    "branch": branch,
                    "repo": repo
                },
                tool_name=self.name
            )
        except FileNotFoundError:
            return ToolResult.error_result(
                error=f"File not found: {path}",
                tool_name=self.name
            )
        except RepositoryNotFoundError:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                tool_name=self.name
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to read file: {str(e)}",
                tool_name=self.name
            )


class GitHubWriteFileTool(BaseTool):
    """Tool to write file content to a remote Git repository via GitHub API."""
    
    name = "github_write_file"
    description = "Schreibt Inhalt in eine Datei auf GitHub (erstellt oder ueberschreibt)"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="path",
            description="Path to the file within the repository",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="content",
            description="Content to write to the file",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="branch",
            description="Branch name (default: main)",
            type=ToolParameterType.STRING,
            required=False,
            default="main"
        ),
        ToolParameter(
            name="message",
            description="Commit message for the change",
            type=ToolParameterType.STRING,
            required=False,
            default=None
        )
    ]
    
    def __init__(self, git_provider=None):
        super().__init__()
        self.git = git_provider
    
    async def run(
        self, 
        repo: str, 
        path: str, 
        content: str, 
        branch: str = "main",
        message: Optional[str] = None
    ) -> ToolResult:
        """Write file content to repository."""
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                tool_name=self.name
            )
        
        try:
            from ..git_provider.base import RepositoryNotFoundError
            
            if not message:
                message = f"Update {path}"
            
            commit_sha = await self.git.create_commit(
                repo=repo,
                branch=branch,
                message=message,
                files={path: content}
            )
            
            return ToolResult.success_result(
                data={
                    "commit_sha": commit_sha,
                    "path": path,
                    "branch": branch,
                    "repo": repo,
                    "message": message
                },
                tool_name=self.name
            )
        except RepositoryNotFoundError:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                tool_name=self.name
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to write file: {str(e)}",
                tool_name=self.name
            )


class GitHubListFilesTool(BaseTool):
    """Tool to list all files in a remote Git repository via GitHub API."""
    
    name = "github_list_files"
    description = "Listet alle Dateien in einem GitHub Repository auf"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="branch",
            description="Branch name (default: main)",
            type=ToolParameterType.STRING,
            required=False,
            default="main"
        )
    ]
    
    def __init__(self, git_provider=None):
        super().__init__()
        self.git = git_provider
    
    async def run(self, repo: str, branch: str = "main") -> ToolResult:
        """List all files in repository using GitHub API."""
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                tool_name=self.name
            )
        
        try:
            from ..git_provider.base import RepositoryNotFoundError
            
            if httpx is None:
                return ToolResult.error_result(
                    error="httpx is required for this operation",
                    tool_name=self.name
                )
            
            base_url = "https://api.github.com"
            endpoint = f"/repos/{repo}/git/trees/{branch}?recursive=1"
            url = f"{base_url}{endpoint}"
            
            headers = {
                "Authorization": f"Bearer {self.git.token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.get(url, headers=headers, timeout=30.0)
                
                if response.status_code == 404:
                    return ToolResult.error_result(
                        error=f"Repository or branch not found: {repo}@{branch}",
                        tool_name=self.name
                    )
                elif response.status_code >= 400:
                    return ToolResult.error_result(
                        error=f"GitHub API error: {response.status_code}",
                        tool_name=self.name
                    )
                
                data = response.json()
                tree = data.get("tree", [])
                
                files = []
                directories = []
                
                for item in tree:
                    item_path = item.get("path", "")
                    item_type = item.get("type", "")
                    
                    if item_type == "blob":
                        files.append({
                            "path": item_path,
                            "size": item.get("size", 0),
                            "sha": item.get("sha", "")
                        })
                    elif item_type == "tree":
                        directories.append({
                            "path": item_path,
                            "sha": item.get("sha", "")
                        })
                
                return ToolResult.success_result(
                    data={
                        "files": files,
                        "directories": directories,
                        "total_files": len(files),
                        "total_directories": len(directories),
                        "branch": branch,
                        "repo": repo,
                        "truncated": data.get("truncated", False)
                    },
                    tool_name=self.name
                )
                
        except RepositoryNotFoundError:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                tool_name=self.name
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to list files: {str(e)}",
                tool_name=self.name
            )


class GitHubCreateBranchTool(BaseTool):
    """Tool to create a new branch in a remote Git repository via GitHub API."""
    
    name = "github_create_branch"
    description = "Erstellt einen neuen Branch in einem GitHub Repository"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="branch_name",
            description="Name for the new branch",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="from_branch",
            description="Source branch to create from (default: main)",
            type=ToolParameterType.STRING,
            required=False,
            default="main"
        )
    ]
    
    def __init__(self, git_provider=None):
        super().__init__()
        self.git = git_provider
    
    async def run(
        self, 
        repo: str, 
        branch_name: str, 
        from_branch: str = "main"
    ) -> ToolResult:
        """Create a new branch in the repository."""
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                tool_name=self.name
            )
        
        try:
            from ..git_provider.base import RepositoryNotFoundError
            
            branch_url = await self.git.create_branch(repo, branch_name, from_branch)
            
            return ToolResult.success_result(
                data={
                    "branch_name": branch_name,
                    "from_branch": from_branch,
                    "url": branch_url,
                    "repo": repo
                },
                tool_name=self.name
            )
        except RepositoryNotFoundError:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                tool_name=self.name
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "reference already exists" in error_msg:
                return ToolResult.success_result(
                    data={
                        "branch_name": branch_name,
                        "from_branch": from_branch,
                        "url": f"https://github.com/{repo}/tree/{branch_name}",
                        "repo": repo,
                        "already_existed": True,
                    },
                    tool_name=self.name
                )
            return ToolResult.error_result(
                error=f"Failed to create branch: {str(e)}",
                tool_name=self.name
            )


class GitHubGetRepoInfoTool(BaseTool):
    """Tool to get repository information from GitHub."""
    
    name = "github_get_repo_info"
    description = "Holt Repository-Informationen von GitHub (default_branch, etc.)"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        )
    ]
    
    def __init__(self, git_provider=None):
        super().__init__()
        self.git = git_provider
    
    async def run(self, repo: str) -> ToolResult:
        """Get repository information."""
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                tool_name=self.name
            )
        
        try:
            from ..git_provider.base import RepositoryNotFoundError
            
            repo_info = await self.git.get_repository_info(repo)
            
            return ToolResult.success_result(
                data={
                    "id": repo_info.id,
                    "name": repo_info.name,
                    "full_name": repo_info.full_name,
                    "default_branch": repo_info.default_branch,
                    "url": repo_info.url,
                    "description": repo_info.description,
                    "private": repo_info.private
                },
                tool_name=self.name
            )
        except RepositoryNotFoundError:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                tool_name=self.name
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to get repository info: {str(e)}",
                tool_name=self.name
            )


class GitHubCreatePRTool(BaseTool):
    """Tool to create a Pull Request on GitHub."""
    
    name = "github_create_pr"
    description = "Erstellt einen Pull Request auf GitHub"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="title",
            description="Title of the Pull Request",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="body",
            description="Description / body of the Pull Request",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="head_branch",
            description="Branch with changes (source)",
            type=ToolParameterType.STRING,
            required=True
        ),
        ToolParameter(
            name="base_branch",
            description="Target branch (default: main)",
            type=ToolParameterType.STRING,
            required=False,
            default="main"
        )
    ]
    
    def __init__(self, git_provider=None):
        super().__init__()
        self.git = git_provider
    
    async def run(
        self,
        repo: str,
        title: str,
        body: str,
        head_branch: str,
        base_branch: str = "main"
    ) -> ToolResult:
        """Create a Pull Request."""
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                tool_name=self.name
            )
        
        try:
            pr_info = await self.git.create_pr(
                repo=repo,
                title=title,
                body=body,
                head_branch=head_branch,
                base_branch=base_branch
            )
            
            return ToolResult.success_result(
                data={
                    "pr_number": pr_info.number,
                    "url": pr_info.url,
                    "title": pr_info.title,
                    "state": pr_info.state,
                    "head_branch": head_branch,
                    "base_branch": base_branch,
                    "repo": repo
                },
                tool_name=self.name
            )
        except Exception as e:
            error_msg = str(e).lower()
            if "already exists" in error_msg or "a pull request already exists" in error_msg:
                return ToolResult.success_result(
                    data={
                        "pr_number": None,
                        "url": f"https://github.com/{repo}/pulls",
                        "title": title,
                        "state": "already_existed",
                        "head_branch": head_branch,
                        "base_branch": base_branch,
                        "repo": repo,
                        "already_existed": True,
                    },
                    tool_name=self.name
                )
            return ToolResult.error_result(
                error=f"Failed to create PR: {str(e)}",
                tool_name=self.name
            )


# Backward compatibility aliases for git_file_tools.py
ReadFileTool = GitHubReadFileTool
WriteFileTool = GitHubWriteFileTool
ListFilesTool = GitHubListFilesTool
CreateBranchTool = GitHubCreateBranchTool
GetRepoInfoTool = GitHubGetRepoInfoTool
GitReadFileTool = GitHubReadFileTool
GitWriteFileTool = GitHubWriteFileTool
GitListFilesTool = GitHubListFilesTool
GitCreateBranchTool = GitHubCreateBranchTool
GitGetRepoInfoTool = GitHubGetRepoInfoTool
