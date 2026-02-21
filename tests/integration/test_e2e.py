"""End-to-End Integration Tests for Mohami System."""

import os
import subprocess
import shutil
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

import pytest
import pytest_asyncio


# =============================================================================
# End-to-End Test: Simple Ticket Workflow
# =============================================================================

class TestSimpleTicketE2E:
    """
    End-to-End Test:
    1. Create ticket: "Add line to README"
    2. Agent processes ticket
    3. PR/Branch is created
    4. Assert: README has new content
    """
    
    @pytest_asyncio.fixture
    async def e2e_setup(self, temp_dir: Path):
        """Set up complete E2E test environment."""
        # Create a bare remote repository
        remote_repo = temp_dir / "e2e_remote.git"
        remote_repo.mkdir()
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=remote_repo,
            capture_output=True,
            check=True
        )
        
        # Create source repository with initial content
        source_repo = temp_dir / "e2e_source"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=source_repo, capture_output=True
        )
        
        # Create initial README
        readme_content = """# E2E Test Repository

COMING SOON
"""
        (source_repo / "README.md").write_text(readme_content)
        subprocess.run(["git", "add", "."], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "remote", "add", "origin", str(remote_repo)],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "push", "origin", "main"],
            cwd=source_repo, capture_output=True
        )
        
        return {
            "remote_repo": remote_repo,
            "source_repo": source_repo,
            "temp_dir": temp_dir
        }
    
    @pytest.mark.asyncio
    async def test_e2e_readme_update_workflow(self, e2e_setup):
        """
        E2E Test: Update README through the complete workflow.
        
        Simulates:
        1. Setting up workspace with repo
        2. Using FileReadTool to read README
        3. Using FileWriteTool to update README  
        4. Using Git tools to commit changes
        5. Verifying the changes
        """
        from src.infrastructure.workspace_manager import WorkspaceManager
        from src.infrastructure.repository_manager import RepositoryManager
        from src.tools.file_tools import FileReadTool, FileWriteTool
        from src.tools.git_tools import GitBranchTool, GitCommitTool, GitStatusTool
        
        remote_repo = e2e_setup["remote_repo"]
        temp_dir = e2e_setup["temp_dir"]
        
        # Setup workspace manager with test config
        config_dir = temp_dir / "config"
        config_dir.mkdir()
        config_path = config_dir / "customers.yaml"
        config_content = f"""
customers:
  e2e-test-customer:
    name: "E2E Test Customer"
    git_provider: github
    repo_url: {remote_repo}
    has_ddev: false
    default_branch: main
"""
        config_path.write_text(config_content)
        
        workspace_manager = WorkspaceManager(config_path=str(config_path))
        
        # Step 1: Setup workspace
        success, message = workspace_manager.setup_workspace(
            customer_id="e2e-test-customer",
            repo_url=str(remote_repo),
            branch="main",
            start_ddev=False
        )
        assert success is True, f"Workspace setup failed: {message}"
        
        workspace = workspace_manager.get_workspace("e2e-test-customer")
        assert workspace.workspace_path.exists()
        
        workspace_path = workspace.workspace_path
        
        # Step 2: Read current README
        read_tool = FileReadTool()
        result = await read_tool.run(path=str(workspace_path / "README.md"))
        
        assert result.success is True
        assert "COMING SOON" in result.data["content"]
        
        # Step 3: Create a new branch
        branch_tool = GitBranchTool()
        result = await branch_tool.run(
            action="create",
            branch_name="feature/e2e-update",
            path=str(workspace_path)
        )
        assert result.success is True
        
        # Step 4: Update README with new content
        new_readme_content = """# E2E Test Repository

This is an updated README with new content!

Added by E2E test.
"""
        write_tool = FileWriteTool()
        result = await write_tool.run(
            path=str(workspace_path / "README.md"),
            content=new_readme_content
        )
        assert result.success is True
        
        # Step 5: Commit the changes
        commit_tool = GitCommitTool()
        result = await commit_tool.run(
            message="[E2E-123] Update README with new content",
            path=str(workspace_path)
        )
        assert result.success is True
        assert "commit_hash" in result.data
        
        # Step 6: Verify changes with status tool
        status_tool = GitStatusTool()
        result = await status_tool.run(path=str(workspace_path))
        
        assert result.success is True
        assert result.data["branch"] == "feature/e2e-update"
        assert result.data["total_changes"] == 0  # All changes committed
        
        # Step 7: Read updated README to confirm changes
        result = await read_tool.run(path=str(workspace_path / "README.md"))
        
        assert result.success is True
        assert "COMING SOON" not in result.data["content"]
        assert "updated README with new content" in result.data["content"]
        assert "Added by E2E test" in result.data["content"]
    
    @pytest.mark.asyncio
    async def test_e2e_tool_registry_workflow(self, e2e_setup):
        """
        E2E Test: Complete workflow using ToolRegistry.
        
        Tests:
        1. Register multiple tools
        2. Use registry to discover and execute tools
        3. Complete file operation workflow
        """
        from src.tools.registry import ToolRegistry
        from src.tools.file_tools import FileReadTool, FileWriteTool, FileListTool
        from src.tools.git_tools import GitBranchTool, GitStatusTool
        
        temp_dir = e2e_setup["temp_dir"]
        
        # Create a test workspace
        workspace_path = temp_dir / "registry_test_workspace"
        workspace_path.mkdir()
        subprocess.run(["git", "init"], cwd=workspace_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=workspace_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=workspace_path, capture_output=True
        )
        
        # Step 1: Setup ToolRegistry with all tools
        registry = ToolRegistry()
        registry.register(FileReadTool(), category="file")
        registry.register(FileWriteTool(), category="file")
        registry.register(FileListTool(), category="file")
        registry.register(GitBranchTool(), category="git")
        registry.register(GitStatusTool(), category="git")
        
        assert len(registry) == 5
        
        # Step 2: Use registry to get tools by category
        file_tools = registry.list_by_category("file")
        assert len(file_tools) == 3
        
        # Step 3: Create a file using write tool from registry
        write_tool = registry.get("file_write")
        result = await write_tool.run(
            path=str(workspace_path / "test.txt"),
            content="Registry test content"
        )
        assert result.success is True
        
        # Step 4: List files using registry
        list_tool = registry.get("file_list")
        result = await list_tool.run(path=str(workspace_path))
        assert result.success is True
        assert "test.txt" in [f["name"] for f in result.data["files"]]
        
        # Step 5: Read file using registry
        read_tool = registry.get("file_read")
        result = await read_tool.run(path=str(workspace_path / "test.txt"))
        assert result.success is True
        assert result.data["content"] == "Registry test content"
        
        # Step 6: Get LLM schemas from registry
        schemas = registry.get_schemas_for_llm("openai")
        assert len(schemas) == 5
        assert all(s["type"] == "function" for s in schemas)
    
    @pytest.mark.asyncio
    async def test_e2e_memory_integration(self, e2e_setup):
        """
        E2E Test: Memory system integration.
        
        Tests:
        1. Short-term memory for session data
        2. Tool execution context through memory
        """
        from src.memory.short_term import InMemoryBuffer
        from src.tools.file_tools import FileReadTool, FileWriteTool
        
        temp_dir = e2e_setup["temp_dir"]
        
        # Create test workspace
        workspace_path = temp_dir / "memory_test_workspace"
        workspace_path.mkdir()
        
        # Step 1: Initialize short-term memory
        memory = InMemoryBuffer(customer_id="e2e-memory-test")
        
        # Step 2: Store session context
        memory.set("workspace_path", str(workspace_path))
        memory.set("current_task", "update_documentation")
        memory.set("files_modified", [], ttl=3600)
        
        # Step 3: Execute file operations with memory tracking
        write_tool = FileWriteTool()
        result = await write_tool.run(
            path=str(workspace_path / "doc.txt"),
            content="Documentation content"
        )
        assert result.success is True
        
        # Track in memory
        files_modified = memory.get("files_modified", [])
        files_modified.append("doc.txt")
        memory.set("files_modified", files_modified)
        
        # Step 4: Add reasoning steps
        memory.add_reasoning_step("observe", "Found missing documentation")
        memory.add_reasoning_step("plan", "Create doc.txt with content")
        memory.add_reasoning_step("act", "Created documentation file")
        
        # Step 5: Verify memory state
        assert memory.get("workspace_path") == str(workspace_path)
        assert "doc.txt" in memory.get("files_modified")
        
        reasoning = memory.get_reasoning_steps()
        assert len(reasoning) == 3
        
        session_info = memory.get_session_info()
        assert session_info["data_count"] >= 3
        assert session_info["reasoning_steps_count"] == 3
    
    @pytest.mark.asyncio
    async def test_e2e_github_read_tool_integration(self, mock_git_provider):
        """
        E2E Test: GitHub Read Tool integration.
        
        Tests the GitHub Read Tool with a mock provider simulating
        the complete workflow from reading to processing.
        """
        from src.tools.git_tools import GitHubReadFileTool, GitHubWriteFileTool
        from src.tools.registry import ToolRegistry
        
        # Setup mock provider responses
        mock_git_provider.get_file_content = AsyncMock(return_value="""# Project README

COMING SOON

This project is under development.
""")
        mock_git_provider.create_branch = AsyncMock(
            return_value="https://github.com/test/repo/tree/feature/update-readme"
        )
        mock_git_provider.create_commit = AsyncMock(return_value="abc123def456789")
        
        # Step 1: Create registry and register GitHub tools
        registry = ToolRegistry()
        registry.register(GitHubReadFileTool(git_provider=mock_git_provider), category="github")
        registry.register(GitHubWriteFileTool(git_provider=mock_git_provider), category="github")
        
        # Step 2: Read file from GitHub
        read_tool = registry.get("github_read_file")
        result = await read_tool.run(
            repo="test/repo",
            path="README.md",
            branch="main"
        )
        
        assert result.success is True
        assert "COMING SOON" in result.data["content"]
        assert result.data["repo"] == "test/repo"
        
        # Step 3: Update file via GitHub
        write_tool = registry.get("github_write_file")
        result = await write_tool.run(
            repo="test/repo",
            path="README.md",
            content="# Updated README\n\nProject is now live!",
            branch="main",
            message="Update README with project status"
        )
        
        assert result.success is True
        assert result.data["commit_sha"] == "abc123def456789"
        
        # Verify mock calls
        mock_git_provider.create_commit.assert_awaited_once()
        call_kwargs = mock_git_provider.create_commit.call_args.kwargs
        assert call_kwargs["repo"] == "test/repo"
        assert call_kwargs["branch"] == "main"


