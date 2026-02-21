"""Schicht 2: Session Memory (Redis).

Diese Schicht speichert:
- Chat-Verlauf und Konversationen
- Sitzungs-State (ORPA-Phasen, Kontext)
- Temporäre Daten und Zwischenergebnisse

Lebensdauer: 24-48 Stunden (TTL)
Kunden-Isolation: Key-Prefix customer:{customer_id}:...
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    redis = None


class CustomerIsolationViolation(Exception):
    """Raised when a memory access violates customer isolation."""
    pass


class RedisMemory:
    """Redis-basierte Session-Speicherung mit Kunden-Isolation.
    
    Alle Keys werden automatisch mit customer:{customer_id}: prefixed.
    Unterstützt TTL für automatische Cleanup.
    
    Usage:
        redis_client = redis.Redis(host='redis', port=6379)
        memory = RedisMemory(customer_id="alp-shopware", redis_client=redis_client)
        
        # Chat
        memory.add_chat_message("ticket-123", {"role": "user", "content": "Hilfe"})
        history = memory.get_chat_history("ticket-123")
    """
    
    # Standard-TTLs
    DEFAULT_TTL = 86400  # 24 Stunden
    CHAT_TTL = 86400 * 2  # 48 Stunden
    
    def __init__(self, customer_id: str, redis_client: 'redis.Redis'):
        """Initialize Redis Memory.
        
        Args:
            customer_id: Customer identifier for isolation
            redis_client: Redis client
        """
        self.customer_id = customer_id
        self.redis = redis_client
        self.prefix = f"customer:{customer_id}"
    
    def _key(self, *parts: str) -> str:
        """Erstellt einen customer-isolierten Key."""
        return f"{self.prefix}:{':'.join(parts)}"
    
    # === Basic Operations ===
    
    def set(self, key: str, value: Any, ttl: int = 86400) -> None:
        """Speichert einen Wert in Redis.
        
        Args:
            key: Schlüssel (wird mit customer-Prefix versehen)
            value: Der zu speichernde Wert (wird zu JSON serialisiert)
            ttl: Time-to-live in Sekunden (default: 86400 = 24 Stunden)
        """
        full_key = self._key("data", key)
        json_value = json.dumps({
            "value": value,
            "stored_at": datetime.utcnow().isoformat()
        })
        self.redis.setex(full_key, ttl, json_value)
    
    def get(self, key: str) -> Any:
        """Liest einen Wert aus Redis.
        
        Args:
            key: Schlüssel
            
        Returns:
            Der gespeicherte Wert oder None
        """
        full_key = self._key("data", key)
        data = self.redis.get(full_key)
        
        if data:
            try:
                parsed = json.loads(data)
                return parsed.get("value")
            except json.JSONDecodeError:
                return None
        return None
    
    # === Chat History ===
    
    def get_chat_history(self, ticket_id: str, limit: int = 50) -> List[Dict]:
        """Lädt Chat-Verlauf für ein Ticket.
        
        Args:
            ticket_id: Ticket identifier
            limit: Maximum number of messages (neueste zuerst)
            
        Returns:
            List of messages
        """
        key = self._key("chat", ticket_id, "messages")
        messages = self.redis.lrange(key, -limit, -1)
        return [json.loads(m) for m in messages]
    
    def add_chat_message(self, ticket_id: str, message: Dict) -> None:
        """Fügt Nachricht zum Chat-Verlauf hinzu.
        
        Args:
            ticket_id: Ticket identifier
            message: Message dict mit 'role' und 'content'
                z.B. {"role": "user", "content": "Hilfe benötigt"}
        """
        key = self._key("chat", ticket_id, "messages")
        
        # Stelle sicher dass Timestamp vorhanden
        if "timestamp" not in message:
            message = {
                **message,
                "timestamp": datetime.utcnow().isoformat()
            }
        
        # Pipeline: RPUSH + LTRIM + EXPIRE
        pipe = self.redis.pipeline()
        pipe.rpush(key, json.dumps(message))
        pipe.ltrim(key, -100, -1)  # Nur letzte 100 behalten
        pipe.expire(key, self.CHAT_TTL)
        pipe.execute()
    
    def clear_chat_history(self, ticket_id: str) -> bool:
        """Löscht Chat-Verlauf für ein Ticket.
        
        Returns:
            True wenn Daten gelöscht wurden
        """
        key = self._key("chat", ticket_id, "messages")
        return self.redis.delete(key) > 0
    
    # === Session Management ===
    
    def create_session(self, session_id: str, metadata: Dict = None) -> Dict[str, Any]:
        """Erstellt eine neue Session.
        
        Args:
            session_id: Unique session identifier
            metadata: Additional session metadata
            
        Returns:
            Session data dictionary
        """
        session_data = {
            "session_id": session_id,
            "customer_id": self.customer_id,
            "started_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "status": "active",
            "metadata": metadata or {}
        }
        
        key = self._key("session", session_id)
        self.redis.setex(key, self.DEFAULT_TTL, json.dumps(session_data))
        
        return session_data
    
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lädt Session-Metadaten."""
        key = self._key("session", session_id)
        data = self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Aktualisiert Session-Daten."""
        session = self.get_session(session_id)
        if not session:
            return None
        
        session.update(updates)
        session["last_activity"] = datetime.utcnow().isoformat()
        
        key = self._key("session", session_id)
        self.redis.setex(key, self.DEFAULT_TTL, json.dumps(session))
        
        return session
    
    def end_session(self, session_id: str) -> bool:
        """Beendet eine Session."""
        session = self.get_session(session_id)
        if session:
            session["status"] = "ended"
            session["ended_at"] = datetime.utcnow().isoformat()
            
            key = self._key("session", session_id)
            # Kürzere TTL für beendete Sessions (1 Stunde)
            self.redis.setex(key, 3600, json.dumps(session))
            return True
        return False
    
    # === Context Management ===
    
    def set_context(self, session_id: str, context: Dict[str, Any], ttl: int = None) -> None:
        """Speichert Session-Kontext."""
        key = self._key("context", session_id)
        context_data = {
            **context,
            "updated_at": datetime.utcnow().isoformat()
        }
        self.redis.setex(key, ttl or self.DEFAULT_TTL, json.dumps(context_data))
    
    def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lädt Session-Kontext."""
        key = self._key("context", session_id)
        data = self.redis.get(key)
        return json.loads(data) if data else None
    
    # === Utility ===
    
    def clear_all_customer_data(self) -> int:
        """Löscht ALLE Daten für diesen Kunden (Vorsicht!)."""
        pattern = self._key("*")
        keys = self.redis.keys(pattern)
        if keys:
            return self.redis.delete(*keys)
        return 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Redis-Statistiken für diesen Kunden zurück."""
        pattern = self._key("*")
        keys = self.redis.keys(pattern)
        
        # Nach Typ gruppieren
        by_type = {}
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.replace(self.prefix + ":", "").split(":")
            key_type = parts[0] if parts else "unknown"
            by_type[key_type] = by_type.get(key_type, 0) + 1
        
        return {
            "customer_id": self.customer_id,
            "total_keys": len(keys),
            "by_type": by_type
        }
    
    def __repr__(self) -> str:
        return f"RedisMemory(customer={self.customer_id})"
