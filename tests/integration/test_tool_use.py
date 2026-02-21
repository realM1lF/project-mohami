"""Integration tests for Tool-Use Framework."""

import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio

from src.tools.base import ToolResult
from src.tools.file_tools import FileReadTool, FileWriteTool, FileListTool, FileSearchTool
from src.tools.git_tools import (
    GitHubReadFileTool, GitHubWriteFileTool, GitHubListFilesTool,
    GitBranchTool, GitCommitTool, GitStatusTool
)
from src.tools.registry import ToolRegistry


# =============================================================================
# File Tool Tests
# =============================================================================

class TestFileReadTool:
    """Tests for FileReadTool."""
    
    @pytest_asyncio.fixture
    async def test_file(self, temp_dir: Path) -> Path:
        """Create a test file."""
        test_file = temp_dir / "test_readme.md"
        test_file.write_text("# Test README\n\nCOMING SOON\n\nMore content here.")
        return test_file
    
    @pytest.mark.asyncio
    async def test_read_existing_file(self, test_file: Path):
        """Test reading an existing file."""
        tool = FileReadTool()
        result = await tool.run(path=str(test_file))
        
        assert result.success is True
        assert "COMING SOON" in result.data["content"]
        assert result.data["path"] == str(test_file.resolve())
    
    @pytest.mark.asyncio
    async def test_read_file_with_limit(self, test_file: Path):
        """Test reading file with line limit."""
        tool = FileReadTool()
        result = await tool.run(path=str(test_file), limit=2)
        
        assert result.success is True
        assert "# Test README" in result.data["content"]
        assert "More content" not in result.data["content"]
        assert "more lines" in result.data["content"]
    
    @pytest.mark.asyncio
    async def test_read_nonexistent_file(self, temp_dir: Path):
        """Test reading a file that doesn't exist."""
        tool = FileReadTool()
        result = await tool.run(path=str(temp_dir / "nonexistent.txt"))
        
        assert result.success is False
        assert "File not found" in result.error
    
    @pytest.mark.asyncio
    async def test_read_directory_as_file(self, temp_dir: Path):
        """Test reading a directory path as file."""
        tool = FileReadTool()
        result = await tool.run(path=str(temp_dir))
        
        assert result.success is False
        assert "not a file" in result.error


class TestFileWriteTool:
    """Tests for FileWriteTool."""
    
    @pytest.mark.asyncio
    async def test_write_new_file(self, temp_dir: Path):
        """Test writing a new file."""
        tool = FileWriteTool()
        test_file = temp_dir / "new_file.txt"
        
        result = await tool.run(
            path=str(test_file),
            content="Hello, World!"
        )
        
        assert result.success is True
        assert test_file.exists()
        assert test_file.read_text() == "Hello, World!"
        assert result.data["action"] == "written"
        assert result.data["file_existed"] is False
    
    @pytest.mark.asyncio
    async def test_overwrite_existing_file(self, temp_dir: Path):
        """Test overwriting an existing file."""
        tool = FileWriteTool()
        test_file = temp_dir / "existing.txt"
        test_file.write_text("Old content")
        
        result = await tool.run(
            path=str(test_file),
            content="New content"
        )
        
        assert result.success is True
        assert test_file.read_text() == "New content"
        assert result.data["file_existed"] is True
    
    @pytest.mark.asyncio
    async def test_append_to_file(self, temp_dir: Path):
        """Test appending to a file."""
        tool = FileWriteTool()
        test_file = temp_dir / "append.txt"
        test_file.write_text("First line\n")
        
        result = await tool.run(
            path=str(test_file),
            content="Second line\n",
            append=True
        )
        
        assert result.success is True
        assert result.data["action"] == "appended"
        content = test_file.read_text()
        assert "First line" in content
        assert "Second line" in content
    
    @pytest.mark.asyncio
    async def test_create_nested_directories(self, temp_dir: Path):
        """Test that nested directories are created."""
        tool = FileWriteTool()
        nested_file = temp_dir / "deep" / "nested" / "path" / "file.txt"
        
        result = await tool.run(
            path=str(nested_file),
            content="Nested content"
        )
        
        assert result.success is True
        assert nested_file.exists()
        assert nested_file.read_text() == "Nested content"