# =============================================================================
# Integration Test: Multiple Tools Working Together
# =============================================================================

class TestMultiToolIntegration:
    """Tests for multiple tools working together in workflows."""
    
    @pytest.mark.asyncio
    async def test_file_search_and_replace_workflow(self, temp_dir: Path):
        """
        Integration test: Search for files, read them, and update content.
        """
        from src.tools.file_tools import FileSearchTool, FileReadTool, FileWriteTool, FileListTool
        
        # Setup: Create files with patterns
        (temp_dir / "module1.py").write_text("def old_function():\n    pass")
        (temp_dir / "module2.py").write_text("def old_function():\n    return 42")
        (temp_dir / "readme.txt").write_text("This is documentation")
        
        # Step 1: Search for files containing pattern
        search_tool = FileSearchTool()
        result = await search_tool.run(
            pattern="old_function",
            path=str(temp_dir),
            file_pattern="*.py"
        )
        
        assert result.success is True
        assert result.data["total_matches"] == 2
        
        # Step 2: Read one of the files
        py_files = [m["file"] for m in result.data["matches"]]
        read_tool = FileReadTool()
        result = await read_tool.run(path=py_files[0])
        
        assert result.success is True
        assert "old_function" in result.data["content"]
        
        # Step 3: Update the file
        new_content = result.data["content"].replace("old_function", "new_function")
        write_tool = FileWriteTool()
        result = await write_tool.run(
            path=py_files[0],
            content=new_content
        )
        
        assert result.success is True
        
        # Step 4: Verify update
        result = await read_tool.run(path=py_files[0])
        assert "new_function" in result.data["content"]
        assert "old_function" not in result.data["content"]
    
    @pytest.mark.asyncio
    async def test_git_workflow_with_file_operations(self, temp_dir: Path):
        """
        Integration test: Complete git workflow with file operations.
        """
        from src.tools.file_tools import FileWriteTool
        from src.tools.git_tools import GitBranchTool, GitCommitTool, GitStatusTool
        
        # Setup: Create git repo
        repo_path = temp_dir / "git_workflow_repo"
        repo_path.mkdir()
        subprocess.run(["git", "init"], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_path, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_path, capture_output=True
        )
        (repo_path / "initial.txt").write_text("initial")
        subprocess.run(["git", "add", "."], cwd=repo_path, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=repo_path, capture_output=True
        )
        
        # Step 1: Check initial status
        status_tool = GitStatusTool()
        result = await status_tool.run(path=str(repo_path))
        assert result.success is True
        assert result.data["total_changes"] == 0
        
        # Step 2: Create feature branch
        branch_tool = GitBranchTool()
        result = await branch_tool.run(
            action="create",
            branch_name="feature/new-feature",
            path=str(repo_path)
        )
        assert result.success is True
        
        # Step 3: Add new file
        write_tool = FileWriteTool()
        result = await write_tool.run(
            path=str(repo_path / "feature.py"),
            content="def new_feature():\n    return 'awesome'"
        )
        assert result.success is True
        
        # Step 4: Check status (should show untracked)
        result = await status_tool.run(path=str(repo_path))
        assert result.success is True
        assert result.data["total_changes"] == 1
        assert "feature.py" in result.data["untracked"]
        
        # Step 5: Commit changes
        commit_tool = GitCommitTool()
        result = await commit_tool.run(
            message="Add new feature",
            path=str(repo_path)
        )
        assert result.success is True
        
        # Step 6: Verify clean status
        result = await status_tool.run(path=str(repo_path))
        assert result.success is True
        assert result.data["total_changes"] == 0


