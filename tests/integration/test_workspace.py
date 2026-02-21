"""Integration tests for Workspace and Repository Management."""

import os
import subprocess
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import pytest_asyncio


# =============================================================================
# Repository Manager Tests
# =============================================================================

class TestRepositoryManager:
    """Tests for RepositoryManager."""
    
    @pytest_asyncio.fixture
    async def git_repo_remote(self, temp_dir: Path) -> Path:
        """Create a bare git repository to simulate remote."""
        remote_dir = temp_dir / "remote_repo.git"
        remote_dir.mkdir()
        
        # Initialize bare repo
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=remote_dir,
            capture_output=True,
            check=True
        )
        
        return remote_dir
    
    @pytest_asyncio.fixture
    async def git_repo_with_content(self, temp_dir: Path) -> Path:
        """Create a git repository with some content."""
        repo_dir = temp_dir / "source_repo"
        repo_dir.mkdir()
        
        subprocess.run(["git", "init"], cwd=repo_dir, capture_output=True, check=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=repo_dir, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=repo_dir, capture_output=True
        )
        
        # Create content
        (repo_dir / "README.md").write_text("# Test Repository\n\nThis is a test.")
        (repo_dir / "src" / "main.py").parent.mkdir(parents=True)
        (repo_dir / "src" / "main.py").write_text("print('hello')")
        
        subprocess.run(["git", "add", "."], cwd=repo_dir, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial commit"],
            cwd=repo_dir, capture_output=True
        )
        
        return repo_dir
    
    def test_get_workspace_path(self, repository_manager, workspace_base_path):
        """Test getting workspace path."""
        path = repository_manager.get_workspace_path("test_customer")
        assert path == workspace_base_path / "test_customer"
    
    def test_detect_provider_github(self, repository_manager):
        """Test detecting GitHub provider."""
        from src.infrastructure.repository_manager import GitProvider
        
        provider = repository_manager._detect_provider("https://github.com/user/repo")
        assert provider == GitProvider.GITHUB
        
        provider = repository_manager._detect_provider("git@github.com:user/repo.git")
        assert provider == GitProvider.GITHUB
    
    def test_detect_provider_bitbucket(self, repository_manager):
        """Test detecting Bitbucket provider."""
        from src.infrastructure.repository_manager import GitProvider
        
        provider = repository_manager._detect_provider("https://bitbucket.org/user/repo")
        assert provider == GitProvider.BITBUCKET
    
    def test_normalize_url_https(self, repository_manager):
        """Test normalizing HTTPS URL."""
        from src.infrastructure.repository_manager import GitProvider
        
        url = repository_manager._normalize_url(
            "https://github.com/user/repo",
            GitProvider.GITHUB
        )
        assert url == "https://github.com/user/repo"
    
    def test_normalize_url_ssh(self, repository_manager):
        """Test normalizing SSH URL."""
        from src.infrastructure.repository_manager import GitProvider
        
        url = repository_manager._normalize_url(
            "git@github.com:user/repo.git",
            GitProvider.GITHUB
        )
        assert url == "https://github.com/user/repo"
    
    def test_normalize_url_shorthand(self, repository_manager):
        """Test normalizing owner/repo shorthand."""
        from src.infrastructure.repository_manager import GitProvider
        
        url = repository_manager._normalize_url(
            "owner/repo",
            GitProvider.GITHUB
        )
        assert url == "https://github.com/owner/repo"
    
    def test_get_repo_name_from_url(self, repository_manager):
        """Test extracting repo name from URL."""
        name = repository_manager._get_repo_name_from_url(
            "https://github.com/user/my-repo"
        )
        assert name == "my-repo"
        
        name = repository_manager._get_repo_name_from_url(
            "https://github.com/user/repo.git"
        )
        assert name == "repo"
    
    def test_clone_repo_success(self, repository_manager, git_repo_with_content):
        """Test successful repository cloning."""
        # Clone the local test repo
        success, message = repository_manager.clone_repo(
            customer_id="test_clone",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        assert success is True
        assert "cloned successfully" in message.lower() or "successfully" in message.lower()
        
        # Verify clone worked
        workspace = repository_manager.get_workspace_path("test_clone")
        assert workspace.exists()
        assert (workspace / ".git").exists()
        assert (workspace / "README.md").exists()
    
    def test_clone_repo_already_exists(self, repository_manager, git_repo_with_content):
        """Test cloning when repo already exists (should pull)."""
        # First clone
        repository_manager.clone_repo(
            customer_id="test_double",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        # Second clone should pull
        success, message = repository_manager.clone_repo(
            customer_id="test_double",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        assert success is True
    
    def test_get_repo_info(self, repository_manager, git_repo_with_content):
        """Test getting repository info."""
        # Clone first
        repository_manager.clone_repo(
            customer_id="test_info",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        info = repository_manager.get_repo_info("test_info")
        
        assert info is not None
        assert info["customer_id"] == "test_info"
        assert "current_branch" in info
        assert "last_commit" in info
        assert "recent_commits" in info
    
    def test_get_repo_info_not_cloned(self, repository_manager):
        """Test getting info for non-existent repo."""
        info = repository_manager.get_repo_info("nonexistent")
        assert info is None
    
    def test_checkout_branch(self, repository_manager, git_repo_with_content):
        """Test checking out a branch."""
        # Clone first
        repository_manager.clone_repo(
            customer_id="test_branch",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        # Create a new branch
        success, message = repository_manager.create_branch(
            customer_id="test_branch",
            branch="feature/test",
            base_branch="main"
        )
        
        assert success is True
        assert "feature/test" in message
    
    def test_list_branches(self, repository_manager, git_repo_with_content):
        """Test listing branches."""
        # Clone first
        repository_manager.clone_repo(
            customer_id="test_branches",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        success, branches = repository_manager.list_branches("test_branches")
        
        assert success is True
        assert len(branches) >= 1
        assert any("main" in b or "master" in b for b in branches)
    
    def test_cleanup_repo(self, repository_manager, git_repo_with_content):
        """Test cleaning up a repository."""
        # Clone first
        repository_manager.clone_repo(
            customer_id="test_cleanup",
            repo_url=str(git_repo_with_content),
            branch="main"
        )
        
        workspace = repository_manager.get_workspace_path("test_cleanup")
        assert workspace.exists()
        
        # Cleanup
        success, message = repository_manager.cleanup_repo("test_cleanup")
        
        assert success is True
        assert not workspace.exists()


# =============================================================================
# Workspace Manager Tests
# =============================================================================

class TestWorkspaceManager:
    """Tests for WorkspaceManager."""
    
    def test_get_workspace(self, workspace_manager):
        """Test getting a workspace."""
        workspace = workspace_manager.get_workspace("test-customer")
        
        assert workspace is not None
        assert workspace.customer_id == "test-customer"
        assert workspace.name == "Test Customer"
    
    def test_get_workspace_not_found(self, workspace_manager):
        """Test getting non-existent workspace."""
        workspace = workspace_manager.get_workspace("nonexistent")
        assert workspace is None
    
    def test_list_workspaces(self, workspace_manager):
        """Test listing all workspaces."""
        workspaces = workspace_manager.list_workspaces()
        
        assert len(workspaces) >= 1
        ids = [w.customer_id for w in workspaces]
        assert "test-customer" in ids
    
    def test_setup_workspace_new_customer(self, workspace_manager, temp_dir):
        """Test setting up workspace for new customer via URL."""
        # Create a local git repo to clone from
        source_repo = temp_dir / "source_for_setup"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=source_repo, capture_output=True
        )
        (source_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=source_repo, capture_output=True
        )
        
        # Setup workspace
        success, message = workspace_manager.setup_workspace(
            customer_id="new_customer",
            repo_url=str(source_repo),
            branch="main",
            start_ddev=False
        )
        
        assert success is True
        
        # Verify workspace exists
        workspace = workspace_manager.get_workspace("new_customer")
        assert workspace is not None
        assert workspace.workspace_path.exists()
    
    def test_get_status_existing_workspace(self, workspace_manager, temp_dir):
        """Test getting workspace status."""
        # First setup a workspace
        source_repo = temp_dir / "source_for_status"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=source_repo, capture_output=True
        )
        (source_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=source_repo, capture_output=True
        )
        
        workspace_manager.setup_workspace(
            customer_id="status_test",
            repo_url=str(source_repo),
            start_ddev=False
        )
        
        status = workspace_manager.get_status("status_test")
        
        assert "error" not in status
        assert status["customer_id"] == "status_test"
        assert "workspace_path" in status
        assert "status" in status
    
    def test_get_status_not_found(self, workspace_manager):
        """Test getting status for non-existent workspace."""
        status = workspace_manager.get_status("nonexistent")
        
        assert "error" in status
    
    def test_execute_command_local(self, workspace_manager, temp_dir):
        """Test executing command in workspace."""
        # Setup workspace
        source_repo = temp_dir / "source_for_exec"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=source_repo, capture_output=True
        )
        (source_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=source_repo, capture_output=True
        )
        
        workspace_manager.setup_workspace(
            customer_id="exec_test",
            repo_url=str(source_repo),
            start_ddev=False
        )
        
        # Execute command
        success, stdout, stderr = workspace_manager.execute_command(
            customer_id="exec_test",
            command="echo 'Hello from workspace'",
            use_ddev=False
        )
        
        assert success is True
        assert "Hello from workspace" in stdout
    
    def test_pull_changes(self, workspace_manager, temp_dir):
        """Test pulling changes from remote."""
        # Setup remote and clone
        remote_repo = temp_dir / "remote_for_pull.git"
        remote_repo.mkdir()
        subprocess.run(
            ["git", "init", "--bare"],
            cwd=remote_repo,
            capture_output=True
        )
        
        # Create source repo and push to remote
        source_repo = temp_dir / "source_for_pull"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=source_repo, capture_output=True
        )
        (source_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
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
        
        # Clone via workspace manager
        workspace_manager.setup_workspace(
            customer_id="pull_test",
            repo_url=str(remote_repo),
            start_ddev=False
        )
        
        # Pull changes
        success, message = workspace_manager.pull_changes("pull_test")
        
        assert success is True
    
    def test_list_available_workspaces(self, workspace_manager):
        """Test listing available workspaces."""
        workspaces = workspace_manager.list_available_workspaces()
        
        assert len(workspaces) >= 1
        assert all("customer_id" in w for w in workspaces)
    
    def test_cleanup_workspace(self, workspace_manager, temp_dir):
        """Test cleaning up workspace."""
        # Setup workspace
        source_repo = temp_dir / "source_for_cleanup"
        source_repo.mkdir()
        subprocess.run(["git", "init"], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "config", "user.email", "test@test.com"],
            cwd=source_repo, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.name", "Test User"],
            cwd=source_repo, capture_output=True
        )
        (source_repo / "README.md").write_text("# Test")
        subprocess.run(["git", "add", "."], cwd=source_repo, capture_output=True)
        subprocess.run(
            ["git", "commit", "-m", "Initial"],
            cwd=source_repo, capture_output=True
        )
        
        workspace_manager.setup_workspace(
            customer_id="cleanup_test",
            repo_url=str(source_repo),
            start_ddev=False
        )
        
        workspace = workspace_manager.get_workspace("cleanup_test")
        assert workspace.workspace_path.exists()
        
        # Cleanup without removing all
        success, message = workspace_manager.cleanup_workspace(
            "cleanup_test",
            remove_all=False
        )
        
        assert success is True
        
        # Cleanup all
        success, message = workspace_manager.cleanup_workspace(
            "cleanup_test",
            remove_all=True
        )
        
        assert success is True
        assert not workspace.workspace_path.exists()
