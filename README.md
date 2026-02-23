# 🤖 Mohami - Dein KI-Mitarbeiter für Softwareentwicklung

> Ein autonomer KI-Entwickler, der Tickets entgegennimmt, analysiert, implementiert und aus Erfahrungen lernt.

---

## 🎯 Was ist Mohami?

**Mohami** ist ein KI-gestütztes Entwickler-Assistenzsystem, das wie ein virtueller Mitarbeiter funktioniert:

- 📋 **Liest Tickets** aus einem Kanban-Board
- 🧠 **Analysiert** Code und Anforderungen
- ✍️ **Implementiert** Lösungen automatisch
- 🔄 **Erstellt** Pull Requests
- 🧠 **Merkt sich** erfolgreiche Lösungen

### Das Besondere: Ein Agent mit Gedächtnis

Anders als einfache Code-Assistenten hat Mohami ein **4-Schichten-Gedächtnis**:

| Schicht | Was wird gespeichert? | Beispiel |
|---------|----------------------|----------|
| **Kurzzeit** | Aktives Ticket, aktuelle Phase | "Bearbeite Ticket #123" |
| **Session** | Chat-Verlauf, Zwischenstände | Kundenkommunikation |
| **Langzeit** | Code-Patterns, Lösungen | "Für Shopware 6 nutze Service-Decorator" |
| **Episodisch** | Ticket-Verläufe, Erfolge/Fehler | "Cache-Problem bei ALP-Shopware" |

---

## 🚀 Schnellstart (mit Docker)

### 1. Voraussetzungen

```bash
# Docker & Docker Compose installiert
docker --version  # >= 20.10
docker-compose --version  # >= 1.29
```

### 2. Konfiguration

```bash
# Repository klonen
git clone https://github.com/realM1lF/project-mohami.git
cd project-mohami

# Umgebungsvariablen kopieren
cp .env.example .env

# .env bearbeiten mit deinen API-Keys:
# - OPEN_ROUTER_API_KEY=sk-or-...
# - GITHUB_TOKEN=ghp_...
# - KIMI_API_KEY=...
```

### 3. Starten

```bash
# Alles auf einmal starten
docker-compose up -d --build

# Oder mit Make:
make start
```

### 4. Zugriff

| Service | URL | Beschreibung |
|---------|-----|--------------|
| **Frontend** | http://localhost:3000 | Kanban-Board & Ticket-Übersicht |
| **Backend API** | http://localhost:8000 | REST API & Docs |
| **API Docs** | http://localhost:8000/docs | Swagger UI |

### 5. Erstes Ticket erstellen

```bash
# Über Frontend:
# 1. http://localhost:3000 öffnen
# 2. "Neues Ticket" klicken
# 3. Titel: "README aktualisieren"
# 4. Beschreibung: "Füge ein Beispiel hinzu"
# 5. Auf "In Bearbeitung" setzen

# Oder per API:
curl -X POST http://localhost:8000/tickets \
  -H "Content-Type: application/json" \
  -d '{
    "title": "README aktualisieren",
    "description": "Füge ein Beispiel hinzu",
    "customer": "test-customer",
    "priority": "medium"
  }'
```

---

## 🏗️ Architektur & Funktionsweise

### Der ORPA-Workflow

Mohami arbeitet in einem **4-Phasen-Zyklus**:

```
┌─────────────────────────────────────────────────────────────┐
│  OBSERVE → REASON → PLAN → ACT → (wiederholen bei Bedarf)  │
└─────────────────────────────────────────────────────────────┘
```

**Phase 1: OBSERVE (Beobachten)**
- Liest das Ticket
- Analysiert Repository-Struktur
- Sucht ähnliche Lösungen im Gedächtnis
- Identifiziert relevante Dateien

**Phase 2: REASON (Begründen)**
- LLM (Kimi 2.5) analysiert das Problem
- Entscheidet: Sofort bearbeiten oder Rückfrage?
- Wählt benötigte Tools (Git, File-Ops, DDEV)
- Prüft gegen definierte Regeln

**Phase 3: PLAN (Planen)**
- Erstellt Schritt-für-Schritt Plan
- Definiert Reihenfolge der Tool-Aufrufe
- Identifiziert Abhängigkeiten

**Phase 4: ACT (Ausführen)**
- Führt Tools aus (File-Read, Git-Commit, PR-Create)
- Sammelt Ergebnisse
- Springt bei Bedarf zurück zu OBSERVE

### Kernkomponenten

```
project-mohami/
│
├── 🤖 agent_worker.py          # Haupt-Prozess (Polling & Workflow)
├── 🎯 src/agents/              # Agent-Implementierungen
│   ├── intelligent_agent.py    # ORPA-Workflow & Tool-Auswahl
│   └── orpa_states.py          # Zustandsmaschine
│
├── 🛠️ src/tools/               # Tool-Framework
│   ├── git_tools.py            # GitHub/Git Operationen
│   ├── file_tools.py           # Datei-Lesen/Schreiben
│   ├── code_tools.py           # Code-Analyse
│   └── ddev_tools.py           # DDEV-Integration
│
├── 🧠 src/memory/              # 4-Schichten-Gedächtnis
│   ├── unified_manager.py      # Einheitliche API
│   ├── short_term.py           # In-Memory (Session)
│   ├── session_redis.py        # Redis (24h)
│   ├── long_term_chroma.py     # ChromaDB (Vektoren)
│   └── episodic_memory.py      # SQLite (Historie)
│
├── 📋 src/kanban/              # Ticket-Management
│   ├── main.py                 # FastAPI Backend
│   ├── models.py               # Datenbank-Schema
│   └── crud_async.py           # Async DB-Operationen
│
├── 🔌 src/git_provider/        # Git-Integration
│   ├── github.py               # GitHub API
│   └── bitbucket.py            # Bitbucket API
│
├── 🏗️ src/infrastructure/      # Workspace-Management
│   ├── workspace_manager.py    # DDEV & lokale Workspaces
│   └── repository_manager.py   # Git-Clone/Push/Pull
│
└── 👤 agents/                  # Agent-Konfiguration
    └── mohami/
        ├── soul.md             # Persönlichkeit
        ├── rules.md            # Verhaltensregeln
        ├── knowledge.md        # Domänenwissen
        ├── config.yaml         # Laufzeit-Config
        └── memories/           # Kuratiertes Wissen
            ├── systems/        # Shopware, DDEV, etc.
            ├── lessons/        # Gelernte Lösungen
            └── links/          # Nützliche Ressourcen
```

