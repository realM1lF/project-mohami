"""Git file operation tools for interacting with Git repositories.

These tools provide file-level operations via the Git provider,
allowing AI agents to read, write, and list files in remote repositories.
"""

import base64
from typing import Any, Dict, List, Optional

try:
    import httpx
except ImportError:
    httpx = None

from .base import BaseTool, ToolParameter, ToolParameterType, ToolResult
from ..git_provider.base import FileNotFoundError, RepositoryNotFoundError


class ReadFileTool(BaseTool):
    """Tool to read file content from a Git repository."""
    
    name = "read_file"
    description = "Liest den Inhalt einer Datei aus dem Repository"
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
    
    async def run(self, repo: str, path: str, branch: str = "main") -> ToolResult:
        """Read file content from repository.
        
        Args:
            repo: Repository name (e.g., "owner/repo")
            path: File path within the repository
            branch: Branch name (default: main)
            
        Returns:
            ToolResult with file content or error
        """
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                data={"repo": repo, "path": path, "branch": branch}
            )
        
        try:
            content = await self.git.get_file_content(repo, path, branch)
            return ToolResult.success_result(
                data={
                    "content": content,
                    "path": path,
                    "branch": branch,
                    "repo": repo
                },
                message=f"Successfully read {path} from {repo}@{branch}"
            )
        except FileNotFoundError as e:
            return ToolResult.error_result(
                error=f"File not found: {path}",
                data={"repo": repo, "path": path, "branch": branch}
            )
        except RepositoryNotFoundError as e:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                data={"repo": repo, "path": path, "branch": branch}
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to read file: {str(e)}",
                data={"repo": repo, "path": path, "branch": branch}
            )


class WriteFileTool(BaseTool):
    """Tool to write file content to a Git repository."""
    
    name = "write_file"
    description = "Schreibt Inhalt in eine Datei (erstellt oder überschreibt)"
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
    
    async def run(
        self, 
        repo: str, 
        path: str, 
        content: str, 
        branch: str = "main",
        message: Optional[str] = None
    ) -> ToolResult:
        """Write file content to repository.
        
        Args:
            repo: Repository name (e.g., "owner/repo")
            path: File path within the repository
            content: Content to write to the file
            branch: Branch name (default: main)
            message: Commit message (default: auto-generated)
            
        Returns:
            ToolResult with commit info or error
        """
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                data={"repo": repo, "path": path, "branch": branch}
            )
        
        # Auto-generate commit message if not provided
        if not message:
            message = f"Update {path}"
        
        try:
            # Use create_commit with single file
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
                message=f"Successfully wrote {path} to {repo}@{branch}"
            )
        except RepositoryNotFoundError as e:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                data={"repo": repo, "path": path, "branch": branch}
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to write file: {str(e)}",
                data={"repo": repo, "path": path, "branch": branch}
            )


class ListFilesTool(BaseTool):
    """Tool to list all files in a Git repository."""
    
    name = "list_files"
    description = "Listet alle Dateien im Repository auf"
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
    
    async def run(self, repo: str, branch: str = "main") -> ToolResult:
        """List all files in repository using GitHub API.
        
        Uses GET /repos/{repo}/git/trees/{branch}?recursive=1
        
        Args:
            repo: Repository name (e.g., "owner/repo")
            branch: Branch name (default: main)
            
        Returns:
            ToolResult with list of files or error
        """
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                data={"repo": repo, "branch": branch}
            )
        
        try:
            # Use GitHub API directly to get tree with recursive listing
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
                        data={"repo": repo, "branch": branch}
                    )
                elif response.status_code >= 400:
                    return ToolResult.error_result(
                        error=f"GitHub API error: {response.status_code}",
                        data={"repo": repo, "branch": branch, "response": response.text}
                    )
                
                data = response.json()
                tree = data.get("tree", [])
                
                # Filter only files (type "blob" for files, "tree" for directories)
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
                    message=f"Found {len(files)} files and {len(directories)} directories in {repo}@{branch}"
                )
                
        except RepositoryNotFoundError as e:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                data={"repo": repo, "branch": branch}
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to list files: {str(e)}",
                data={"repo": repo, "branch": branch}
            )


class CreateBranchTool(BaseTool):
    """Tool to create a new branch in a Git repository."""
    
    name = "create_branch"
    description = "Erstellt einen neuen Branch"
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
    
    async def run(
        self, 
        repo: str, 
        branch_name: str, 
        from_branch: str = "main"
    ) -> ToolResult:
        """Create a new branch in the repository.
        
        Args:
            repo: Repository name (e.g., "owner/repo")
            branch_name: Name for the new branch
            from_branch: Source branch to create from (default: main)
            
        Returns:
            ToolResult with branch URL or error
        """
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                data={"repo": repo, "branch_name": branch_name, "from_branch": from_branch}
            )
        
        try:
            branch_url = await self.git.create_branch(repo, branch_name, from_branch)
            
            return ToolResult.success_result(
                data={
                    "branch_name": branch_name,
                    "from_branch": from_branch,
                    "url": branch_url,
                    "repo": repo
                },
                message=f"Successfully created branch '{branch_name}' from '{from_branch}'"
            )
        except RepositoryNotFoundError as e:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                data={"repo": repo, "branch_name": branch_name, "from_branch": from_branch}
            )
        except Exception as e:
            # Handle case where branch already exists
            error_msg = str(e).lower()
            if "already exists" in error_msg or "reference already exists" in error_msg:
                return ToolResult.error_result(
                    error=f"Branch '{branch_name}' already exists",
                    data={
                        "repo": repo, 
                        "branch_name": branch_name, 
                        "from_branch": from_branch,
                        "exists": True
                    }
                )
            return ToolResult.error_result(
                error=f"Failed to create branch: {str(e)}",
                data={"repo": repo, "branch_name": branch_name, "from_branch": from_branch}
            )


class GetRepoInfoTool(BaseTool):
    """Tool to get repository information."""
    
    name = "get_repo_info"
    description = "Holt Repository-Informationen (default_branch, etc.)"
    parameters = [
        ToolParameter(
            name="repo",
            description="Repository name in format 'owner/repo'",
            type=ToolParameterType.STRING,
            required=True
        )
    ]
    
    async def run(self, repo: str) -> ToolResult:
        """Get repository information.
        
        Args:
            repo: Repository name (e.g., "owner/repo")
            
        Returns:
            ToolResult with repository info or error
        """
        if not self.git:
            return ToolResult.error_result(
                error="Git provider not initialized",
                data={"repo": repo}
            )
        
        try:
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
                message=f"Successfully retrieved info for {repo}"
            )
        except RepositoryNotFoundError as e:
            return ToolResult.error_result(
                error=f"Repository not found: {repo}",
                data={"repo": repo}
            )
        except Exception as e:
            return ToolResult.error_result(
                error=f"Failed to get repository info: {str(e)}",
                data={"repo": repo}
            )


# Backward compatibility aliases
GitReadFileTool = ReadFileTool
GitWriteFileTool = WriteFileTool
GitListFilesTool = ListFilesTool
GitCreateBranchTool = CreateBranchTool
GitGetRepoInfoTool = GetRepoInfoTool
