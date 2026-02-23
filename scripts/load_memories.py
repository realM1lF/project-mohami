#!/usr/bin/env python3
"""
Load memories from markdown files into ChromaDB (Long-Term Memory).

INKREMENTELL mit UPSERT: 
- Neue Files → werden hinzugefügt
- Geänderte Files → alte Version wird ersetzt
- Unveränderte Files → werden übersprungen

Usage:
    python load_memories.py              # Lädt nur neue/geänderte Memories
    python load_memories.py --force      # Lädt ALLE Memories neu (Reset)
    python load_memories.py --dry-run    # Zeigt was geladen/ersetzt würde
"""

import asyncio
import hashlib
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Set, Tuple, Optional

from src.memory import UnifiedMemoryManager
from src.memory.unified_manager import MemoryConfig


# Konfiguration
MEMORIES_DIR = Path("agents/mohami/memories")
CUSTOMER_ID = "mohami"
CHROMA_PATH = "./data/chroma"
MEMORY_TYPE = "curated_memory"  # Collection-Name im ChromaDB


def get_file_hash(filepath: Path) -> str:
    """Erstellt einen Hash vom Datei-Inhalt (für Änderungs-Erkennung)."""
    content = filepath.read_bytes()
    return hashlib.md5(content).hexdigest()


def get_file_mod_time(filepath: Path) -> float:
    """Gibt die letzte Änderungszeit zurück."""
    return filepath.stat().st_mtime


async def find_all_memory_files() -> List[Path]:
    """Findet alle .md Files im memories Ordner (rekursiv)."""
    if not MEMORIES_DIR.exists():
        print(f"❌ Ordner nicht gefunden: {MEMORIES_DIR}")
        return []
    
    files = list(MEMORIES_DIR.rglob("*.md"))
    print(f"📁 Gefunden: {len(files)} Markdown-Dateien")
    return files


async def get_existing_memories(memory: UnifiedMemoryManager) -> Dict[str, Dict]:
    """
    Holt alle bestehenden Memories aus ChromaDB.
    
    Returns:
        Dict mit filepath als Key, enthält hash und chroma_id
    """
    try:
        # Zugriff auf die ChromaDB Collection direkt
        if not memory.long_term:
            print("   ⚠️  Long-term memory nicht verfügbar")
            return {}
        
        collection_name = f"{CUSTOMER_ID}_{MEMORY_TYPE}"
        collection = memory.long_term.chroma._get_collection(collection_name)
        
        # Hole alle Einträge
        results = collection.get(include=["metadatas"])
        
        existing = {}
        if results and results.get("ids"):
            for i, memory_id in enumerate(results["ids"]):
                metadata = results["metadatas"][i] if results["metadatas"] else {}
                source = metadata.get("source", "")
                content_hash = metadata.get("content_hash", "")
                
                if source:
                    existing[source] = {
                        "hash": content_hash,
                        "chroma_id": memory_id,
                        "loaded_at": metadata.get("loaded_at", "")
                    }
        
        return existing
        
    except Exception as e:
        print(f"⚠️  Konnte bestehende Memories nicht laden: {e}")
        return {}


async def delete_memory_by_id(memory: UnifiedMemoryManager, chroma_id: str) -> bool:
    """Löscht einen Memory-Eintrag aus ChromaDB anhand der ID."""
    try:
        collection_name = f"{CUSTOMER_ID}_{MEMORY_TYPE}"
        collection = memory.long_term.chroma._get_collection(collection_name)
        collection.delete(ids=[chroma_id])
        return True
    except Exception as e:
        print(f"   ⚠️  Konnte alte Version nicht löschen: {e}")
        return False


async def load_memory_file(
    memory: UnifiedMemoryManager, 
    filepath: Path, 
    existing_info: Optional[Dict] = None,
    dry_run: bool = False
) -> Tuple[bool, str]:
    """
    Lädt eine einzelne Memory-Datei.
    
    Returns:
        (success, action) - action ist 'added', 'updated', oder 'error'
    """
    try:
        content = filepath.read_text(encoding='utf-8')
        
        # Erstelle eindeutigen Key aus Pfad
        relative_path = filepath.relative_to(MEMORIES_DIR)
        source_path = str(filepath)
        current_hash = get_file_hash(filepath)
        
        # Prüfe ob geändert
        is_update = False
        if existing_info:
            old_hash = existing_info.get("hash", "")
            if old_hash != current_hash:
                is_update = True
                if not dry_run:
                    # Lösche alte Version
                    chroma_id = existing_info.get("chroma_id")
                    if chroma_id:
                        await delete_memory_by_id(memory, chroma_id)
        
        # Extrahiere Titel (erste H1 oder Filename)
        title = filepath.stem
        for line in content.split('\n')[:10]:
            if line.startswith('# '):
                title = line[2:].strip()
                break
        
        if dry_run:
            action = "UPDATED" if is_update else "NEW"
            print(f"   📖 [{action}] {relative_path}")
            return True, action.lower()
        
        # Erstelle eindeutige ID für ChromaDB
        chroma_id = f"memory_{filepath.stem}_{current_hash[:8]}"
        
        # Speichere in ChromaDB über den LongTermMemoryManager
        memory.long_term.add_memory(
            content=content,
            memory_type=MEMORY_TYPE,
            metadata={
                "title": title,
                "source": source_path,
                "content_hash": current_hash,
                "relative_path": str(relative_path),
                "loaded_at": datetime.now().isoformat(),
            }
        )
        
        action_text = "Aktualisiert" if is_update else "Neu geladen"
        print(f"   ✅ {action_text}: {relative_path}")
        return True, "updated" if is_update else "added"
        
    except Exception as e:
        print(f"   ❌ Fehler bei {filepath}: {e}")
        return False, "error"


