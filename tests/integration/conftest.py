"""Shared fixtures for integration tests."""

import asyncio
import os
import tempfile
import shutil
from pathlib import Path
from typing import Generator, AsyncGenerator
from unittest.mock import AsyncMock, MagicMock

import pytest
import pytest_asyncio


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest.fixture(scope="session")
def event_loop() -> Generator[asyncio.AbstractEventLoop, None, None]:
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Path Fixtures
# =============================================================================

@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for tests."""
    tmp_path = Path(tempfile.mkdtemp(prefix="mohami_test_"))
    yield tmp_path
    # Cleanup
    shutil.rmtree(tmp_path, ignore_errors=True)


@pytest.fixture
def workspace_base_path(temp_dir: Path) -> Path:
    """Base path for test workspaces."""
    base_path = temp_dir / "workspaces"
    base_path.mkdir(parents=True, exist_ok=True)
    return base_path


@pytest.fixture
def chroma_db_path(temp_dir: Path) -> Path:
    """Path for ChromaDB test database."""
    db_path = temp_dir / "chroma_db"
    db_path.mkdir(parents=True, exist_ok=True)
    return db_path


@pytest.fixture
def episodic_db_path(temp_dir: Path) -> Path:
    """Path for episodic SQLite test database."""
    return temp_dir / "episodic_test.db"


# =============================================================================
# Mock Git Provider Fixture
# =============================================================================

@pytest.fixture
def mock_git_provider() -> MagicMock:
    """Create a mock Git provider for testing."""
    mock = MagicMock()
    mock.token = "test_token_12345"
    
    # Async methods
    mock.get_file_content = AsyncMock(return_value="# Test README\n\nCOMING SOON")
    mock.create_branch = AsyncMock(return_value="https://github.com/test/repo/tree/feature/test")
    mock.create_commit = AsyncMock(return_value="abc123def456")
    mock.create_pr = AsyncMock(return_value=MagicMock(
        id="pr_123",
        number=1,
        title="Test PR",
        body="Test PR body",
        head_branch="feature/test",
        base_branch="main",
        url="https://github.com/test/repo/pull/1",
        state="open"
    ))
    mock.get_repository_info = AsyncMock(return_value=MagicMock(
        id="repo_123",
        name="test-repo",
        full_name="test/test-repo",
        default_branch="main",
        url="https://github.com/test/test-repo",
        description="Test repository",
        private=False
    ))
    mock.list_branches = AsyncMock(return_value=["main", "develop", "feature/test"])
    mock.delete_branch = AsyncMock(return_value=None)
    mock.get_pr = AsyncMock(return_value=MagicMock(
        id="pr_123",
        number=1,
        title="Test PR",
        body="Test PR body",
        head_branch="feature/test",
        base_branch="main",
        url="https://github.com/test/repo/pull/1",
        state="open"
    ))
    
    return mock


# =============================================================================
# Memory Fixtures (with skip if dependencies not available)
# =============================================================================

@pytest.fixture
def short_term_memory():
    """Create an InMemoryBuffer for testing."""
    from src.memory.short_term import InMemoryBuffer
    return InMemoryBuffer(customer_id="test_customer")


@pytest.fixture
def chroma_client(chroma_db_path: Path):
    """Create a ChromaDB client for testing."""
    try:
        import chromadb
        from chromadb.config import Settings
        
        client = chromadb.PersistentClient(
            path=str(chroma_db_path),
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        return client
    except ImportError:
        pytest.skip("chromadb not installed")


@pytest.fixture
def embedding_provider():
    """Create a mock embedding provider for testing."""
    mock = MagicMock()
    # Return a simple embedding vector
    mock.embed = AsyncMock(return_value=[0.1, 0.2, 0.3, 0.4, 0.5])
    mock.embed_batch = AsyncMock(return_value=[[0.1, 0.2, 0.3, 0.4, 0.5]] * 5)
    return mock


@pytest.fixture
def memory_store(chroma_client, chroma_db_path: Path):
    """Create a ChromaMemoryStore for testing."""
    try:
        from src.memory.chroma_store import ChromaMemoryStore
        return ChromaMemoryStore(persist_directory=str(chroma_db_path))
    except ImportError as e:
        pytest.skip(f"ChromaMemoryStore not available: {e}")


@pytest.fixture
def chroma_long_term_memory(chroma_client, embedding_provider):
    """Create a ChromaLongTermMemory for testing."""
    try:
        from src.memory.chroma_long_term import ChromaLongTermMemory
        return ChromaLongTermMemory(
            chroma_client=chroma_client,
            customer_id="test_customer",
            embedding_function=None
        )
    except ImportError as e:
        pytest.skip(f"ChromaLongTermMemory not available: {e}")


@pytest.fixture
def episodic_memory(memory_store, embedding_provider):
    """Create an EpisodicMemory for testing."""
    try:
        from src.memory.episodic_memory import EpisodicMemory
        return EpisodicMemory(
            memory_store=memory_store,
            embedding_provider=embedding_provider
        )
    except ImportError as e:
        pytest.skip(f"EpisodicMemory not available: {e}")


# =============================================================================
# Tool Fixtures
# =============================================================================

@pytest.fixture
def tool_registry():
    """Create a ToolRegistry for testing."""
    from src.tools.registry import ToolRegistry
    return ToolRegistry()


# =============================================================================
# Workspace Fixtures
# =============================================================================

@pytest.fixture
def repository_manager(workspace_base_path: Path):
    """Create a RepositoryManager for testing."""
    from src.infrastructure.repository_manager import RepositoryManager
    return RepositoryManager(base_workspaces_path=str(workspace_base_path))


@pytest.fixture
def workspace_manager(temp_dir: Path, workspace_base_path: Path):
    """Create a WorkspaceManager for testing."""
    from src.infrastructure.workspace_manager import WorkspaceManager
    
    # Create a minimal customers.yaml config
    config_dir = temp_dir / "config"
    config_dir.mkdir(parents=True, exist_ok=True)
    config_path = config_dir / "customers.yaml"
    
    config_content = """
customers:
  test-customer:
    name: "Test Customer"
    git_provider: github
    repo_url: https://github.com/test/test-repo
    has_ddev: false
    default_branch: main
"""
    config_path.write_text(config_content)
    
    return WorkspaceManager(config_path=str(config_path))


# =============================================================================
# Async Fixtures Helper
# =============================================================================

@pytest_asyncio.fixture
async def async_temp_dir() -> AsyncGenerator[Path, None]:
    """Async fixture for temporary directory."""
    tmp_path = Path(tempfile.mkdtemp(prefix="mohami_async_test_"))
    yield tmp_path
    shutil.rmtree(tmp_path, ignore_errors=True)
