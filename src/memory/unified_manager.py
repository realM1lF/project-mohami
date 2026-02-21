"""Unified Memory Manager - Verbindet alle 4 Gedächtnis-Schichten.

Bietet eine einheitliche API für:
- Kurzzeit-Speicher (InMemoryBuffer)
- Session-Speicher (Redis)
- Langzeit-Speicher (ChromaDB)
- Episodisches Gedächtnis (SQLite)

Usage:
    manager = UnifiedMemoryManager(customer_id="alp-shopware")
    
    # Kontext speichern (auto-tier wählt passende Schicht)
    manager.store_context("current_ticket", ticket_data, tier="auto")
    
    # Kontext abrufen (sucht in allen Schichten)
    data = manager.retrieve_context("current_ticket", tier="auto")
    
    # Learning aufzeichnen
    manager.record_learning(LearningEpisode(...))
"""

from typing import Dict, Any, List, Optional, Union
from dataclasses import dataclass, field
from datetime import datetime
import os

# Import der 4 Schichten
from .short_term import InMemoryBuffer
from .session_redis import RedisMemory
from .long_term_chroma import ChromaLongTermMemory
from .episodic_db import EpisodicMemory
from .chroma_store import ChromaMemoryStore

# Versuche Redis zu importieren, fallback auf None
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False


@dataclass
class LearningEpisode:
    """Eine Lern-Episode für das episodische Gedächtnis."""
    ticket_id: str
    problem: str
    solution: str
    success: bool
    episode_type: str = "resolution"  # resolution, error, insight
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: str = field(default_factory=lambda: datetime.utcnow().isoformat())


@dataclass
class MemoryConfig:
    """Konfiguration für alle Gedächtnis-Schichten."""
    # Short Term
    short_term_ttl: int = 3600  # 1 Stunde
    
    # Session (Redis)
    session_ttl: int = 86400  # 24 Stunden
    redis_host: str = "redis"
    redis_port: int = 6379
    redis_db: int = 0
    
    # Long Term (ChromaDB)
    chroma_persist_dir: str = "./chroma_db"
    
    # Episodic (SQLite)
    episodic_db_dir: str = "./data/episodic"
    
    # Auto-Tier Rules
    auto_tier_keywords: Dict[str, str] = field(default_factory=lambda: {
        "ticket_": "session",      # Ticket-Daten -> Redis
        "chat_": "session",        # Chat -> Redis
        "pattern_": "long_term",   # Patterns -> Chroma
        "solution_": "long_term",  # Solutions -> Chroma
        "lesson_": "episodic",     # Lessons -> SQLite
        "episode_": "episodic",    # Episodes -> SQLite
        "temp_": "short_term",     # Temp -> InMemory
        "current_": "short_term",  # Current -> InMemory
    })


