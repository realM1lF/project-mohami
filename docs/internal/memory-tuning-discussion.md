1) Warum wirkt Mohami trotz Full-Doku „Azubi-Level“?
Hauptgründe:
Falscher Ziel-Repo-Kontext fürs Ticket
Ticket 73cc8715... lief gegen realM1lF/personal-ki-agents, nicht gegen ein echtes Shopware-Kundenrepo.
Dann kann er nur generische Plugin-Struktur bauen, aber nicht „seniorig“ ins bestehende Shop integrieren.
Kein echter Runtime-Kontext (DDEV/DB/Shopware-Instanz)
Ohne laufendes Shopware + DB + bin/console + echte Tests bleibt es bei „Best Guess“-Code.
Memory ist absichtlich stärker begrenzt (für Stabilität)
Ihr habt Limits auf semantische Treffer/Snippet-Länge gesetzt, dadurch weniger Fachkontext pro Call:
AGENT_SEMANTIC_MEMORY_LIMIT=3
AGENT_SEMANTIC_HIT_CHARS=350
(siehe src/agents/intelligent_agent.py)
Large doc != automatisch hohe Antwortqualität
Die Full-TXT ist Wissensbasis, aber das Modell zieht pro Anfrage nur wenige passende Chunks.
Wenn Retrieval nicht exakt trifft, kommt generisches Ergebnis.
Ticket war relativ allgemein formuliert („Top Bar Plugin“)
Solche Aufgaben werden oft mit „Template-Lösung“ beantwortet, wenn keine projektspezifischen Constraints vorliegen.
2) Zur Meldung mit SHOPWARE_OFFICIAL_LLM_DOCS_FULL.txt
Die Meldung ist normal und kommt vom Editor (Performance-Schutz für große Dateien):
> tokenization/wrapping/codelens/sticky scroll etc. disabled for large file
Bedeutung:
Nur UI-Komfortfunktionen im Editor sind reduziert.
Dateiinhalt ist nicht kaputt, nicht abgeschnitten.
Mohami/Backend können die Datei weiterhin lesen/verarbeiten (über Chunks/Memory-Sync).
Wenn du „Senior-Level“ willst, brauchst du vor allem:
1) echtes Shopware-Zielrepo,
2) echte Laufzeitumgebung (DDEV + DB),
3) engere Ticketvorgaben (Akzeptanzkriterien, Shopware-Version, betroffene Dateien/Plugins).
doch, ich habe in realM1lF/personal-ki-agents ein vollwertiges shpoware projekt rein vorhin schon. Shopware instanz, ddev und datenbank dazu hat er nicht, aber wäre für die aufgabe auch nicht notwendig gewesen. Können wir am memory nicht noch was arbeiten? Wie gesagt, ich dachte, wir haben seine gedächtnis datenbank extra erstellt, damit wir ohne viele tokens schnell auf relevante themen zugreifen können.

Ich prüfe kurz noch die Retrieval-Mechanik (Chunking/Query/Limit), damit ich dir konkret sagen kann, wo ihr am Memory drehen solltet, ohne wieder Timeouts zu provozieren.
Ja, absolut — da könnt ihr am Memory deutlich verbessern, ohne Token-Kosten explodieren zu lassen.
Du hast recht mit deiner Erwartung: Die DB ist da, damit nicht die ganze Full-TXT jedes Mal ins Prompt muss.
Aktuell ist das aber sehr konservativ eingestellt.
Warum es trotz Memory noch „zu basic“ wirkt
Retrieval ist stark gedrosselt:
AGENT_SEMANTIC_MEMORY_LIMIT=3
AGENT_SEMANTIC_HIT_CHARS=350
Das gibt dem Modell oft nur kurze Fragmente statt belastbarer Shopware-Muster.
Query ist relativ simpel (title + description + understanding + approach) und holt nicht immer die besten Shopware-Chunks.
Optional: Wenn Ticket auf Deutsch ist, viele Docs aber Englisch, kann die Trefferqualität sinken.
Wichtig zu deiner Meldung mit der großen Datei
Die IDE-Meldung („tokenization... turned off“) ist nur Editor-Performance, nicht Memory/Agent-Qualität.
Die Datei bleibt nutzbar.
Konkreter, schneller Tuning-Plan (ohne großen Umbau)
1) Retrieval-Budget leicht erhöhen (Quick Win)
Per Env-Config testen:
AGENT_SEMANTIC_MEMORY_LIMIT=5
AGENT_SEMANTIC_CUSTOMER_LIMIT=3
AGENT_SEMANTIC_HIT_CHARS=700
optional AGENT_LLM_TIMEOUT_SECONDS=120 (weil Kontext größer wird)
Das ist meist der beste erste Hebel.
2) Zweistufiges Retrieval (sehr effektiv)
Reasoning: klein halten (aktuell)
Planning/Act: gezielt mehr Shopware-Kontext nachladen (nur für relevante Sections)
So bleibt es schnell, aber beim Umsetzen genauer.
3) Query-Verbesserung
Vor der Suche 3–5 Suchbegriffe ableiten (z. B. storefront, subscriber, twig, plugin base class, services.xml) und damit zusätzlich suchen/reranken.
4) Strukturierteres Chunking
Nicht nur Zeichenblöcke, sondern entlang von Markdown-Überschriften/Codeblöcken schneiden.
Dann landen vollständige Patterns im Treffer statt abgeschnittener Schnipsel.
5) „High-Value Shopware Patterns“ als kuratierter Layer
Kurze, verlässliche Pattern-Datei (Plugin-Skelett, Subscriber, Twig-Include, services.xml, DI, lifecycle).
Die kommt mit hoher Priorität in Retrieval.