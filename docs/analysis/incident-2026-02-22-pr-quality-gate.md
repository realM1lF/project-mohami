# Analyse: PR-Quality-Gate-Fehler (Ticket #a851e2ab)

## Was passiert ist

- Ticket: Shopware-Plugin „Top-Bar“ mit „Hallo Welt“
- Agent hat Branch + Commits erstellt (laut Gate: branch_ok, commit_ok)
- Quality Gate schlug fehl: **„Pull Request wurde nicht erfolgreich erstellt“**
- → pr_ok war `false`

## Ablauf-Logik (Code-Trace)

1. **Quality Gate** läuft nur, wenn der Workflow in `COMPLETED` endet.
2. `COMPLETED` wird nur erreicht, wenn **alle** Schritte des Plans erfolgreich waren (`all_success = True`).
3. Wenn ein Schritt fehlschlägt → `break` → keine weiteren Schritte → `all_success = False` → Übergang zu REASONING oder ERROR, **kein** Quality Gate.
4. **Folgerung:** Der Plan wurde vollständig ausgeführt, alle Schritte waren erfolgreich – aber es gab **keinen** erfolgreichen `github_create_pr`-Schritt in den Ergebnissen.

## Mögliche Ursachen

### 1. Plan enthielt keinen PR-Schritt (sehr wahrscheinlich)

Für ein Shopware-Plugin erzeugt das LLM typischerweise viele `github_write_file`-Schritte (z.B. composer.json, Plugin-Klasse, services.xml, Twig, CSS, …). Der Plan kann so aussehen:

```
Step 1: github_get_repo_info
Step 2: github_create_branch
Step 3: github_write_file (composer.json)
Step 4: github_write_file (Plugin.php)
Step 5: github_write_file (services.xml)
Step 6: github_write_file (Twig-Template)
Step 7: github_write_file (CSS)
Step 8: github_create_pr   ← fehlt evtl.
```

**Warum fehlt der PR-Schritt?**

- **Truncation:** `llm_max_tokens = 4096` – bei langen Plänen kann die Antwort abgeschnitten werden, der letzte Schritt (PR) fällt weg.
- **LLM-Omission:** Bei vielen Schritten vergisst das Modell manchmal den PR-Schritt am Ende.
- **Parse-Fehler:** Wenn das JSON nicht sauber geparst wird, greift ein Regex-Fallback; der könnte bei komplexem JSON Schritte verlieren.

### 2. PR-Schritt war im Plan, aber Tool-Aufruf schlug fehl

- Dann wäre `all_success = False` und der Workflow hätte **nicht** `COMPLETED` erreicht.
- Das Quality Gate würde in diesem Fall gar nicht laufen.
- **→ Passt nicht** zum beobachteten Verhalten (Gate lief, pr_ok = false).

### 3. GitHub-API-Fehler

- Wenn `create_pr` einen Fehler wirft (außer „already exists“), gibt das Tool `success=False` zurück.
- Dann würde der Agent abbrechen und nicht `COMPLETED` erreichen.
- **→ Passt nicht** zum beobachteten Verhalten.

## Warum früher keine Probleme?

- Frühere Tickets waren vermutlich einfacher (weniger Dateien, kürzerer Plan).
- Kürzerer Plan → weniger Truncation, PR-Schritt bleibt erhalten.
- Oder: früher wurde der Fallback-Plan genutzt (`_create_standard_github_plan`), der immer einen PR-Schritt enthält.

## Empfohlene Fixes (ohne Workaround)

1. **Plan-Validierung:** Nach dem Parsen prüfen, ob `github_create_pr` im Plan vorkommt. Wenn nicht und es ein Repo-Ticket ist → PR-Schritt automatisch anhängen.
2. **Fallback-Plan:** Wenn der geparste Plan keinen PR-Schritt hat, den letzten Schritt durch `github_create_pr` ergänzen (analog zu `_create_standard_github_plan`).
3. **Token-Limit:** Für die Planning-Phase `max_tokens` erhöhen (z.B. 6144 oder 8192), um Truncation bei langen Plänen zu reduzieren.
4. **Prompt-Verstärkung:** Im Planning-Prompt explizit fordern: „Der letzte Schritt MUSS github_create_pr sein, wenn Repository-Änderungen geplant sind.“

## Was der Workaround (require_pr_for_success: false) macht

- Er verhindert nur, dass das Gate bei fehlendem PR fehlschlägt.
- Die eigentliche Ursache (fehlender PR-Schritt im Plan) bleibt ungelöst.
- Sinnvoll als Übergang, aber die oben genannten Fixes sollten umgesetzt werden.

---

## Umgesetzter Fix (2026-02-22)

**`_ensure_pr_step_if_repo_changes`** in `intelligent_agent.py`:
- Nach dem Plan-Parsing wird geprüft: Hat der Plan Repo-Änderungen (create_branch/write_file), aber keinen `github_create_pr`?
- Wenn ja → PR-Step wird automatisch angehängt (Branch/Base aus Plan oder Kontext).
- Behebt LLM-Omission und Truncation bei komplexen Plänen.