class UnifiedMemoryManager:
    """Verwaltet alle 4 Gedächtnis-Schichten.
    
    Bietet:
    - Einheitliche API für alle Schichten
    - Auto-Tier Auswahl basierend auf Key-Patterns
    - Cross-Tier Suche und Retrieval
    - Learning und Episode Recording
    
    Tier-Strategie:
    - "short_term": Aktive Session-Daten (schnell, flüchtig)
    - "session": Chat-History, Session-State (Redis, 24-48h)
    - "long_term": Patterns, Solutions (ChromaDB, permanent)
    - "episodic": Ticket-Resolutionen, Lessons (SQLite, permanent)
    - "auto": Automatische Auswahl basierend auf Key
    """
    
    def __init__(
        self,
        customer_id: str,
        config: MemoryConfig = None,
        redis_client=None,
        chroma_client=None
    ):
        """Initialize Unified Memory Manager.
        
        Args:
            customer_id: Customer identifier
            config: MemoryConfig (optional, uses defaults)
            redis_client: Optional pre-configured Redis client
            chroma_client: Optional pre-configured Chroma client
        """
        self.customer_id = customer_id
        self.config = config or MemoryConfig()
        
        # === Schicht 1: Short Term (In-Memory) ===
        self.short_term = InMemoryBuffer(customer_id=customer_id)
        
        # === Schicht 2: Session (Redis) ===
        if redis_client:
            self.session = RedisMemory(customer_id, redis_client)
        elif REDIS_AVAILABLE:
            try:
                redis_client = redis.Redis(
                    host=self.config.redis_host,
                    port=self.config.redis_port,
                    db=self.config.redis_db,
                    decode_responses=False
                )
                self.session = RedisMemory(customer_id, redis_client)
            except Exception:
                self.session = None
        else:
            self.session = None
        
        # === Schicht 3: Long Term (ChromaDB) ===
        if chroma_client:
            self.long_term = ChromaLongTermMemory(customer_id, chroma_client)
        else:
            try:
                chroma = ChromaMemoryStore(
                    persist_directory=self.config.chroma_persist_dir
                )
                self.long_term = ChromaLongTermMemory(customer_id, chroma)
            except Exception:
                self.long_term = None
        
        # === Schicht 4: Episodic (SQLite) ===
        db_path = os.path.join(
            self.config.episodic_db_dir,
            f"{customer_id}.db"
        )
        self.episodic = EpisodicMemory(customer_id, db_path)
    
    # === Core Operations ===
    
    def store_context(
        self,
        key: str,
        value: Any,
        tier: str = "auto",
        ttl: int = None
    ) -> bool:
        """Speichert Kontext in die gewählte Schicht.
        
        Args:
            key: Schlüssel für den Wert
            value: Der zu speichernde Wert
            tier: Ziel-Schicht ("short_term", "session", "long_term", "episodic", "auto")
            ttl: Optional custom TTL
            
        Returns:
            True wenn erfolgreich
        """
        target_tier = self._resolve_tier(key, tier)
        
        try:
            if target_tier == "short_term":
                self.short_term.set(key, value, ttl=ttl or self.config.short_term_ttl)
                return True
                
            elif target_tier == "session":
                if self.session:
                    self.session.set(key, value, ttl=ttl or self.config.session_ttl)
                    return True
                else:
                    # Fallback zu short_term wenn Redis nicht verfügbar
                    self.short_term.set(key, value, ttl=ttl or self.config.short_term_ttl)
                    return True
                    
            elif target_tier == "long_term":
                if self.long_term:
                    self.long_term.add_memory(
                        content=str(value),
                        memory_type="generic",
                        metadata={"key": key, "customer": self.customer_id}
                    )
                    return True
                return False
                
            elif target_tier == "episodic":
                # Episodic speichert keine generischen Key-Values
                # Stattdessen als "note" Episode
                content = f"{key}: {value}" if not isinstance(value, str) else value
                self.episodic.record_ticket_resolution(
                    ticket_id=key,
                    problem="Note",
                    solution=content,
                    success=True,
                    metadata={"type": "note", "value": value}
                )
                return True
                
        except Exception as e:
            print(f"Error storing to {target_tier}: {e}")
            return False
        
        return False
    
    def retrieve_context(
        self,
        key: str,
        tier: str = "auto",
        default: Any = None
    ) -> Any:
        """Ruft Kontext aus der gewählten Schicht ab.
        
        Args:
            key: Schlüssel
            tier: Quell-Schicht oder "auto" für Suche in allen
            default: Default-Wert wenn nicht gefunden
            
        Returns:
            Der gespeicherte Wert oder default
        """
        if tier == "auto":
            # Suche in allen Schichten (Reihenfolge: short -> session -> long -> episodic)
            result = self.short_term.get(key)
            if result is not None:
                return result
            
            if self.session:
                result = self.session.get(key)
                if result is not None:
                    return result
            
            # Long-term und episodic haben kein einfaches Key-Value
            # Die werden über search abgefragt
            
            return default
        
        # Spezifische Schicht
        target_tier = self._resolve_tier(key, tier)
        
        try:
            if target_tier == "short_term":
                return self.short_term.get(key, default)
                
            elif target_tier == "session":
                if self.session:
                    result = self.session.get(key)
                    return result if result is not None else default
                return default
                
            elif target_tier == "long_term":
                # Long-term verwendet search
                results = self.long_term.search(key) if self.long_term else []
                return results[0] if results else default
                
            elif target_tier == "episodic":
                # Episodic verwendet get_relevant_episodes
                episodes = self.episodic.get_relevant_episodes(key, n_results=1)
                return episodes[0] if episodes else default
                
        except Exception as e:
            print(f"Error retrieving from {target_tier}: {e}")
            return default
        
        return default
    
    def delete_context(self, key: str, tier: str = "auto") -> bool:
        """Löscht Kontext aus der gewählten Schicht.
        
        Returns:
            True wenn gelöscht
        """
        target_tier = self._resolve_tier(key, tier)
        
        try:
            if target_tier == "short_term":
                return self.short_term.delete(key)
                
            elif target_tier == "session":
                # Redis unterstützt kein einfaches delete in unserer API
                # Setze stattdessen auf None mit kurzem TTL
                if self.session:
                    self.session.set(key, None, ttl=1)
                return True
                
        except Exception:
            pass
        
        return False
    
    # === Tier-Specific Operations ===
    
    def store_session_data(self, key: str, value: Any, ttl: int = None) -> bool:
        """Speichert Daten in Session-Schicht (Redis)."""
        return self.store_context(key, value, tier="session", ttl=ttl)
    
    def get_session_data(self, key: str, default: Any = None) -> Any:
        """Holt Daten aus Session-Schicht."""
        return self.retrieve_context(key, tier="session", default=default)
    
    def store_code_pattern(
        self,
        pattern: str,
        metadata: Dict = None
    ) -> Optional[str]:
        """Speichert ein Code-Pattern in Long-Term Memory.
        
        Returns:
            Pattern ID oder None
        """
        if self.long_term:
            return self.long_term.store_code_pattern(pattern, metadata)
        return None
    
    def find_similar_patterns(
        self,
        query: str,
        limit: int = 5
    ) -> List[Dict]:
        """Findet ähnliche Code-Patterns."""
        if self.long_term:
            return self.long_term.find_similar_patterns(query, limit=limit)
        return []
    
    def store_solution(
        self,
        problem: str,
        solution: str,
        ticket_id: str,
        metadata: Dict = None
    ) -> Optional[str]:
        """Speichert eine Lösung in Long-Term Memory.
        
        Returns:
            Solution ID oder None
        """
        if self.long_term:
            return self.long_term.store_solution(problem, solution, ticket_id, metadata)
        return None
    
    def find_solutions(self, problem: str, limit: int = 5) -> List[Dict]:
        """Findet Lösungen für ein Problem."""
        if self.long_term:
            return self.long_term.find_solutions(problem, limit=limit)
        return []
    
    # === Chat Operations ===
    
    def add_chat_message(
        self,
        ticket_id: str,
        role: str,
        content: str,
        metadata: Dict = None
    ) -> bool:
        """Fügt Chat-Nachricht zur Session hinzu.
        
        Args:
            ticket_id: Ticket identifier
            role: user, assistant, system
            content: Nachrichteninhalt
            metadata: Zusätzliche Metadaten
            
        Returns:
            True wenn erfolgreich
        """
        if self.session:
            message = {
                "role": role,
                "content": content,
                "timestamp": datetime.utcnow().isoformat(),
                **(metadata or {})
            }
            self.session.add_chat_message(ticket_id, message)
            return True
        return False
    
    def get_chat_history(
        self,
        ticket_id: str,
        limit: int = 50
    ) -> List[Dict]:
        """Holt Chat-History für ein Ticket."""
        if self.session:
            return self.session.get_chat_history(ticket_id, limit=limit)
        return []
    
    def clear_chat_history(self, ticket_id: str) -> bool:
        """Löscht Chat-History für ein Ticket."""
        if self.session:
            return self.session.clear_chat_history(ticket_id)
        return False
    
    # === Learning & Episodes ===
    
    def record_learning(self, episode: LearningEpisode) -> bool:
        """Zeichnet eine Lern-Episode auf.
        
        Speichert in:
        - Episodic Memory (SQLite)
        - Long-Term Memory (als Solution wenn erfolgreich)
        
        Args:
            episode: LearningEpisode mit Problem, Solution, etc.
            
        Returns:
            True wenn erfolgreich
        """
        try:
            # 1. In Episodic Memory speichern
            self.episodic.record_ticket_resolution(
                ticket_id=episode.ticket_id,
                problem=episode.problem,
                solution=episode.solution,
                success=episode.success,
                metadata={
                    "episode_type": episode.episode_type,
                    **episode.metadata
                }
            )
            
            # 2. Wenn erfolgreich, auch in Long-Term als Solution
            if episode.success and self.long_term:
                self.long_term.store_solution(
                    problem=episode.problem,
                    solution=episode.solution,
                    ticket_id=episode.ticket_id,
                    metadata=episode.metadata
                )
            
            # 3. In Short-Term als "recent_learning" speichern
            learnings = self.short_term.get("recent_learnings", [])
            learnings.append({
                "ticket_id": episode.ticket_id,
                "problem": episode.problem[:100],
                "success": episode.success,
                "timestamp": episode.timestamp
            })
            # Nur letzte 10 behalten
            self.short_term.set("recent_learnings", learnings[-10:])
            
            return True
            
        except Exception as e:
            print(f"Error recording learning: {e}")
            return False
    
    def get_relevant_learnings(
        self,
        query: str,
        n_results: int = 3
    ) -> List[Dict]:
        """Holt relevante vergangene Learnings.
        
        Sucht in:
        - Episodic Memory (ähnliche Episoden)
        - Long-Term Memory (ähnliche Solutions)
        
        Args:
            query: Suchquery
            n_results: Anzahl der Ergebnisse
            
        Returns:
            Kombinierte Liste von Learnings
        """
        results = []
        
        # Aus Episodic Memory
        episodes = self.episodic.get_relevant_episodes(
            query, n_results=n_results, only_successful=True
        )
        for ep in episodes:
            results.append({
                "source": "episodic",
                "ticket_id": ep["ticket_id"],
                "problem": ep["problem_summary"],
                "solution": ep["solution_summary"],
                "success": ep["success"],
                "content": ep["content"]
            })
        
        # Aus Long-Term Memory
        if self.long_term:
            solutions = self.long_term.find_solutions(query, limit=n_results)
            for sol in solutions:
                meta = sol.get("metadata", {})
                results.append({
                    "source": "long_term",
                    "ticket_id": meta.get("ticket_id", "unknown"),
                    "content": sol["content"],
                    "distance": sol.get("distance")
                })
        
        return results[:n_results]
    
    def get_recent_learnings(self, limit: int = 5) -> List[Dict]:
        """Holt kürzliche Learnings aus Short-Term Memory."""
        learnings = self.short_term.get("recent_learnings", [])
        return learnings[-limit:]
    
    # === Context für Agent ===
    
    def build_agent_context(
        self,
        ticket_id: str,
        ticket_description: str = ""
    ) -> Dict[str, Any]:
        """Baut vollständigen Kontext für einen Agent.
        
        Sammelt aus allen Schichten:
        - Aktuelle Session-Daten
        - Chat-History
        - Relevante vergangene Learnings
        - Aktive Patterns
        
        Returns:
            Kontext-Dictionary für Agent
        """
        context = {
            "customer_id": self.customer_id,
            "ticket_id": ticket_id,
            "timestamp": datetime.utcnow().isoformat(),
        }
        
        # 1. Session-Daten
        context["current_data"] = self.short_term.get_all()
        context["orpa_phase"] = self.short_term.get_orpa_phase()
        
        # 2. Chat-History
        context["chat_history"] = self.get_chat_history(ticket_id, limit=20)
        
        # 3. Relevante Learnings
        if ticket_description:
            context["relevant_learnings"] = self.get_relevant_learnings(
                ticket_description, n_results=3
            )
        
        # 4. Recent Learnings
        context["recent_learnings"] = self.get_recent_learnings(limit=5)
        
        # 5. Stats
        context["memory_stats"] = self.get_stats()
        
        return context
    
    # === Utility ===
    
    def _resolve_tier(self, key: str, tier: str) -> str:
        """Bestimmt die Ziel-Schicht basierend auf Key und tier."""
        if tier != "auto":
            return tier
        
        # Prüfe Keywords
        for prefix, target in self.config.auto_tier_keywords.items():
            if key.startswith(prefix):
                return target
        
        # Default: short_term für aktive Session-Daten
        return "short_term"
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken über alle Schichten zurück."""
        stats = {
            "customer_id": self.customer_id,
            "tiers": {}
        }
        
        # Short Term
        stats["tiers"]["short_term"] = self.short_term.get_session_info()
        
        # Session
        if self.session:
            try:
                stats["tiers"]["session"] = self.session.get_stats()
            except Exception:
                stats["tiers"]["session"] = {"status": "unavailable"}
        else:
            stats["tiers"]["session"] = {"status": "disabled"}
        
        # Long Term
        if self.long_term:
            try:
                stats["tiers"]["long_term"] = self.long_term.get_stats()
            except Exception:
                stats["tiers"]["long_term"] = {"status": "unavailable"}
        else:
            stats["tiers"]["long_term"] = {"status": "disabled"}
        
        # Episodic
        try:
            stats["tiers"]["episodic"] = self.episodic.get_stats()
        except Exception:
            stats["tiers"]["episodic"] = {"status": "error"}
        
        return stats
    
    def clear_tier(self, tier: str) -> bool:
        """Löscht alle Daten einer Schicht.
        
        Args:
            tier: "short_term", "session", "long_term", "episodic", oder "all"
            
        Returns:
            True wenn erfolgreich
        """
        try:
            if tier == "short_term" or tier == "all":
                self.short_term.clear()
            
            if tier == "session" or tier == "all":
                if self.session:
                    self.session.clear_all_customer_data()
            
            if tier == "episodic" or tier == "all":
                self.episodic.clear_all()
            
            # Long-Term hat kein einfaches clear in unserer API
            
            return True
            
        except Exception as e:
            print(f"Error clearing tier {tier}: {e}")
            return False
    
    def cleanup(self):
        """Führt Cleanup in allen Schichten durch."""
        # Short Term: Entferne abgelaufene Einträge
        self.short_term.cleanup_expired()
        
        # Andere Schichten haben eigene TTL-Mechanismen
    
    def __repr__(self) -> str:
        return f"UnifiedMemoryManager(customer={self.customer_id})"
