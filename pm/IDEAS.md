# 🚀 Vision & Ideen für Mohami

> Langfristige Produktvision und Erweiterungsideen für das KI-Mitarbeiter-System

---

## 🎯 Vision: "Mohami Studio"

Eine **visuelle Oberfläche** (Web-UI), mit der Nicht-Entwickler:
- Neue Kunden anlegen und verwalten
- KI-Mitarbeiter (Agenten) erstellen und konfigurieren
- API-Keys, Tokens und Zugänge sicher hinterlegen
- Das Gedächtnis der Agenten pflegen

**Zielgruppe:** Agentur-Inhaber, Team-Leads, Projektmanager - keine Entwickler!

---

## 📋 Feature-Ideen

### 1. 🏢 Kunden-Verwaltung (Customer Management)

#### Aktuell (Code-basiert)
```bash
mkdir -p customers/alp-shopware
echo "# ALP Shopware" > customers/alp-shopware/context.md
```

#### Vision (UI-basiert)
```
┌─────────────────────────────────────────────────────────────┐
│  ➕ Neuer Kunde                                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Kunden-Name:    [ALP Shopware                    ]        │
│  Kürzel:         [alp-shopware                    ]        │
│  Kontakt:        [max.mustermann@alp-shop.de      ]        │
│                                                             │
│  ┌─ Technologie-Stack ─────────────────────────────────┐   │
│  │  • Shopware-Version: [6.5.8.14               ] [▼] │   │
│  │  • PHP-Version:      [8.1                     ] [▼] │   │
│  │  • Datenbank:        [MariaDB 10.4            ] [▼] │   │
│  │  • Hosting:          [Mittwald                ] [▼] │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Besonderheiten:                                            │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Der Kunde bevorzugt kurze, prägnante Antworten     │   │
│  │ Keine externen APIs ohne vorherige Absprache       │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│              [💾 Speichern]  [❌ Abbrechen]                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Automatisch erstellt wird:**
- `customers/{kürzel}/context.md`
- `customers/{kürzel}/tech-stack.md`
- ChromaDB Collection für den Kunden

---

### 2. 🤖 Agenten-Designer (Agent Builder)

#### Schritt 1: Basis erstellen
```
┌─────────────────────────────────────────────────────────────┐
│  🎨 Neuen Agenten erstellen                                │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Name:           [Mohami                          ]        │
│  ID:             [mohami                          ]        │
│  Rolle:          [Senior Developer                ] [▼]    │
│                                                             │
│  Avatar:         [🧑‍💻]  [🤖]  [👨‍🔬]  [👩‍💻]  [🦊]  [+]    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Schritt 2: Persönlichkeit konfigurieren
```
┌─────────────────────────────────────────────────────────────┐
│  🧠 Persönlichkeit definieren                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Persönlichkeits-Template:  [Freundlich & Professionell ▼] │
│                                                             │
│  Anpassen:                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Kommunikationsstil:                                │   │
│  │ (•) Formal    ( ) Locker    ( ) Direkt             │   │
│  │                                                    │   │
│  │ Detaillierungsgrad:                                │   │
│  │ ( ) Ausführlich  (•) Prägnant  ( ) Nur Code        │   │
│  │                                                    │   │
│  │ Humor:                                             │   │
│  │ [⚪⚪⚪⚫⚫]  (3/5 - Gelegentlich)                 │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  Eigene Beschreibung:                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Du bist ein erfahrener Shopware-Entwickler mit     │   │
│  │ 10 Jahren Erfahrung. Du schätzt sauberen Code      │   │
│  │ und denkst immer an die Wartbarkeit.               │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Automatisch generiert wird:** `agents/{id}/soul.md`

#### Schritt 3: Regeln & Constraints
```
┌─────────────────────────────────────────────────────────────┐
│  📜 Harte Regeln (Constraints)                             │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ➕ Neue Regel hinzufügen                                   │
│                                                             │
│  ┌─ Regel 1 ───────────────────────────────────────────┐   │
│  │ ❌ Niemals direkt auf Production deployen!          │   │
│  │    Tags: [sicherheit] [deployment]                  │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Regel 2 ───────────────────────────────────────────┐   │
│  │ ⚠️  Immer Tests schreiben vor Commit                │   │
│  │    Tags: [testing] [qualität]                       │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Regel 3 ───────────────────────────────────────────┐   │
│  │ 📝 Jede Funktion muss PHPDoc haben                  │   │
│  │    Tags: [dokumentation]                            │   │
│  └──────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Automatisch generiert wird:** `agents/{id}/rules.md`

