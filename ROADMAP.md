# 🗺️ Mohami Master Roadmap

**Lead:** Kimi (Koordination, Architektur, Integration)  
**Stand:** 21. Feb 2026 - Sprint 1 (MVP+) abgeschlossen

---

## Phase 1: ✅ ABGESCHLOSSEN (Heute)

### Deliverables:
- [x] Tool-Use Framework (BaseTool, Registry, Executor)
- [x] 4-Schichten Gedächtnis (Short, Session, Long, Episodic)
- [x] Material Design 3 UI
- [x] Agenten-Template-System
- [x] DDEV Architektur V2 (Clone-to-Workspace)
- [x] GitHub Repository (realM1lF/project-mohami)

**Status:** Alles implementiert, aber noch nicht integriert!

---

## Phase 2.1: Integration Sprint (Tag 1-2) 🎯 JETZT

### Ziel: Alles zusammenführen
Der Agent Worker läuft noch mit altem Code. Wir müssen den neuen Tool-Use Agent aktivieren.

### Sub-Tasks:

#### @integration (Core Developer)
**Aufgabe:** Verbinde alle Komponenten

```python
# Neuen Agent erstellen: src/agents/intelligent_agent.py
class IntelligentAgent:
    def __init__(self):
        self.tools = ToolRegistry()  # Alle Tools registrieren
        self.memory = UnifiedMemoryManager()  # 4-Schichten
        self.workspace = WorkspaceManager()  # Clone/DDEV
    
    async def process_ticket(self, ticket_id):
        # ORPA Workflow mit Tool-Use
        # 1. OBSERVE: Context + Memory laden
        # 2. REASON: LLM analysiert mit Tools
        # 3. PLAN: Tool-Execution-Plan erstellen
        # 4. ACT: Tools ausführen
```

**Deliverables:**
- `src/agents/intelligent_agent.py` (neuer Haupt-Agent)
- Integration Tool-Use in ORPA Workflow
- Workspace + Repository Manager nutzen

**Zeit:** 4h

---

#### @migration (Backend Developer)
**Aufgabe:** Alten Agent ersetzen

```python
# agent_worker.py aktualisieren
# Statt: DeveloperAgent (alt, hardcoded)
# Neu: IntelligentAgent (Tool-Use, Memory)
```

**Deliverables:**
- `agent_worker.py` nutzt IntelligentAgent
- Rückwärtskompatibilität (Falls was schiefgeht)
- Config-Switch: USE_INTELLIGENT_AGENT=true/false

**Zeit:** 2h

---

#### @tester (QA Engineer)
**Aufgabe:** Integration Tests

**Test-Szenarien:**
1. **Tool-Use Test:** "Lies README.md" → KI ruft ReadFileTool
2. **Memory Test:** Ticket erstellen → Zweites Ticket erkennt Pattern
3. **Workspace Test:** Setup Workspace → Clone funktioniert
4. **End-to-End:** Ticket "Füge Zeile zu README" → PR wird erstellt

**Deliverables:**
- `tests/integration/test_tool_use.py`
- `tests/integration/test_memory.py`
- `tests/integration/test_e2e.py`

**Zeit:** 3h

---

### Phase 2.1 Success Criteria:
- [ ] Agent Worker läuft mit neuem IntelligentAgent
- [ ] Ein einfaches Ticket wird per Tool-Use bearbeitet
- [ ] Memory speichert und retrieved korrekt
- [ ] Alle Integration-Tests passen

---

## Phase 2.2: Bugfix & Polish (Tag 3) 🔧

### Ziel: Stabilisieren
Was @tester findet, repariert @fixer.

### Sub-Tasks:

#### @qa-lead (Vision Keeper & Tester)
**Aufgabe:** Ausführliches Testing

**Test-Plan:**
1. **Frontend:** Alle UI-Elemente klicken
2. **API:** Alle Endpunkte testen
3. **Agent:** 10 verschiedene Ticket-Typen
4. **Memory:** Großes Ticket-Volume (100+ Tickets)
5. **Dokumentation:** README ist verständlich?

**Deliverables:**
- QA_REPORT.md mit Bugs
- STRATEGIC_QUESTIONS.md (falls Architektur-Fragen)

**Zeit:** 4h

---

#### @fixer (Full-Stack Developer)
**Aufgabe:** Bugs reparieren

**Prioritäten:**
1. P0 (Kritisch): Crash, Datenverlust
2. P1 (Hoch): Feature nicht nutzbar
3. P2 (Mittel): UI-Probleme
4. P3 (Niedrig): Schönheitsfehler

**Deliverables:**
- Bugfixes für alle P0-P2
- Falls P3 zu viel: Liste für später

**Zeit:** 3h

---

#### @docs (Technical Writer)
**Aufgabe:** Dokumentation

**Deliverables:**
- `README.md` aktualisieren (Setup, Usage)
- `docs/ARCHITECTURE.md` für Entwickler
- `docs/AGENT_SETUP.md` (wie erstelle ich neuen Agent)
- `CHANGELOG.md` für Versionen

