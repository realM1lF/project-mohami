# IntelligentAgent - ORPA + Tool-Use Integration

Der neue `IntelligentAgent` ist die zentrale Integration aller Mohami-Komponenten:
- **Tool-Use Pattern**: KI entscheidet selbst welche Tools verwendet werden
- **4-Schichten Gedächtnis**: Kurzzeit, Session, Langzeit, Episodisch
- **Workspace/Repository**: Automatische Repository-Verwaltung
- **ORPA Workflow**: Observe → Reason → Plan → Act

## Architektur

```
┌─────────────────────────────────────────────────────────────┐
│                    IntelligentAgent                          │
│                       (intelligent_agent.py)                 │
├─────────────────────────────────────────────────────────────┤
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │ ToolRegistry │  │UnifiedMemory │  │   Workspace  │      │
│  │  + Executor  │  │   Manager    │  │   Manager    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│         │                  │                  │              │
│         ▼                  ▼                  ▼              │
│  ┌────────────────────────────────────────────────────┐    │
│  │              ORPA State Machine                     │    │
│  │         (orpa_states.py)                           │    │
│  │   OBSERVE → REASON → PLAN → ACT → (loop/complete)  │    │
│  └────────────────────────────────────────────────────┘    │
│                              │                               │
│                              ▼                               │
│  ┌────────────────────────────────────────────────────┐    │
│  │              Kimi LLM Client                        │    │
│  └────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

## Dateien

| Datei | Beschreibung |
|-------|--------------|
| `intelligent_agent.py` | Hauptklasse - verbindet alle Komponenten |
| `agent_types.py` | Type Definitions (AgentConfig, ORPAState, etc.) |
| `orpa_states.py` | ORPA State Machine & Workflow |
| `example_usage.py` | Beispiele für die Verwendung |
| `verify_integration.py` | Verifikation der Integration |

## Schnelle Verwendung

```python
from src.agents import IntelligentAgent, AgentConfig

# 1. Konfiguration erstellen
config = AgentConfig(
    customer_id="acme-corp",
    max_iterations=5,
    auto_execute=True,
    enable_memory=True,
    enable_workspace=True,
)

# 2. Agent erstellen
agent = IntelligentAgent("dev-agent-001", config)

# 3. Ticket verarbeiten
result = await agent.process_ticket(
    ticket_id="ACM-123",
    ticket_data={
        "title": "Add user authentication",
        "description": "Implement JWT-based authentication...",
    }
)

# 4. Ergebnis auswerten
print(f"Success: {result.success}")
print(f"Files modified: {result.files_modified}")
```

## ORPA Workflow

Der Agent arbeitet nach dem ORPA-Prinzip:

### 1. OBSERVE (Beobachten)
- Repository-Struktur analysieren
- Relevante Dateien finden
- Ähnliche Lösungen aus dem Gedächtnis laden
- Git-Status prüfen

### 2. REASON (Überlegen)
Die KI analysiert:
- Was will der User?
- Welche Tools brauche ich?
- Was ist der beste Ansatz?

```python
# Die KI bekommt:
- Ticket Beschreibung
- Verfügbare Tools (mit Schemas)
- Memory (ähnliche Tickets)
- Repository-Kontext

# Die KI entscheidet:
{
    "understanding": "Der User will...",
    "needed_tools": ["file_read", "write_file"],
    "approach": "Ich werde...",
    "needs_clarification": false
}
```

### 3. PLAN (Planen)
- Detaillierter Ausführungsplan erstellen
- Tool-Aufrufe in Reihenfolge definieren
- Abhängigkeiten berücksichtigen

```python
{
    "steps": [
        {
            "step_number": 1,
            "tool": "file_read",
            "parameters": {"path": "/workspace/config.py"},
            "description": "Read current config"
        },
        {
            "step_number": 2,
            "tool": "file_write",
            "parameters": {"path": "/workspace/config.py", "content": "..."},
            "description": "Update config with auth"
        }
    ]
}
```

### 4. ACT (Handeln)
- Tools nacheinander ausführen
- Ergebnisse überwachen
- Bei Fehlern: Re-Reasoning

## Integration mit Bestehenden Komponenten

### Tool-Use Framework (`src/tools/`)
```python
from ..tools.registry import ToolRegistry
from ..tools.executor import ToolExecutor

# Tools registrieren
self.tools.register(FileReadTool(), category="file")
self.tools.register(FileWriteTool(), category="file")

