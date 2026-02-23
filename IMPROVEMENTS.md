# 🔧 Verbesserungsvorschläge & Bekannte Probleme

> Dieses Dokument listet bekannte Issues, technische Schulden und Optimierungspotenzial auf.
> 
> **Letzte Aktualisierung:** 23. Februar 2026

---

## 🚨 KRITISCH (Sofort beheben)

### 2. Docker Container läuft als root
- **Status:** 🔴 SECURITY
- **Ort:** `docker/Dockerfile.worker`, `docker/Dockerfile.backend`
- **Beschreibung:** Kein Non-Root-User definiert
- **Impact:** Container hat root-Rechte auf Host bei Escape
- **Lösung:**
  ```dockerfile
  RUN groupadd -r appgroup && useradd -r -g appgroup appuser
  USER appuser
  ```

### 3. Subprocess mit shell=True
- **Status:** 🔴 SECURITY
- **Ort:** `src/infrastructure/workspace_manager.py:531`
- **Beschreibung:** `subprocess.run(..., shell=True)` ohne Sanitization
- **Impact:** Command Injection möglich
- **Lösung:** `shell=False` und Command als Liste übergeben

### 4. Fehlende Health Checks
- **Status:** 🔴 RELIABILITY
- **Ort:** `docker-compose.yml`
- **Beschreibung:** Keine HEALTHCHECK für Services
- **Impact:** Container als "healthy" markiert obwohl App down
- **Lösung:**
  ```yaml
  healthcheck:
    test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
    interval: 30s
    timeout: 10s
    retries: 3
  ```

### 5. SQLite ohne Backup-Strategie
- **Status:** 🔴 DATA LOSS RISK
- **Ort:** `docker-compose.yml`, `~/ki-data/kanban.db`
- **Beschreibung:** SQLite wird gemountet ohne Backup
- **Impact:** Datenverlust bei Container-Fehler
- **Lösung:** 
  - PostgreSQL für Production
  - Oder: Automated SQLite-Backups

---

## ⚠️ HOCH (Bald beheben)

### 6. Duplizierter Code: AgentContext & AgentState
- **Status:** ⚠️ MAINTENABILITY
- **Ort:** `src/agents/developer_agent.py`, `src/agents/enhanced_agent.py`, `src/agents/enhanced_developer_agent.py`
- **Beschreibung:** Identische Klassen in 3+ Dateien
- **Impact:** Änderungen müssen an mehreren Stellen erfolgen
- **Lösung:** In `src/agents/agent_types.py` zentralisieren

### 7. While True ohne Exit-Bedingung
- **Status:** ⚠️ RELIABILITY
- **Ort:** Mehrere Agent-Dateien
- **Beschreibung:** Endlosschleifen ohne Graceful-Shutdown
- **Impact:** Prozess kann nicht sauber beendet werden
- **Lösung:**
  ```python
  self._running = True
  while self._running:
      # ...
      if signal_received:
          break
  ```

### 8. Print statt Logging
- **Status:** ⚠️ DEBUGGABILITY
- **Ort:** 40+ Vorkommen, besonders in `src/agents/`
- **Beschreibung:** `print()` statt `logging` verwendet
- **Impact:** Keine Log-Rotation, keine Levels
- **Lösung:** `logging.getLogger(__name__)` verwenden

### 9. Fehlende Timeouts bei Redis
- **Status:** ⚠️ RELIABILITY
- **Ort:** `src/memory/redis_memory.py`, `src/memory/session_redis.py`
- **Beschreibung:** Redis ohne Timeout-Handling
- **Impact:** Hängt bei Netzwerkproblemen
- **Lösung:** `redis.Redis(socket_timeout=5, socket_connect_timeout=5)`

### 10. Fehlende Input-Validierung bei API
- **Status:** ⚠️ STABILITY
- **Ort:** `src/kanban/main.py`
- **Beschreibung:** Einige Endpoints ohne Pydantic-Validierung
- **Impact:** 500 Errors bei invalidem Input
- **Lösung:** Pydantic-Models für alle Request Bodies

### 11. TODO: Multi-Collection Search
- **Status:** ⚠️ FUNCTIONALITY
- **Ort:** `src/memory/long_term_chroma.py:295`
- **Beschreibung:** Gibt leere Liste statt zu suchen
- **Impact:** Memory-Suche über Collections hinweg defekt
- **Lösung:** Cross-Collection Search implementieren

### 12. Hardcoded Tokens im Code
- **Status:** ⚠️ SECURITY
- **Ort:** `src/git_provider/factory.py`
- **Beschreibung:** Beispiel-Tokens wie "ghp_xxx" im Code
- **Impact:** Verwirrung, könnten aus Versehen verwendet werden
- **Lösung:** `<YOUR_TOKEN_HERE>` oder ENV-Variablen verwenden