---

### 3. 🧠 Gedächtnis-Manager (Memory Curator)

#### Visuelle Memory-Pflege
```
┌─────────────────────────────────────────────────────────────┐
│  🧠 Mohamis Gedächtnis verwalten                           │
├─────────────────────────────────────────────────────────────┤
│  Tabs: [Systems] [Lessons Learned] [Links] [Search]        │
│                                                             │
│  ┌─ Systems ────────────────────────────────────────────┐   │
│  │                                                       │   │
│  │  🔧 DDEV        [Edit] [Delete]  Letzte Änderung:    │   │
│  │     12 Einträge                    vor 2 Tagen       │   │
│  │                                                       │   │
│  │  🛒 Shopware 6  [Edit] [Delete]  Letzte Änderung:    │   │
│  │     8 Einträge                     vor 1 Woche       │   │
│  │                                                       │   │
│  │  ➕ Neues System hinzufügen                           │   │
│  │                                                       │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ➕ Schnell-Eintrag:                                        │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ Titel: [                                          ] │   │
│  │ Kategorie: [Lessons Learned ▼]    Wichtigkeit: [⭐⭐⭐] │   │
│  │                                                     │   │
│  │ Inhalt:                                             │   │
│  │ ┌───────────────────────────────────────────────┐  │   │
│  │ │ Bei Shopware 6.5 Cache-Problemen:             │  │   │
│  │ │ 1. bin/console cache:clear                    │  │   │
│  │ │ 2. DDEV restart                               │  │   │
│  │ │ 3. Immer prüfen: theme:compile läuft durch    │  │   │
│  │ └───────────────────────────────────────────────┘  │   │
│  │                                                     │   │
│  │ Tags: [shopware] [cache] [troubleshooting]         │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### Wichtige Funktionen:
- **Markdown-Editor** mit Preview
- **Auto-Kategorisierung** per KI
- **Versionierung** (wer hat wann was geändert)
- **Suche** über alle Memories mit Semantik
- **Import/Export** (für Backups oder Sharing)

---

### 4. 🔐 Sicherer Zugangs-Manager (Secrets Vault)

#### Problem aktuell:
API-Keys, Tokens und Passwörter liegen verstreut in:
- `.env` Dateien
- Docker Compose
- GitHub Secrets
- Lokale Configs

#### Vision: Zentraler Vault pro Kunde
```
┌─────────────────────────────────────────────────────────────┐
│  🔐 Zugänge & API-Keys für ALP-Shopware                    │
├─────────────────────────────────────────────────────────────┤
│  🔒 Verschlüsselt mit AES-256 (nur Agenten haben Zugriff)  │
│                                                             │
│  ┌─ GitHub ─────────────────────────────────────────────┐   │
│  │  Token:    [•••••••••••••••••••••••]  [👁️] [🔄]    │   │
│  │  Owner:    netgrade                                   │   │
│  │  Repos:    alp-shopware, alp-docs                     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Server (SSH) ────────────────────────────────────────┐   │
│  │  Host:      ssh.mittwald.de                           │   │
│  │  User:      deploy                                    │   │
│  │  Key:      [•••••••••••••••••••••••]  [👁️] [📥]    │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Shopware API ────────────────────────────────────────┐   │
│  │  URL:       https://alp-shopware.de/api               │   │
│  │  Client-ID: [•••••••••••••••••••••••]  [👁️]         │   │
│  │  Secret:    [•••••••••••••••••••••••]  [👁️]         │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ OpenAI API (für diesen Kunden) ─────────────────────┐   │
│  │  Modell:   GPT-4                                     │   │
│  │  Key:      [•••••••••••••••••••••••]  [👁️]         │   │
│  │  Limit:    $100/Monat                                │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
│  ➕ Neuen Zugang hinzufügen                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