class TestFileListTool:
    """Tests for FileListTool."""
    
    @pytest_asyncio.fixture
    async def test_directory(self, temp_dir: Path) -> Path:
        """Create a test directory structure."""
        # Create files
        (temp_dir / "file1.txt").write_text("content1")
        (temp_dir / "file2.py").write_text("content2")
        
        # Create subdirectory
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.txt").write_text("content3")
        
        return temp_dir
    
    @pytest.mark.asyncio
    async def test_list_directory(self, test_directory: Path):
        """Test listing directory contents."""
        tool = FileListTool()
        result = await tool.run(path=str(test_directory))
        
        assert result.success is True
        files = [f["name"] for f in result.data["files"]]
        dirs = [d["name"] for d in result.data["directories"]]
        
        assert "file1.txt" in files
        assert "file2.py" in files
        assert "subdir" in dirs
        assert result.data["total_count"] == 3
    
    @pytest.mark.asyncio
    async def test_list_recursive(self, test_directory: Path):
        """Test recursive directory listing."""
        tool = FileListTool()
        result = await tool.run(path=str(test_directory), recursive=True)
        
        assert result.success is True
        files = [f["name"] for f in result.data["files"]]
        
        assert "file1.txt" in files
        assert "file2.py" in files
        assert "file3.txt" in files  # From subdirectory
    
    @pytest.mark.asyncio
    async def test_list_with_pattern(self, test_directory: Path):
        """Test listing with file pattern."""
        tool = FileListTool()
        result = await tool.run(path=str(test_directory), pattern="*.txt")
        
        assert result.success is True
        files = [f["name"] for f in result.data["files"]]
        
        assert "file1.txt" in files
        assert "file2.py" not in files  # Should be filtered out


class TestFileSearchTool:
    """Tests for FileSearchTool."""
    
    @pytest_asyncio.fixture
    async def test_directory(self, temp_dir: Path) -> Path:
        """Create a test directory with searchable files."""
        (temp_dir / "file1.py").write_text("def hello():\n    return 'world'")
        (temp_dir / "file2.txt").write_text("Hello world in text")
        
        subdir = temp_dir / "subdir"
        subdir.mkdir()
        (subdir / "file3.py").write_text("class HelloWorld:\n    pass")
        
        return temp_dir
    
    @pytest.mark.asyncio
    async def test_search_pattern(self, test_directory: Path):
        """Test searching for a pattern."""
        tool = FileSearchTool()
        result = await tool.run(pattern="hello", path=str(test_directory))
        
        assert result.success is True
        assert result.data["total_matches"] >= 2
        
        matches = result.data["matches"]
        files_matched = set(m["file"] for m in matches)
        assert len(files_matched) >= 2
    
    @pytest.mark.asyncio
    async def test_search_with_file_pattern(self, test_directory: Path):
        """Test searching with file pattern filter."""
        tool = FileSearchTool()
        result = await tool.run(
            pattern="hello",
            path=str(test_directory),
            file_pattern="*.py"
        )
        
        assert result.success is True
        
        for match in result.data["matches"]:
            assert match["file"].endswith(".py")
    
    @pytest.mark.asyncio
    async def test_search_max_results(self, test_directory: Path):
        """Test search with max results limit."""
        tool = FileSearchTool()
        result = await tool.run(
            pattern="hello",
            path=str(test_directory),
            max_results=1
        )
        
        assert result.success is True
        assert result.data["total_matches"] == 1


# =============================================================================
# GitHub Remote Tool Tests (with mocks)
# =============================================================================

class TestGitHubReadFileTool:
    """Tests for GitHubReadFileTool with mocked Git provider."""
    
    @pytest.mark.asyncio
    async def test_read_file_from_github(self, mock_git_provider):
        """Test reading file via GitHub API."""
        tool = GitHubReadFileTool(git_provider=mock_git_provider)
        result = await tool.run(repo="test/repo", path="README.md", branch="main")
        
        assert result.success is True
        assert "COMING SOON" in result.data["content"]
        assert result.data["path"] == "README.md"
        assert result.data["branch"] == "main"
        
        # Verify mock was called correctly
        mock_git_provider.get_file_content.assert_awaited_once_with(
            "test/repo", "README.md", "main"
        )
    
    @pytest.mark.asyncio
    async def test_read_file_no_provider(self):
        """Test that tool fails without git provider."""
        tool = GitHubReadFileTool(git_provider=None)
        result = await tool.run(repo="test/repo", path="README.md")
        
        assert result.success is False
        assert "Git provider not initialized" in result.error


class TestGitHubWriteFileTool:
    """Tests for GitHubWriteFileTool with mocked Git provider."""
    
    @pytest.mark.asyncio
    async def test_write_file_to_github(self, mock_git_provider):
        """Test writing file via GitHub API."""
        tool = GitHubWriteFileTool(git_provider=mock_git_provider)
        result = await tool.run(
            repo="test/repo",
            path="new_file.txt",
            content="New content",
            branch="main",
            message="Add new file"
        )
        
        assert result.success is True
        assert result.data["commit_sha"] == "abc123def456"
        
        # Verify mock was called
        mock_git_provider.create_commit.assert_awaited_once()
    
    @pytest.mark.asyncio
    async def test_write_file_default_message(self, mock_git_provider):
        """Test that default commit message is generated."""
        tool = GitHubWriteFileTool(git_provider=mock_git_provider)
        result = await tool.run(
            repo="test/repo",
            path="test.txt",
            content="Content",
            branch="main"
        )
        
        assert result.success is True
        # Check that create_commit was called with default message
        call_args = mock_git_provider.create_commit.call_args
        assert "Update test.txt" in str(call_args)