### 13. Fehlende Testabdeckung
- **Status:** ⚠️ QUALITY
- **Ort:** `src/agents/intelligent_agent.py`, `src/infrastructure/workspace_manager.py`
- **Beschreibung:** Nur 10 Testdateien für 61 Source-Dateien (~15% Coverage)
- **Impact:** Keine Sicherheit bei Refactoring
- **Lösung:** Unit-Tests für Core-Komponenten

### 14. Keine Rate-Limiting für LLM
- **Status:** ⚠️ COST CONTROL
- **Ort:** `src/llm/kimi_client.py`
- **Beschreibung:** Keine Begrenzung der API-Aufrufe
- **Impact:** Hohe Kosten bei Fehlern/Loops
- **Lösung:** Token-Bucket oder Redis-based Rate-Limiting

### 15. Keine Retry-Logik für Git
- **Status:** ⚠️ RELIABILITY
- **Ort:** `src/infrastructure/workspace_manager.py`
- **Beschreibung:** Git-Befehle ohne Retry
- **Impact:** Fehler bei temporären Netzwerkproblemen
- **Lösung:** Exponentieller Backoff für Git-Ops

### 16. Fehlender Graceful Shutdown
- **Status:** ⚠️ RELIABILITY
- **Ort:** `agent_worker.py`
- **Beschreibung:** Kein Signal-Handler für SIGTERM/SIGINT
- **Impact:** Datenverlust bei Container-Stop
- **Lösung:**
  ```python
  import signal
  signal.signal(signal.SIGTERM, graceful_shutdown)
  ```

### 17. Unvollständige Type Hints
- **Status:** ⚠️ MAINTAINABILITY
- **Ort:** Mehrere Dateien in `src/agents/`, `src/tools/`
- **Beschreibung:** Viele Funktionen ohne Return-Type oder `Any`
- **Impact:** Keine statische Typ-Überprüfung
- **Lösung:** MyPy aktivieren und Typen vervollständigen

---

## 🔧 MITTEL (Nice to have)

### 18. Zirkuläre Imports
- **Status:** 🔧 CODE QUALITY
- **Ort:** `src/agents/intelligent_agent.py`
- **Beschreibung:** Komplexe Import-Struktur
- **Impact:** Kann zu Import-Fehlern führen
- **Lösung:** Dependency Injection oder Interface-Module

### 19. JSON ohne Fehlerhandling
- **Status:** 🔧 ROBUSTNESS
- **Ort:** 40+ Vorkommen von `json.loads/dumps`
- **Beschreibung:** Keine try/except bei JSON
- **Impact:** Crashes bei invalidem JSON
- **Lösung:** Wrapper-Funktionen mit Error-Handling

### 20. Magic Numbers
- **Status:** 🔧 MAINTAINABILITY
- **Ort:** `src/agents/intelligent_agent.py`, `src/llm/kimi_client.py`
- **Beschreibung:** Hartcodierte Werte wie `max_iterations=5`
- **Impact:** Schwer zu konfigurieren
- **Lösung:** In Konfigurations-Klassen auslagern

### 21. Fehlende Pagination
- **Status:** 🔧 PERFORMANCE
- **Ort:** `src/kanban/crud_async.py`
- **Beschreibung:** Keine Limit/Offset bei DB-Queries
- **Impact:** Performance-Probleme bei vielen Tickets
- **Lösung:** Pagination für alle List-Endpoints

### 22. Kein Circuit Breaker
- **Status:** 🔧 RESILIENCE
- **Ort:** `src/llm/kimi_client.py`, `src/git_provider/`
- **Beschreibung:** Keine Circuit-Breaker für externe Services
- **Impact:** Cascading Failures
- **Lösung:** `pybreaker` implementieren

### 23. Keine Metriken/Monitoring
- **Status:** 🔧 OBSERVABILITY
- **Ort:** Gesamtes Projekt
- **Beschreibung:** Keine Prometheus/OpenTelemetry
- **Impact:** Kein Einblick in Performance
- **Lösung:** Metriken für LLM-Calls, Git-Ops, DB-Queries

### 24. Keine API-Versionierung
- **Status:** 🔧 API DESIGN
- **Ort:** `src/kanban/main.py`
- **Beschreibung:** FastAPI ohne Version-Prefix
- **Impact:** Breaking Changes bei Updates
- **Lösung:** `/api/v1/` Prefix hinzufügen

### 25. Unvollständige OpenAPI Doku
- **Status:** 🔧 DOCUMENTATION
- **Ort:** `src/kanban/main.py`
- **Beschreibung:** Fehlende Beispiele und Beschreibungen
- **Impact:** API schwer zu verstehen
- **Lösung:** Vollständige OpenAPI-Dokumentation