**Sicherheits-Features:**
- 🔐 Verschlüsselte Speicherung (HashiCorp Vault oder ähnlich)
- 🎭 Agenten bekommen nur die Keys, die sie brauchen
- 📝 Audit-Log: Wer hat wann auf welchen Key zugegriffen?
- ⏰ Rotation-Reminder: "SSH-Key ist 90 Tage alt"

---

### 5. 📊 Dashboard & Monitoring

```
┌─────────────────────────────────────────────────────────────┐
│  📊 Mohami Dashboard                                       │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  ┌─ Aktivität heute ───────┐ ┌─ System-Status ───────────┐  │
│  │  🎫 3 Tickets bearbeitet │ │  ✅ Redis: Online         │  │
│  │  📝 12 Commits          │ │  ✅ ChromaDB: Online      │  │
│  │  ⏱️  4.2h Arbeitszeit   │ │  ✅ GitHub: Verbunden     │  │
│  └──────────────────────────┘ └───────────────────────────┘  │
│                                                             │
│  ┌─ Gedächtnis-Statistik ────────────────────────────────┐   │
│  │                                                        │   │
│  │  Systems:     [████████░░] 8 Einträge                 │   │
│  │  Lessons:     [██████░░░░] 12 Lösungen gelernt        │   │
│  │  Episodic:    [██████████] 47 Tickets in DB           │   │
│  │                                                        │   │
│  │  Letzte Einträge:                                      │   │
│  │  • Neue Lösung: "Shopware Cache leeren" (vor 2h)      │   │
│  │  • System-Update: "DDEV v1.23" (vor 1d)               │   │
│  └────────────────────────────────────────────────────────┘   │
│                                                             │
│  ┌─ Aktive Tickets ──────────────────────────────────────┐   │
│  │  #1234 🟡 Shopware Update auf 6.6  [ALP-Shopware]     │   │
│  │  #1235 🟢 Neue Payment-Integration [ALP-Shopware]     │   │
│  │  #1236 🔴 Kritischer Bug in Checkout [Test-Kunde]     │   │
│  └───────────────────────────────────────────────────────┘   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

### 6. 🎮 Playground (Test-Bereich)

```
┌─────────────────────────────────────────────────────────────┐
│  🎮 Playground - Teste Mohami ohne Risiko                  │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Szenario:                                                  │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ "Shopware 6 Plugin erstellen, das eine neue API     │   │
│  │  Endpoint für Produkt-Bewertungen hinzufügt"        │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [▶️ Szenario starten]  [📋 Aus Vorlage]  [🎲 Zufällig]    │
│                                                             │
│  ─────────────────────────────────────────────────────────  │
│                                                             │
│  🧠 Mohamis Gedanken:                                      │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ 1. Analysiere Anforderung... ✅                      │   │
│  │ 2. Prüfe Tech-Stack (ALP-Shopware)... ✅             │   │
│  │ 3. Suche ähnliche Lösungen... ⏳                     │   │
│  │    └─> "API-Endpoint Pattern" gefunden               │   │
│  │ 4. Generiere Code... ⏳                              │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  💻 Generierter Code:                                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │ class RatingApiController extends AbstractController │   │
│  │ {                                                   │   │
│  │     // ...                                          │   │
│  └─────────────────────────────────────────────────────┘   │
│                                                             │
│  [💾 Als Memory speichern]  [🔄 Neu generieren]            │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 💰 Monetarisierungs-Strategien

### Modell 1: Open Core (Empfohlen)

```
┌─────────────────────────────────────────────────────────────┐
│  Mohami Open Core                                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  🆓 Open Source (GitHub)              💼 Enterprise         │
│  ─────────────────────────            ───────────────────   │
│  • Basis-Agent                         • Mohami Studio UI   │
│  • CLI-Interface                       • Multi-Agent Teams  │
│  • Markdown-Memories                   • Advanced Analytics │
│  • Single-User                         • Secrets Vault      │
│  • Self-Hosted required                • Priority Support   │
│  • Community Support                   • SLA garantiert     │
│                                        • On-Premise Option  │
│  Preis: Kostenlos                      Preis: €99/Agent/Mon │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Modell 2: SaaS-Hosting

```
┌─────────────────────────────────────────────────────────────┐
│  Mohami Cloud                                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  Starter                    Professional         Enterprise │
│  €49/Monat                  €199/Monat          Custom      │
│  ─────────────────          ─────────────────   ─────────   │
│  • 1 Agent                  • 5 Agents          • Unlimited │
│  • 3 Kunden                 • 20 Kunden         • SLA       │
│  • 100 Tickets/Mon          • Unlimited         • Dediziert │
│  • Basis-Features           • Studio UI         • White-Label│
│  • E-Mail Support           • Secrets Vault     • Custom Dev│
│                             • Priority Chat                 │
│                                                             │
│  [Kostenlos testen]         [Kostenlos testen]  [Kontakt]   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### Modell 3: Usage-Based (API-Modell)

```
Pay-as-you-go:
• €0.10 pro Ticket-Verarbeitung
• €0.01 pro Memory-Abfrage  
• €5/Monat pro aktivem Kunden
• OpenAI-Kosten werden 1:1 weitergegeben

Beispiel Rechnung (kleine Agentur):
• 50 Tickets/Monat × €0.10 = €5
• 20 aktive Kunden × €5 = €100
• OpenAI-Kosten = €45
• ─────────────────────────────
• GESAMT = €150/Monat
```

---

## 🛣️ Roadmap zur Vision

### Phase 1: Foundation (Jetzt - 3 Monate)
- [x] Core Agent System
- [x] 4-Schichten Memory
- [ ] Customer-Ordner auslagern (`/customers/` statt `/agents/mohami/customers/`)
- [ ] Basic REST API für externe Integration

### Phase 2: API & Integration (3-6 Monate)
- [ ] REST API v1 (CRUD für Kunden, Agenten, Memories)
- [ ] Webhook-Support (GitHub, GitLab)
- [ ] Basic Web UI (nur View, kein Edit)

### Phase 3: Mohami Studio MVP (6-12 Monate)
- [ ] Kunden-Verwaltung UI
- [ ] Agenten-Builder UI
- [ ] Memory-Manager UI
- [ ] Simples Dashboard

### Phase 4: Enterprise Features (12+ Monate)
- [ ] Secrets Vault
- [ ] Multi-Agent Teams
- [ ] Advanced Analytics
- [ ] Audit-Logging
- [ ] SSO / LDAP Integration

---

## 🎯 Nächste Schritte (Priorisierung)

### 🔥 Critical Path (Muss zuerst)
1. **Customer-Architektur fixen**
   - `/customers/` Ordner auslagern
   - Agenten können auf alle Kunden zugreifen
   - Notwendig für Multi-Agent-Setup

2. **REST API**
   - Grundlage für jede UI
   - CRUD für: Kunden, Agenten, Memories

### ⚡ High Impact (Sollte bald)
3. **Secrets Management**
   - Sicherheitskritisch für Production
   - Vault-Integration

4. **Memory UI (Read-Only)**
   - Einfacher Browsen der Memories
   - Suche über ChromaDB

### 💡 Nice to Have (Später)
5. **Agenten-Builder UI**
6. **Dashboard mit Analytics**
7. **Playground für Tests**

---

## 🤔 Offene Fragen

1. **Soll die UI in das bestehende Frontend (Next.js)?**
   - Pro: Eine Codebase
   - Con: Frontend ist schon groß

2. **Soll es ein separates "Mohami Studio" Projekt geben?**
   - Pro: Klare Trennung, kann unabhängig deployed werden
   - Con: Mehr Wartung

3. **Wer ist die Zielgruppe für v1?**
   - a) Nur wir selbst (internes Tool)
   - b) Andere Entwickler (GitHub Open Source)
   - c) Agenturen (SaaS)

4. **Welches Auth-System?**
   - Einfach: Basic Auth / API Keys
   - Mittel: JWT mit Refresh Tokens
   - Enterprise: OAuth2 / SSO

---

> 💡 **Hinweis:** Diese Datei ist ein Lebendes Dokument. Ideen können 
> hinzugefügt, priorisiert oder verworfen werden. Diskussion ist willkommen!