# Tools ausführen
result = await self.executor.execute(
    tool_name="file_read",
    parameters={"path": "/tmp/test.txt"}
)
```

### 4-Schichten Gedächtnis (`src/memory/`)
```python
from ..memory.unified_manager import UnifiedMemoryManager, LearningEpisode

# Kontext speichern
self.memory.store_context("key", value, tier="session")

# Ähnliche Lösungen finden
learnings = self.memory.find_solutions(problem_description)

# Lern-Episode aufzeichnen
self.memory.record_learning(LearningEpisode(
    ticket_id="ABC-123",
    problem="Auth issue",
    solution="Added JWT middleware",
    success=True,
))
```

### Workspace Management (`src/infrastructure/`)
```python
from ..infrastructure.workspace_manager import get_workspace_manager
from ..infrastructure.repository_manager import get_repository_manager

# Workspace vorbereiten
self.workspace.setup_workspace(customer_id="acme")

# Befehle ausführen
success, stdout, stderr = self.workspace.execute_command(
    customer_id="acme",
    command="pytest tests/"
)

# Changes pushen
self.workspace.sync_to_repo(customer_id="acme")
```

### LLM Client (`src/llm/`)
```python
from ..llm.kimi_client import KimiClient, Message

# LLM Anfrage
messages = [
    Message(role="system", content=system_prompt),
    Message(role="user", content=user_prompt)
]
response = await self.llm.chat(messages=messages)
```

## State Machine

Die ORPA State Machine verwaltet den Workflow:

```
IDLE → OBSERVING → REASONING → PLANNING → ACTING
                              ↑___________________|
                              (loop if needed)
                              
ACTING → COMPLETED (success)
ACTING → ERROR (failure)
REASONING → NEEDS_CLARIFICATION (human input needed)
```

**Iteration Limit**: Nach `max_iterations` (default: 10) wird der Loop zwangsweise beendet.

## Konfiguration

### AgentConfig

```python
AgentConfig(
    customer_id="acme-corp",          # Pflicht: Kunde
    max_iterations=10,                 # Max ORPA Iterationen
    auto_execute=True,                 # Tools auto-ausführen
    tool_timeout=300,                  # Timeout in Sekunden
    llm_temperature=0.3,               # LLM Kreativität
    enable_memory=True,                # Gedächtnis aktivieren
    enable_workspace=True,             # Workspace aktivieren
    allowed_tools=None,                # None = alle erlaubt
    forbidden_tools=["dangerous_cmd"], # Blacklist
)
```

## Callbacks & Monitoring

```python
# Progress tracking
agent.on_progress(lambda state, context: 
    print(f"[{state.value}] {context.ticket.ticket_id}")
)

# State transition tracking
machine = ORPAStateMachine(
    on_transition=lambda old, new, ctx: 
        print(f"{old.value} → {new.value}")
)
```

## Fehlerbehandlung

Der Agent behandelt verschiedene Fehlerszenarien:

1. **Tool nicht gefunden**: Error result zurückgeben
2. **Tool-Parameter ungültig**: Validation error
3. **Tool-Ausführung fehlschlägt**: Re-Reasoning oder Abbruch
4. **Max Iterationen erreicht**: Erzwungenes COMPLETED
5. **LLM nicht erreichbar**: Error state

## Migration vom Alten Agent

Alt (`developer_agent.py`):
```python
from src.agents import DeveloperAgent

agent = DeveloperAgent(...)
result = await agent.process(ticket)
```

Neu (`intelligent_agent.py`):
```python
from src.agents import IntelligentAgent, AgentConfig

config = AgentConfig(customer_id="acme")
agent = IntelligentAgent("agent-1", config)
result = await agent.process_ticket(ticket_id, ticket_data)
```

## Tests

```bash
# Integration verifizieren
python3 src/agents/verify_integration.py

# Unit Tests (mit pytest)
pytest src/agents/test_intelligent_agent.py -v
```

## Nächste Schritte

1. **DDD-Regeln**: Integration der Domain-Driven Design Constraints
2. **Multi-Agent**: Unterstützung für mehrere spezialisierte Agenten
3. **Human-in-the-Loop**: Bessere Unterstützung für Rückfragen
4. **Performance**: Caching und Optimierung
5. **Observability**: Metriken und Logging

---

**Wichtig**: Dieser Agent ersetzt den alten `DeveloperAgent`. Alle neuen Features sollten hier implementiert werden!