### Technologie-Stack

| Komponente | Technologie | Zweck |
|------------|-------------|-------|
| **Language** | Python 3.11+ | Haupt-Backend |
| **LLM** | Kimi 2.5 (via OpenRouter) | Intelligenz |
| **API** | FastAPI | REST Backend |
| **Frontend** | React | Web-UI |
| **Database** | SQLite (Dev) / PostgreSQL (Prod) | Tickets & Metadaten |
| **Cache** | Redis 7 | Session & Short-Term Memory |
| **Vector DB** | ChromaDB | Semantic Memory |
| **Container** | Docker Compose | Deployment |
| **Dev Env** | DDEV (optional) | Shopware-Entwicklung |

---

## 🎮 Agenten-Konfiguration

### Eigener Agent

Jeder Agent hat eine eigene Identität in `agents/{agent_id}/`:

**soul.md** - Persönlichkeit:
```markdown
# MeinAgent

## Persönlichkeit
- Freundlich und professionell
- Lösungsorientiert

## Kommunikationsstil
- Kurz und prägnant
- Keine Technik-Floskeln
```

**rules.md** - Verhaltensregeln:
```markdown
# Grundregeln

## Hard Constraints
- Niemals auf Production deployen
- Immer Tests schreiben
- Keine API-Keys im Code

## Code-Qualität
- PHPDoc für alle Funktionen
- Typ-Hints verwenden
```

**knowledge.md** - Domänenwissen:
```markdown
# Wissen

## Shopware 6
- Service-Decorator Pattern bevorzugen
- Cache immer nach DB-Änderungen leeren
```

### Kunden-Integration

Kunden werden in `customers/{customer}/` konfiguriert:

```bash
customers/
└── alp-shopware/
    ├── context.md          # Projektbeschreibung
    └── tech-stack.md       # Technologie-Stack
```

---

## 🔧 Development (ohne Docker)

### Lokale Entwicklung

```bash
# Python Environment
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Frontend
cd frontend
npm install
npm start

# Backend (Terminal 1)
uvicorn src.kanban.main:app --reload --port 8000

# Agent Worker (Terminal 2)
python agent_worker.py
```

### Tests ausführen

```bash
# Alle Tests
pytest

# Nur Integrationstests
pytest -m integration

# Mit Coverage
pytest --cov=src --cov-report=html
```

### Memories laden

```bash
# Lädt alle Markdown-Dateien aus agents/{agent}/memories/ in ChromaDB
python scripts/load_memories.py

# Dry-run (zeigt was geladen würde)
python scripts/load_memories.py --dry-run
```

---

## 📊 Monitoring & Debugging

### Logs anzeigen

```bash
# Alle Services
docker-compose logs -f

# Nur Agent
docker-compose logs -f ki-agent

# Nur Backend
docker-compose logs -f ki-backend
```

### Datenbank inspizieren

```bash
# SQLite direkt
sqlite3 ~/ki-data/kanban.db

# oder über API
curl http://localhost:8000/tickets
```

### Redis Cache

```bash
# Redis CLI
docker exec -it ki-redis redis-cli

# Keys anzeigen
KEYS *
```

---

## 🛣️ Roadmap & Vision

Siehe [IDEAS.md](IDEAS.md) für die langfristige Vision ("Mohami Studio") und [ROADMAP.md](ROADMAP.md) für den Entwicklungsplan.

Kurzfristige Highlights:
- ✅ ORPA-Workflow mit Tool-Use
- ✅ 4-Schichten-Gedächtnis
- ✅ GitHub/Bitbucket Integration
- ✅ DDEV-Integration
- 🔄 Mohami Studio (UI für Non-Devs)
- 🔄 Multi-Agent-Teams
- 🔄 Secrets Vault

---

## 🤝 Mitwirken

1. Fork erstellen
2. Feature-Branch: `git checkout -b feature/neues-feature`
3. Committen: `git commit -am 'feat: neues Feature'`
4. Pushen: `git push origin feature/neues-feature`
5. Pull Request erstellen

Siehe [IMPROVEMENTS.md](IMPROVEMENTS.md) für bekannte Issues und Optimierungspotenzial.

---

## 📄 Lizenz

MIT License - siehe [LICENSE](LICENSE)

---

## 💬 Support

- 📧 Issues: [GitHub Issues](https://github.com/realM1lF/project-mohami/issues)
- 💡 Ideen: [GitHub Discussions](https://github.com/realM1lF/project-mohami/discussions)

---

**Made with ❤️ and 🤖 by the Mohami Team**