class TestGitHubListFilesTool:
    """Tests for GitHubListFilesTool."""
    
    @pytest.mark.asyncio
    async def test_list_files_mock(self, mock_git_provider):
        """Test listing files with mocked provider (token only)."""
        # This test validates the tool structure
        tool = GitHubListFilesTool(git_provider=mock_git_provider)
        
        # The actual API call would require httpx, which we mock
        # Just verify the tool is properly configured
        assert tool.name == "github_list_files"
        assert "Listet alle Dateien" in tool.description


# =============================================================================
# Local Git Tool Tests
# =============================================================================

class TestLocalGitTools:
    """Tests for local git tools using actual git operations."""
    
    @pytest_asyncio.fixture
    async def git_repo(self, temp_dir: Path) -> Path:
        """Create a temporary git repository."""
        import subprocess
        
        repo_dir = temp_dir / "git_repo"
        repo_dir.mkdir()
        
        # Initialize git repo
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.email", "test@test.com"], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "config", "user.name", "Test User"], cwd=repo_dir, capture_output=True)
        
        # Create initial file and commit
        (repo_dir / "README.md").write_text("# Initial")
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(["git", "commit", "-m", "Initial commit"], cwd=repo_dir, capture_output=True)
        
        return repo_dir
    
    @pytest.mark.asyncio
    async def test_git_branch_list(self, git_repo: Path):
        """Test listing branches."""
        tool = GitBranchTool()
        result = await tool.run(action="list", path=str(git_repo))
        
        assert result.success is True
        assert result.data["count"] >= 1
        
        branches = [b["name"] for b in result.data["branches"]]
        assert any("main" in b or "master" in b for b in branches)
    
    @pytest.mark.asyncio
    async def test_git_branch_create(self, git_repo: Path):
        """Test creating a branch."""
        tool = GitBranchTool()
        result = await tool.run(
            action="create",
            branch_name="feature/test",
            path=str(git_repo)
        )
        
        assert result.success is True
        assert result.data["action"] == "created"
        assert result.data["branch"] == "feature/test"
    
    @pytest.mark.asyncio
    async def test_git_status(self, git_repo: Path):
        """Test git status."""
        # Create a new file
        (git_repo / "new_file.txt").write_text("New content")
        
        tool = GitStatusTool()
        result = await tool.run(path=str(git_repo))
        
        assert result.success is True
        assert result.data["total_changes"] >= 1
        assert "new_file.txt" in result.data["untracked"]
    
    @pytest.mark.asyncio
    async def test_git_commit(self, git_repo: Path):
        """Test creating a commit."""
        # Stage a new file
        (git_repo / "commit_file.txt").write_text("Commit content")
        
        tool = GitCommitTool()
        result = await tool.run(
            message="Test commit",
            files=["commit_file.txt"],
            path=str(git_repo)
        )
        
        assert result.success is True
        assert result.data["message"] == "Test commit"
        assert "commit_hash" in result.data


# =============================================================================
# Tool Registry Tests
# =============================================================================

class TestToolRegistryIntegration:
    """Integration tests for ToolRegistry."""
    
    @pytest.mark.asyncio
    async def test_register_and_use_file_tools(self, tool_registry, temp_dir: Path):
        """Test registering and using file tools together."""
        # Register file tools
        tool_registry.register(FileReadTool(), category="file")
        tool_registry.register(FileWriteTool(), category="file")
        tool_registry.register(FileListTool(), category="file")
        
        # Verify registration
        assert len(tool_registry) == 3
        assert tool_registry.is_registered("file_read")
        assert tool_registry.is_registered("file_write")
        assert tool_registry.is_registered("file_list")
        
        # Use write tool
        test_file = temp_dir / "registry_test.txt"
        write_tool = tool_registry.get("file_write")
        result = await write_tool.run(path=str(test_file), content="Registry test")
        assert result.success is True
        
        # Use read tool
        read_tool = tool_registry.get("file_read")
        result = await read_tool.run(path=str(test_file))
        assert result.success is True
        assert "Registry test" in result.data["content"]
    
    def test_get_schemas_for_llm_integration(self, tool_registry):
        """Test getting schemas for LLM consumption."""
        tool_registry.register(FileReadTool(), category="file")
        tool_registry.register(GitBranchTool(), category="git")
        
        # Test OpenAI format
        openai_schemas = tool_registry.get_schemas_for_llm("openai")
        assert len(openai_schemas) == 2
        assert all(s["type"] == "function" for s in openai_schemas)
        
        # Test Anthropic format
        anthropic_schemas = tool_registry.get_schemas_for_llm("anthropic")
        assert len(anthropic_schemas) == 2
        assert all("name" in s for s in anthropic_schemas)
    
    def test_category_organization(self, tool_registry):
        """Test tool categorization."""
        tool_registry.register(FileReadTool(), category="file")
        tool_registry.register(FileWriteTool(), category="file")
        tool_registry.register(GitBranchTool(), category="git")
        tool_registry.register(GitCommitTool(), category="git")
        
        # List by category
        file_tools = tool_registry.list_by_category("file")
        git_tools = tool_registry.list_by_category("git")
        
        assert len(file_tools) == 2
        assert len(git_tools) == 2
        
        tool_names = [t.name for t in file_tools]
        assert "file_read" in tool_names
        assert "file_write" in tool_names