async def main():
    parser = argparse.ArgumentParser(description='Lade Memories in ChromaDB (Inkrementell + Upsert)')
    parser.add_argument('--force', action='store_true', 
                       help='Alle Memories neu laden (löscht alles zuerst)')
    parser.add_argument('--dry-run', action='store_true',
                       help='Nur anzeigen, was geladen/ersetzt würde')
    parser.add_argument('--reset', action='store_true',
                       help='LÖSCHT alle bestehenden Memories und lädt neu')
    args = parser.parse_args()
    
    print("🧠 Mohami Memory Loader (Inkrementell + Upsert)\n")
    
    # Initialisiere Memory Manager
    print(f"📡 Verbinde mit ChromaDB ({CHROMA_PATH})...")
    config = MemoryConfig(chroma_persist_dir=CHROMA_PATH)
    memory = UnifiedMemoryManager(
        customer_id=CUSTOMER_ID,
        config=config
    )
    
    if not memory.long_term:
        print("❌ Long-term memory konnte nicht initialisiert werden!")
        return
    
    # Optional: Reset (alles löschen)
    if args.reset and not args.dry_run:
        print("⚠️  Lösche alle bestehenden curated memories...")
        try:
            existing = await get_existing_memories(memory)
            for source, info in existing.items():
                chroma_id = info.get("chroma_id")
                if chroma_id:
                    await delete_memory_by_id(memory, chroma_id)
            print(f"   🗑️  {len(existing)} alte Einträge gelöscht")
        except Exception as e:
            print(f"   ⚠️  Fehler beim Löschen: {e}")
    
    # Finde alle Memory-Files
    memory_files = await find_all_memory_files()
    if not memory_files:
        return
    
    # Lade bestehende Memories für Vergleich
    print("🔍 Lade bestehende Memories aus ChromaDB...")
    existing_memories = await get_existing_memories(memory)
    print(f"   📚 Bereits gespeichert: {len(existing_memories)}")
    
    # Kategorisiere Files
    files_to_add = []      # Komplett neue Files
    files_to_update = []   # Geänderte Files (Hash unterschiedlich)
    files_unchanged = []   # Identische Files
    
    for filepath in memory_files:
        source_path = str(filepath)
        current_hash = get_file_hash(filepath)
        
        if source_path in existing_memories:
            old_hash = existing_memories[source_path].get("hash", "")
            if old_hash == current_hash:
                files_unchanged.append(filepath)
            else:
                files_to_update.append((filepath, existing_memories[source_path]))
        else:
            files_to_add.append(filepath)
    
    # Zeige Status
    print(f"\n📊 Status:")
    print(f"   ⏭️  Unverändert: {len(files_unchanged)}")
    print(f"   🔄 Zu aktualisieren: {len(files_to_update)}")
    print(f"   ➕ Neu hinzuzufügen: {len(files_to_add)}")
    
    # Force Mode: Alles als neu markieren
    if args.force:
        print(f"\n🔄 FORCE-MODE: Alles wird neu geladen")
        files_to_add = memory_files
        files_to_update = []
        files_unchanged = []
        if not args.dry_run:
            # Lösche alles
            for source, info in existing_memories.items():
                chroma_id = info.get("chroma_id")
                if chroma_id:
                    await delete_memory_by_id(memory, chroma_id)
    
    # Nichts zu tun?
    total_work = len(files_to_add) + len(files_to_update)
    if total_work == 0:
        print("\n✅ Alle Memories sind aktuell!")
        return
    
    # Zeige Details im Dry-Run
    if args.dry_run:
        print(f"\n📝 DRY-RUN - Keine Änderungen werden gespeichert\n")
        if files_to_update:
            print("Zu aktualisierende Files (wurden bearbeitet):")
            for filepath, info in files_to_update:
                print(f"   🔄 {filepath.relative_to(MEMORIES_DIR)}")
                print(f"      Alte Version: {info.get('loaded_at', 'unbekannt')[:19] if info.get('loaded_at') else 'unbekannt'}")
        if files_to_add:
            print("Neue Files:")
            for filepath in files_to_add:
                print(f"   ➕ {filepath.relative_to(MEMORIES_DIR)}")
        print(f"\n{'='*50}")
        print(f"📊 Zusammenfassung: {len(files_to_add)} neu, {len(files_to_update)} aktualisiert")
        return
    
    # Führe Änderungen durch
    print(f"\n💾 Speichere Änderungen...\n")
    
    added_count = 0
    updated_count = 0
    error_count = 0
    
    # 1. Aktualisiere geänderte Files
    for filepath, existing_info in files_to_update:
        success, action = await load_memory_file(
            memory, filepath, existing_info=existing_info, dry_run=False
        )
        if action == "updated":
            updated_count += 1
        elif action == "error":
            error_count += 1
    
    # 2. Füge neue Files hinzu
    for filepath in files_to_add:
        success, action = await load_memory_file(
            memory, filepath, existing_info=None, dry_run=False
        )
        if action == "added":
            added_count += 1
        elif action == "error":
            error_count += 1
    
    # Zusammenfassung
    print(f"\n{'='*50}")
    print(f"✅ FERTIG!")
    print(f"   ➕ Neu hinzugefügt: {added_count}")
    print(f"   🔄 Aktualisiert: {updated_count}")
    print(f"   ⏭️  Unverändert: {len(files_unchanged)}")
    if error_count:
        print(f"   ❌ Fehler: {error_count}")
    print(f"\n🧠 Diese Memories bleiben auch nach Neustart erhalten!")
    print(f"   (Gespeichert in: {CHROMA_PATH})")


if __name__ == "__main__":
    asyncio.run(main())