---

## 📝 NIEDRIG (Kosmetisch)

### 26. Gemischte Sprachen (DE/EN)
- **Status:** 📝 CONSISTENCY
- **Ort:** Kommentare und Docstrings
- **Beschreibung:** Deutsch und Englisch gemischt
- **Lösung:** Einheitlich auf Englisch umstellen

### 27. Inconsistent Naming
- **Status:** 📝 CONSISTENCY
- **Ort:** `kimi_client.py` vs `OPEN_ROUTER_API_KEY`
- **Beschreibung:** Kimi vs OpenRouter inkonsistent
- **Lösung:** Einheitliche Benennung (LLM_CLIENT_*)

### 28. requirements.txt ohne Versions-Pinner
- **Status:** 📝 STABILITY
- **Ort:** `requirements.txt`
- **Beschreibung:** Einige Dependencies ohne Version
- **Lösung:** `pip-compile` oder `poetry` verwenden

### 29. Lange Dateien
- **Status:** 📝 MAINTAINABILITY
- **Ort:** `src/agents/intelligent_agent.py` (2.378 Zeilen)
- **Beschreibung:** Datei zu lang
- **Lösung:** In Module aufteilen

---

## 📊 Statistik

| Metrik | Wert |
|--------|------|
| Python-Dateien | 61 |
| Geschätzte Code-Zeilen | ~21.000 |
| Testdateien | 14 |
| Geschätzte Test-Coverage | ~15% |
| KRITISCHE Issues | 5 |
| HOHE Issues | 12 |
| MITTLERE Issues | 8 |
| NIEDRIGE Issues | 5 |

---

## 🎯 Priorisierte Roadmap

### Sofort (heute)
1. API-Keys rotieren
2. `.env` aus Git-History entfernen
3. Non-Root-User zu Dockerfiles hinzufügen
4. `shell=True` entfernen

### Diese Woche
5. AgentContext/AgentState deduplizieren
6. Print → Logging umstellen
7. While True mit Exit-Bedingung versehen
8. Health Checks hinzufügen

### Diesen Monat
9. Testabdeckung erhöhen
10. Input-Validierung vervollständigen
11. Monitoring/Metriken implementieren
12. SQLite → PostgreSQL migrieren (Production)

---

## 💡 Architektur-Verbesserungen

### Geplante Refactorings

#### 1. Agent-Modularisierung
```
src/agents/
├── core/
│   ├── agent_types.py      # Gemeinsame Typen
│   ├── base_agent.py       # Abstract Base
│   └── orpa/
│       ├── states.py
│       ├── transitions.py
│       └── workflow.py
├── implementations/
│   └── intelligent_agent.py
└── tools/
    └── integration/
```

#### 2. Memory-Layer-Optimierung
- Consistente Interface-Definition
- Bessere Error-Handling zwischen Layern
- Automatic Fallback bei Layer-Failure

#### 3. Tool-Registry-Verbesserung
- Plugin-System für externe Tools
- Dynamische Tool-Entdeckung
- Tool-Versioning

#### 4. Konfigurations-Management
- Zentrale Config-Klasse statt scattered Configs
- Environment-spezifische Overrides
- Config-Validierung mit Pydantic

---

## 🔍 Performance-Optimierungen

### Identifizierte Bottlenecks

1. **LLM-Calls:** Kein Caching von Prompts
2. **ChromaDB:** Keine Index-Optimierung
3. **Git-Operations:** Keine parallele Ausführung
4. **File-IO:** Synchrone Operationen

### Empfohlene Optimierungen

| Bereich | Optimierung | Erwarteter Impact |
|---------|-------------|-------------------|
| LLM | Prompt-Caching | -30% API-Kosten |
| Memory | ChromaDB Indexing | -50% Query-Zeit |
| Git | Async Operations | -40% Workflow-Zeit |
| Files | Batch-Operations | -20% IO-Zeit |

---

## 🛡️ Security-Checkliste

- [x] `.env` ist in `.gitignore` (nicht im Repo)
- [x] `.env.example` erstellt
- [ ] Non-Root-User in Docker
- [ ] `shell=True` entfernt
- [ ] Input-Sanitization für alle User-Inputs
- [ ] Rate-Limiting implementiert
- [ ] Audit-Logging für sensitive Operationen
- [ ] Secrets-Management (Vault) evaluiert

---

## 📚 Weiterführende Dokumentation

- [Architektur](docs/ARCHITECTURE_V2.md)
- [Vision & Roadmap](IDEAS.md)
- [DDEV Integration](docs/guides/DDEV_INTEGRATION.md)

---

**Hinweis:** Diese Liste wird laufend aktualisiert. Neue Issues sollten hier dokumentiert und priorisiert werden.
