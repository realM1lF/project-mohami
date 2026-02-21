# Integration Tests für Mohami

Dieses Verzeichnis enthält Integrationstests für alle kritischen Komponenten des Mohami Systems.

## Test-Struktur

```
tests/integration/
├── conftest.py              # Shared fixtures für alle Tests
├── test_tool_use.py         # Tool-Use Framework Tests
├── test_memory.py           # Memory System Tests
├── test_workspace.py        # Workspace/Repo Management Tests
└── test_e2e.py             # End-to-End Tests
```

## Test-Kategorien

### 1. test_tool_use.py
Tests für das Tool-Use Framework:
- **File Tools**: `FileReadTool`, `FileWriteTool`, `FileListTool`, `FileSearchTool`
- **GitHub Tools**: `GitHubReadFileTool`, `GitHubWriteFileTool` (mit Mocks)
- **Local Git Tools**: `GitBranchTool`, `GitCommitTool`, `GitStatusTool`
- **Tool Registry**: Registration, Discovery, Schema-Generierung

### 2. test_memory.py
Tests für das Memory-System:
- **Short Term Memory**: `InMemoryBuffer` - TTL, Reasoning Steps, ORPA State
- **Long Term Memory**: `ChromaLongTermMemory` - Patterns, Solutions, Docs
- **Episodic Memory**: `EpisodicMemory` - Ticket Resolutions, Lessons

### 3. test_workspace.py
Tests für Workspace und Repository Management:
- **RepositoryManager**: Clone, Pull, Push, Branch Management
- **WorkspaceManager**: Setup, DDEV Integration, Command Execution

### 4. test_e2e.py
End-to-End Integration Tests:
- Komplette Ticket-Workflows
- Multi-Tool Integration
- Error Handling

## Ausführung

### Alle Integrationstests ausführen:
```bash
python -m pytest tests/integration/ -v
```

### Spezifische Testdatei:
```bash
python -m pytest tests/integration/test_tool_use.py -v
```

### Nur schnelle Tests (ohne git-Operationen):
```bash
python -m pytest tests/integration/ -v -m "not requires_git"
```

### Tests mit ChromaDB überspringen:
```bash
python -m pytest tests/integration/ -v --ignore-glob="*memory*"
```

## Abhängigkeiten

Die Tests benötigen:
- `pytest`
- `pytest-asyncio`
- `pyyaml`
- `chromadb` (optional, für Memory-Tests)
- `git` (für Repository-Tests)

## Fixtures

Die `conftest.py` stellt folgende Fixtures bereit:

- `temp_dir` - Temporäres Verzeichnis für Tests
- `workspace_base_path` - Basis-Pfad für Workspaces
- `mock_git_provider` - Mock für GitHub API
- `short_term_memory` - InMemoryBuffer Instanz
- `chroma_client` - ChromaDB Client (optional)
- `chroma_long_term_memory` - ChromaLongTermMemory Instanz
- `episodic_memory` - EpisodicMemory Instanz
- `tool_registry` - ToolRegistry Instanz
- `repository_manager` - RepositoryManager Instanz
- `workspace_manager` - WorkspaceManager Instanz

## Mocking

Für externe APIs (GitHub) werden Mocks verwendet:
- `mock_git_provider` simuliert alle Git-Operationen
- Keine echten API-Calls werden durchgeführt

Für lokale Git-Operationen werden temporäre Repositories erstellt und nach dem Test wieder gelöscht.