# =============================================================================
# Error Handling Integration Tests
# =============================================================================

class TestErrorHandlingIntegration:
    """Integration tests for error handling across components."""
    
    @pytest.mark.asyncio
    async def test_tool_error_propagation(self, temp_dir: Path):
        """Test that tool errors are properly propagated."""
        from src.tools.file_tools import FileReadTool, FileWriteTool
        
        # Test reading non-existent file
        read_tool = FileReadTool()
        result = await read_tool.run(path=str(temp_dir / "nonexistent.txt"))
        
        assert result.success is False
        assert result.error is not None
        assert "File not found" in result.error
        
        # Test reading directory as file
        result = await read_tool.run(path=str(temp_dir))
        assert result.success is False
        assert "not a file" in result.error
    
    @pytest.mark.asyncio
    async def test_git_tool_errors(self, temp_dir: Path):
        """Test git tool error handling."""
        from src.tools.git_tools import GitBranchTool, GitStatusTool
        
        # Test operations in non-git directory
        status_tool = GitStatusTool()
        result = await status_tool.run(path=str(temp_dir))
        
        assert result.success is False
        assert "Not a git repository" in result.error
        
        # Test branch operations without required params
        branch_tool = GitBranchTool()
        result = await branch_tool.run(
            action="create",
            path=str(temp_dir)  # Not a git repo
        )
        
        assert result.success is False
    
    def test_repository_manager_error_handling(self, temp_dir: Path):
        """Test RepositoryManager error handling."""
        from src.infrastructure.repository_manager import RepositoryManager
        
        manager = RepositoryManager(base_workspaces_path=str(temp_dir / "workspaces"))
        
        # Test operations on non-existent repo
        success, message = manager.pull_changes("nonexistent")
        assert success is False
        
        # Test checkout on non-existent repo
        success, message = manager.checkout_branch("nonexistent", "main")
        assert success is False
        
        # Test get info on non-existent repo
        info = manager.get_repo_info("nonexistent")
        assert info is None