**Zeit:** 2h

---

### Phase 2.2 Success Criteria:
- [ ] Keine P0/P1 Bugs
- [ ] README ist verständlich für Neuling
- [ ] Alle Tests passen

---

## Phase 3: Multi-File & Plugins (Tag 4-7) 🚀

### Ziel: Komplexe Aufgaben
Agent kann ganze Plugins mit 10+ Dateien erstellen.

### Sub-Tasks:

#### @multi-file (Senior Developer)
**Aufgabe:** Multi-File Planung

```python
# Plan kann mehrere Dateien enthalten:
plan = {
    "files": [
        {"path": "src/Plugin.php", "content": "..."},
        {"path": "src/Service/MyService.php", "content": "..."},
        {"path": "tests/MyServiceTest.php", "content": "..."}
    ],
    "dependencies": [
        "src/Service/MyService.php -> src/Plugin.php"
    ]
}
```

**Deliverables:**
- `src/planning/multi_file_planner.py`
- Dependency-Graph für Dateien
- Reihenfolge-Optimierung (was zuerst?)

**Zeit:** 6h

---

#### @plugin-generator (Shopware Specialist)
**Aufgabe:** Shopware Plugin Templates

**Deliverables:**
- `templates/plugins/shopware-6.5/`
  - `plugin.xml`
  - `src/{PluginName}.php`
  - `src/Resources/config/services.xml`
  - `src/Controller/ApiController.php`
  - etc.
- `templates/plugins/shopware-6.7/` (neuere Struktur)
- Generator: "Erstelle Plugin für B2B Preisregeln"

**Zeit:** 6h

---

#### @ux-enhancer (Frontend Developer)
**Aufgabe:** Kanban Erweiterungen

**Features:**
1. **Multi-File View:** Zeige alle Dateien eines Tickets
2. **Progress Bar:** "3 von 5 Dateien erstellt"
3. **Diff View:** Zeige Code-Änderungen im Browser
4. **Agent Chat:** Echtzeit-Chat mit Agent (WebSocket)

**Deliverables:**
- `frontend/src/components/MultiFileView.js`
- `frontend/src/components/DiffViewer.js`
- `frontend/src/components/AgentChat.js`

**Zeit:** 5h

---

### Phase 3 Success Criteria:
- [ ] "Erstelle Shopware Plugin" Ticket funktioniert
- [ ] Alle 5+ Dateien werden korrekt erstellt
- [ ] Frontend zeigt Multi-File Plan an

---

## Phase 4: Production Ready (Tag 8-10) 🏭

### Ziel: Deployment
System kann auf Server deployed werden.

### Sub-Tasks:

#### @security (Security Engineer)
**Aufgabe:** Absicherung

**Checkliste:**
- [ ] Secrets in Environment (nicht im Code)
- [ ] API-Keys rotated regelmäßig
- [ ] Rate-Limiting für OpenRouter
- [ ] Customer Isolation enforced
- [ ] Keine SQL-Injections möglich
- [ ] CORS korrekt konfiguriert

**Deliverables:**
- `docs/SECURITY.md`
- `scripts/rotate_secrets.py`
- Rate-Limiter implementiert

**Zeit:** 4h

---

#### @infra-prod (DevOps Engineer)
**Aufgabe:** Production Setup

**Deliverables:**
- `docker-compose.prod.yml` (ohne Dev-Tools)
- `docker-compose.monitoring.yml` (Prometheus, Grafana)
- `scripts/deploy.sh` (One-Command Deploy)
- `nginx/` (Reverse Proxy Config)

**Zeit:** 5h

---

#### @monitoring (SRE)
**Aufgabe:** Observability

**Deliverables:**
- Logging (Structured JSON)
- Metrics (Tickets/h, Success Rate, Token-Kosten)
- Alerts (wenn Agent crashed)
- Health Checks (/health, /ready)

**Zeit:** 4h

---

### Phase 4 Success Criteria:
- [ ] Läuft auf Server ohne Abstürze
- [ ] Monitoring zeigt alle Metriken
- [ ] Deployment dauert < 5 Minuten
- [ ] Security Audit bestanden

---

## 📅 Timeline

| Phase | Tage | Deliverable |
|-------|------|-------------|
| 2.1 Integration | Tag 1-2 | Neuer Agent läuft mit Tool-Use |
| 2.2 Bugfix | Tag 3 | Stabiles, dokumentiertes System |
| 3 Multi-File | Tag 4-7 | Plugin-Generation funktioniert |
| 4 Production | Tag 8-10 | Deployed auf Server |

**Gesamt:** ~10 Tage bis Production

---

## 🎯 JETZT: Phase 2.1 Starten

Ich starte als Lead mit den 3 Sub-Agents für Integration:

1. **@integration** → IntelligentAgent bauen
2. **@migration** → Agent Worker umstellen
3. **@tester** → Tests schreiben

**Parallel:** Alle 3 arbeiten gleichzeitig, ich koordiniere.

---

**Go für Phase 2.1?** 👍
