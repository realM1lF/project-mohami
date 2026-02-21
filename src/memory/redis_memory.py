"""Schicht 2: Session Memory (Redis).

Diese Schicht speichert:
- Chat-Verlauf und Konversationen
- Sitzungs-State (ORPA-Phasen, Kontext)
- Temporäre Daten und Zwischenergebnisse
- Rate Limits und Quotas

Lebensdauer: 24-48 Stunden (TTL)
Kunden-Isolation: Key-Prefix customer:{customer_id}:...
"""

import json
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
import redis.asyncio as redis


class CustomerIsolationViolation(Exception):
    """Raised when a memory access violates customer isolation."""
    pass


class RedisMemory:
    """Redis-basierte Session-Speicherung mit Kunden-Isolation.
    
    Alle Keys werden automatisch mit customer:{customer_id}: prefixed.
    Unterstützt TTL für automatische Cleanup.
    
    Usage:
        redis_client = redis.Redis(host='redis', port=6379)
        memory = RedisMemory(redis_client, customer_id="alp-shopware")
        
        # Session
        await memory.create_session("sess_123", "agent_001", ticket_id="TICKET-42")
        
        # Chat
        await memory.append_message("chat_456", "user", "Hilfe benötigt", token_count=10)
        
        # Context
        await memory.set_context("sess_123", {"current_phase": "observe"})
    """
    
    # Standard-TTLs
    SESSION_TTL = timedelta(hours=24)
    CHAT_TTL = timedelta(hours=48)
    CONTEXT_TTL = timedelta(hours=24)
    CACHE_TTL = timedelta(minutes=15)
    TEMP_TTL = timedelta(minutes=30)
    LOCK_TTL = timedelta(minutes=5)
    
    def __init__(self, redis_client: redis.Redis, customer_id: str):
        """Initialize Redis Memory.
        
        Args:
            redis_client: Async Redis client
            customer_id: Customer identifier for isolation
        """
        self.redis = redis_client
        self.customer_id = customer_id
        self._prefix = f"customer:{customer_id}"
    
    def _key(self, *parts: str) -> str:
        """Erstellt einen customer-isolierten Key."""
        return f"{self._prefix}:{':'.join(parts)}"
    
    def _validate_customer(self, resource_customer_id: str) -> bool:
        """Validiert Kunden-Zugriff."""
        if resource_customer_id != self.customer_id:
            raise CustomerIsolationViolation(
                f"Zugriff verweigert: Agent für '{self.customer_id}' "
                f"darf nicht auf Daten von '{resource_customer_id}' zugreifen"
            )
        return True
    
    # === Session Management ===
    
    async def create_session(
        self,
        session_id: str,
        agent_id: str,
        ticket_id: Optional[str] = None,
        metadata: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """Erstellt eine neue Agent-Session.
        
        Args:
            session_id: Unique session identifier
            agent_id: Agent identifier
            ticket_id: Optional associated ticket
            metadata: Additional session metadata
            
        Returns:
            Session data dictionary
        """
        session_data = {
            "session_id": session_id,
            "agent_id": agent_id,
            "ticket_id": ticket_id,
            "customer_id": self.customer_id,
            "started_at": datetime.utcnow().isoformat(),
            "last_activity": datetime.utcnow().isoformat(),
            "status": "active",
            "metadata": metadata or {}
        }
        
        key = self._key("session", session_id, "meta")
        await self.redis.setex(
            key,
            self.SESSION_TTL,
            json.dumps(session_data)
        )
        
        return session_data
    
    async def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lädt Session-Metadaten."""
        key = self._key("session", session_id, "meta")
        data = await self.redis.get(key)
        
        if data:
            return json.loads(data)
        return None
    
    async def update_session(self, session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Aktualisiert Session-Daten."""
        session = await self.get_session(session_id)
        if not session:
            return None
        
        session.update(updates)
        session["last_activity"] = datetime.utcnow().isoformat()
        
        key = self._key("session", session_id, "meta")
        await self.redis.setex(
            key,
            self.SESSION_TTL,
            json.dumps(session)
        )
        
        return session
    
    async def end_session(self, session_id: str) -> bool:
        """Beendet eine Session (setzt Status auf 'ended')."""
        session = await self.get_session(session_id)
        if session:
            session["status"] = "ended"
            session["ended_at"] = datetime.utcnow().isoformat()
            
            key = self._key("session", session_id, "meta")
            # Kürzere TTL für beendete Sessions (1 Stunde)
            await self.redis.setex(
                key,
                timedelta(hours=1),
                json.dumps(session)
            )
            return True
        return False
    
    async def update_activity(self, session_id: str) -> bool:
        """Aktualisiert letzte Aktivität und verlängert TTL."""
        key = self._key("session", session_id, "meta")
        return await self.redis.expire(key, self.SESSION_TTL)
    
    # === Session Context ===
    
    async def set_context(self, session_id: str, context: Dict[str, Any]) -> None:
        """Speichert Session-Kontext.
        
        Speichert:
        - ORPA-Phase
        - Aktive Tools
        - Temporäre Variablen
        """
        key = self._key("session", session_id, "context")
        context_data = {
            **context,
            "updated_at": datetime.utcnow().isoformat()
        }
        await self.redis.setex(key, self.CONTEXT_TTL, json.dumps(context_data))
    
    async def get_context(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Lädt Session-Kontext."""
        key = self._key("session", session_id, "context")
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def update_context(self, session_id: str, updates: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Aktualisiert Session-Kontext (merge)."""
        current = await self.get_context(session_id) or {}
        current.update(updates)
        current["updated_at"] = datetime.utcnow().isoformat()
        
        await self.set_context(session_id, current)
        return current
    
    # === Chat History ===
    
    async def append_message(
        self,
        chat_id: str,
        role: str,  # "user", "assistant", "system", "tool"
        content: str,
        token_count: int = 0,
        metadata: Optional[Dict] = None
    ) -> None:
        """Fügt Nachricht zum Chat-Verlauf hinzu.
        
        Args:
            chat_id: Chat/Conversation identifier
            role: Message role
            content: Message content
            token_count: Token count for quota tracking
            metadata: Additional metadata (z.B. tool_calls)
        """
        key = self._key("chat", chat_id, "messages")
        
        message = {
            "role": role,
            "content": content,
            "timestamp": datetime.utcnow().isoformat(),
            "token_count": token_count,
            "metadata": metadata or {}
        }
        
        # Pipeline: RPUSH + LTRIM + EXPIRE
        pipe = self.redis.pipeline()
        pipe.rpush(key, json.dumps(message))
        pipe.ltrim(key, -100, -1)  # Nur letzte 100 behalten
        pipe.expire(key, self.CHAT_TTL)
        await pipe.execute()
        
        # Token-Count aktualisieren
        if token_count > 0:
            token_key = self._key("chat", chat_id, "token_count")
            await self.redis.incrby(token_key, token_count)
            await self.redis.expire(token_key, self.CHAT_TTL)
    
    async def get_chat_history(self, chat_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        """Lädt Chat-Verlauf.
        
        Args:
            chat_id: Chat identifier
            limit: Maximum number of messages (neueste zuerst)
            
        Returns:
            List of messages
        """
        key = self._key("chat", chat_id, "messages")
        messages = await self.redis.lrange(key, -limit, -1)
        return [json.loads(m) for m in messages]
    
    async def get_chat_summary(self, chat_id: str) -> Optional[str]:
        """Lädt laufende Chat-Zusammenfassung (für Kontext-Fenster)."""
        key = self._key("chat", chat_id, "summary")
        summary = await self.redis.get(key)
        return summary.decode() if summary else None
    
    async def update_chat_summary(self, chat_id: str, summary: str) -> None:
        """Aktualisiert Chat-Zusammenfassung."""
        key = self._key("chat", chat_id, "summary")
        await self.redis.setex(key, self.CHAT_TTL, summary)
    
    async def get_chat_token_count(self, chat_id: str) -> int:
        """Gibt aktuellen Token-Verbrauch zurück."""
        key = self._key("chat", chat_id, "token_count")
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    # === Caching Layer ===
    
    async def cache_get(self, cache_type: str, cache_key: str) -> Optional[Any]:
        """Generischer Cache-Getter.
        
        Cache-Typen:
        - tech_stack: Kunden-Konfiguration (selten ändernd)
        - plugins: Plugin-Liste (mittlere Änderungsrate)
        - pattern: Code-Patterns (Query-Cache)
        - git: Git-API Responses
        """
        key = self._key("cache", cache_type, cache_key)
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    async def cache_set(
        self,
        cache_type: str,
        cache_key: str,
        value: Any,
        ttl: Optional[timedelta] = None
    ) -> None:
        """Generischer Cache-Setter."""
        key = self._key("cache", cache_type, cache_key)
        ttl = ttl or self.CACHE_TTL
        await self.redis.setex(key, ttl, json.dumps(value))
    
    async def cache_delete(self, cache_type: str, cache_key: str) -> bool:
        """Löscht Cache-Eintrag."""
        key = self._key("cache", cache_type, cache_key)
        return await self.redis.delete(key) > 0
    
    async def cache_clear_type(self, cache_type: str) -> int:
        """Löscht alle Einträge eines Cache-Typs."""
        pattern = self._key("cache", cache_type, "*")
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0
    
    # === ORPA State ===
    
    async def set_orpa_phase(self, session_id: str, phase: str) -> None:
        """Setzt aktuelle ORPA-Phase."""
        key = self._key("orpa", session_id, "current_phase")
        await self.redis.setex(key, timedelta(hours=1), phase)
    
    async def get_orpa_phase(self, session_id: str) -> Optional[str]:
        """Gibt aktuelle ORPA-Phase zurück."""
        key = self._key("orpa", session_id, "current_phase")
        phase = await self.redis.get(key)
        return phase.decode() if phase else None
    
    async def add_orpa_observation(self, session_id: str, observation: str) -> None:
        """Fügt ORPA-Beobachtung hinzu."""
        key = self._key("orpa", session_id, "observations")
        obs_data = {
            "content": observation,
            "timestamp": datetime.utcnow().isoformat()
        }
        pipe = self.redis.pipeline()
        pipe.rpush(key, json.dumps(obs_data))
        pipe.ltrim(key, -50, -1)  # Max 50 Beobachtungen
        pipe.expire(key, timedelta(hours=1))
        await pipe.execute()
    
    async def get_orpa_observations(self, session_id: str, limit: int = 20) -> List[Dict]:
        """Gibt ORPA-Beobachtungen zurück."""
        key = self._key("orpa", session_id, "observations")
        observations = await self.redis.lrange(key, -limit, -1)
        return [json.loads(o) for o in observations]
    
    async def set_orpa_reasoning(self, session_id: str, reasoning: str) -> None:
        """Speichert Reasoning-Output."""
        key = self._key("orpa", session_id, "reasoning")
        await self.redis.setex(key, timedelta(hours=1), reasoning)
    
    async def get_orpa_reasoning(self, session_id: str) -> Optional[str]:
        """Gibt Reasoning-Output zurück."""
        key = self._key("orpa", session_id, "reasoning")
        reasoning = await self.redis.get(key)
        return reasoning.decode() if reasoning else None
    
    async def add_orpa_plan_step(self, session_id: str, step: Dict[str, Any]) -> None:
        """Fügt Plan-Schritt hinzu."""
        key = self._key("orpa", session_id, "plan")
        step["timestamp"] = datetime.utcnow().isoformat()
        pipe = self.redis.pipeline()
        pipe.rpush(key, json.dumps(step))
        pipe.expire(key, timedelta(hours=1))
        await pipe.execute()
    
    async def get_orpa_plan(self, session_id: str) -> List[Dict]:
        """Gibt aktuellen Plan zurück."""
        key = self._key("orpa", session_id, "plan")
        steps = await self.redis.lrange(key, 0, -1)
        return [json.loads(s) for s in steps]
    
    async def update_plan_step_status(
        self,
        session_id: str,
        step_index: int,
        status: str,  # "pending", "in_progress", "completed", "failed"
        result: Any = None
    ) -> bool:
        """Aktualisiert Status eines Plan-Schritts."""
        plan = await self.get_orpa_plan(session_id)
        if 0 <= step_index < len(plan):
            plan[step_index]["status"] = status
            if result is not None:
                plan[step_index]["result"] = result
            plan[step_index]["updated_at"] = datetime.utcnow().isoformat()
            
            # Speichern (löschen + neu schreiben)
            key = self._key("orpa", session_id, "plan")
            pipe = self.redis.pipeline()
            pipe.delete(key)
            for step in plan:
                pipe.rpush(key, json.dumps(step))
            pipe.expire(key, timedelta(hours=1))
            await pipe.execute()
            return True
        return False
    
    # === Temporary Data ===
    
    async def set_temp(self, session_id: str, artifact_id: str, data: Any, ttl: Optional[timedelta] = None) -> None:
        """Speichert temporäre Arbeitsdaten.
        
        Args:
            session_id: Session identifier
            artifact_id: Artifact identifier (z.B. "diff_output", "file_content")
            data: Data to store
            ttl: Optional custom TTL
        """
        key = self._key("temp", session_id, artifact_id)
        await self.redis.setex(
            key,
            ttl or self.TEMP_TTL,
            json.dumps({
                "data": data,
                "stored_at": datetime.utcnow().isoformat()
            })
        )
    
    async def get_temp(self, session_id: str, artifact_id: str) -> Optional[Any]:
        """Lädt temporäre Daten."""
        key = self._key("temp", session_id, artifact_id)
        stored = await self.redis.get(key)
        if stored:
            return json.loads(stored)["data"]
        return None
    
    async def delete_temp(self, session_id: str, artifact_id: str) -> bool:
        """Löscht temporäre Daten."""
        key = self._key("temp", session_id, artifact_id)
        return await self.redis.delete(key) > 0
    
    # === Distributed Locking ===
    
    async def acquire_lock(
        self,
        resource_type: str,
        resource_id: str,
        agent_id: str,
        ttl: Optional[timedelta] = None
    ) -> bool:
        """Versucht Lock zu erwerben.
        
        Args:
            resource_type: "ticket", "file", "branch"
            resource_id: Resource identifier
            agent_id: Agent trying to acquire lock
            ttl: Lock TTL
            
        Returns:
            True if lock acquired
        """
        key = self._key("lock", resource_type, resource_id)
        lock_data = json.dumps({
            "agent_id": agent_id,
            "acquired_at": datetime.utcnow().isoformat()
        })
        
        # NX = Nur setzen wenn nicht existiert
        acquired = await self.redis.set(key, lock_data, nx=True, ex=ttl or self.LOCK_TTL)
        return acquired is not None
    
    async def release_lock(self, resource_type: str, resource_id: str, agent_id: str) -> bool:
        """Gibt Lock frei (nur wenn wir ihn besitzen).
        
        Returns:
            True if lock was released
        """
        key = self._key("lock", resource_type, resource_id)
        
        current = await self.redis.get(key)
        if not current:
            return False
        
        data = json.loads(current)
        if data.get("agent_id") != agent_id:
            return False
        
        await self.redis.delete(key)
        return True
    
    async def extend_lock(
        self,
        resource_type: str,
        resource_id: str,
        agent_id: str,
        additional_ttl: timedelta
    ) -> bool:
        """Verlängert Lock (Heartbeat).
        
        Returns:
            True if lock was extended
        """
        key = self._key("lock", resource_type, resource_id)
        
        current = await self.redis.get(key)
        if not current:
            return False
        
        data = json.loads(current)
        if data.get("agent_id") != agent_id:
            return False
        
        await self.redis.expire(key, additional_ttl)
        return True
    
    async def get_lock_info(self, resource_type: str, resource_id: str) -> Optional[Dict]:
        """Gibt Lock-Info zurück (ohne Änderung)."""
        key = self._key("lock", resource_type, resource_id)
        data = await self.redis.get(key)
        return json.loads(data) if data else None
    
    # === Rate Limiting & Quotas ===
    
    async def increment_quota(self, quota_type: str, amount: int = 1) -> int:
        """Erhöht Quota-Zähler.
        
        Args:
            quota_type: z.B. "llm_tokens", "api_calls:github"
            amount: Amount to increment
            
        Returns:
            New count
        """
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = self._key("quota", quota_type, today)
        new_count = await self.redis.incrby(key, amount)
        await self.redis.expire(key, timedelta(hours=48))
        return new_count
    
    async def get_quota(self, quota_type: str) -> int:
        """Gibt aktuellen Quota-Verbrauch zurück."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        key = self._key("quota", quota_type, today)
        count = await self.redis.get(key)
        return int(count) if count else 0
    
    async def check_rate_limit(self, limit_name: str, max_calls: int, window_seconds: int) -> bool:
        """Prüft Rate Limit (Sliding Window).
        
        Args:
            limit_name: Name des Limits
            max_calls: Maximum erlaubte Calls
            window_seconds: Zeitfenster in Sekunden
            
        Returns:
            True wenn erlaubt, False wenn limitiert
        """
        key = self._key("rate_limit", limit_name)
        now = datetime.utcnow().timestamp()
        window_start = now - window_seconds
        
        # Alte Einträge entfernen und neuen hinzufügen
        pipe = self.redis.pipeline()
        pipe.zremrangebyscore(key, 0, window_start)
        pipe.zadd(key, {str(now): now})
        pipe.zcard(key)
        pipe.expire(key, window_seconds)
        
        results = await pipe.execute()
        current_count = results[2]
        
        return current_count <= max_calls
    
    # === Cleanup ===
    
    async def clear_all_customer_data(self) -> int:
        """Löscht ALLE Daten für diesen Kunden (Vorsicht!)."""
        pattern = self._key("*")
        keys = await self.redis.keys(pattern)
        if keys:
            return await self.redis.delete(*keys)
        return 0
    
    async def get_stats(self) -> Dict[str, Any]:
        """Gibt Redis-Statistiken für diesen Kunden zurück."""
        pattern = self._key("*")
        keys = await self.redis.keys(pattern)
        
        # Nach Typ gruppieren
        by_type = {}
        for key in keys:
            key_str = key.decode() if isinstance(key, bytes) else key
            parts = key_str.replace(self._prefix + ":", "").split(":")
            key_type = parts[0] if parts else "unknown"
            by_type[key_type] = by_type.get(key_type, 0) + 1
        
        return {
            "customer_id": self.customer_id,
            "total_keys": len(keys),
            "by_type": by_type
        }
