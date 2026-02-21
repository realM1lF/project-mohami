# Phase 3: IntelligentAgent Stabilisierung

**Lead:** Kimi (Tech-Lead)  
**Dauer:** 2-3 Tage  
**Ziel:** Mohami wird wirklich "intelligent"

---

## Warum das jetzt kommt FIRST

Ohne den IntelligentAgent haben wir:
- ❌ Ein hübsches Kanban-Board
- ❌ Einen Bot der nur Keywords versteht
- ❌ Keine echte KI-Assistenz

Mit dem IntelligentAgent haben wir:
- ✅ Einen Agent der natürliche Sprache versteht
- ✅ Einen Agent der selbstständig plant und handelt
- ✅ Einen Agent der aus Erfahrung lernt
- ✅ Die Basis für Multi-File, Plugins, alles!

**Deshalb:** Erst den Agent fixen, dann Features bauen!

---

## Tag 1: Fix Core Issues

### @architect (Core Developer) - 6h
**Aufgabe:** IntelligentAgent Tool-Import fixen

**Problem:** `RuntimeError: Tools module not available`

**Lösung:**
1. Import-Pfade korrigieren (absolute statt relative im Container)
2. Tool-Initialisierung robust machen
3. Fallback wenn Tools fehlen → klare Fehlermeldung statt crash

**Deliverable:**
- IntelligentAgent startet ohne Fehler
- Tools werden korrekt registriert
- `verify_integration.py` läuft durch

---

### @tool-master (Tool Developer) - 6h
**Aufgabe:** 3 Kern-Tools "echt" machen

**Aktuell:** Tools sind Platzhalter
```python
# FALSCH (aktuell):
return {"code": "# TODO: Implement\n"}
```

**Ziel:** Tools nutzen wirklich LLM
```python
# RICHTIG:
response = await llm.chat("Generiere Python Code für...")
return {"code": response.content}
```

**Tools zu fixen:**
1. **CodeGenerateTool** - Nutzt Kimi für Code-Generierung
2. **FileReadTool** - Liest wirklich aus GitHub/Workspace
3. **FileWriteTool** - Schreibt wirklich Dateien

**Deliverable:**
- Tools produzieren echte Ergebnisse
- Integration mit KimiClient funktioniert

---

## Tag 2: Integration & Testing

### @integration (Integration Developer) - 6h
**Aufgabe:** Agent Worker + IntelligentAgent verheiraten

**Problem:** Worker erwartet alte API, IntelligentAgent hat neue API

**Lösung:**
1. AgentWorker aktualisieren für IntelligentAgent
2. Config-Übergabe korrekt machen
3. Ticket-Daten aus DB laden (nicht Dummy!)

**Deliverable:**
- `agent_worker.py` nutzt IntelligentAgent
- Ticket-Daten fließen korrekt durch
- Keine "Dummy Tickets" mehr

---

### @qa-tester (QA Engineer) - 6h
**Aufgabe:** E2E Test "Ticket → PR"

**Test-Szenario:**
```
1. User erstellt Ticket: "Füge Zeile zu README"
2. Agent analysiert mit LLM
3. Agent nutzt ReadFileTool
4. Agent nutzt WriteFileTool
5. Agent erstellt PR
6. Assert: PR existiert, README geändert
```

**Deliverable:**
- Test läuft automatisch durch
- Dokumentation was funktioniert
- Liste was noch broken ist

---

## Tag 3: Polish & Merge

### @architect (Core Developer) - 4h
**Aufgabe:** Memory-Integration vervollständigen

- Episodic Memory speichert wirklich Tickets
- Long-Term Memory speichert Code-Patterns
- Agent lernt aus vergangenen Aktionen

---

### @docs (Technical Writer) - 4h
**Aufgabe:** Dokumentation

- `docs/AGENT_ARCHITECTURE.md` - Wie funktioniert der Agent?
- `docs/TOOLS.md` - Welche Tools gibt es?
- `README.md` Update - Quickstart für neue User

---

## Success Criteria

- [ ] IntelligentAgent läuft stabil
- [ ] Agent versteht natürliche Sprache (nicht nur Keywords)
- [ ] Agent nutzt Tools selbstständig
- [ ] E2E Test "Ticket → PR" besteht
- [ ] Dokumentation ist aktuell

---

## Danach kommt Phase 4: Features

WENN der Agent läuft, bauen wir:
- Multi-File Planung (Plugins mit 10 Dateien)
- Shopware-Integration
- DDEV-Tests
- Alles was du willst!

**ABER:** Erst die Basis, dann das Haus!
