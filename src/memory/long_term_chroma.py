"""Schicht 3: Long Term Memory (ChromaDB).

Diese Schicht speichert:
- Code-Patterns und Lösungen
- Wiederkehrende Probleme und deren Lösungen
- Embeddings für semantische Suche

Lebensdauer: Permanent
"""

from typing import Dict, Any, List, Optional
from datetime import datetime
import hashlib
import json

from .chroma_store import ChromaMemoryStore


def _sanitize_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure all metadata values are ChromaDB-compatible primitives (str, int, float, bool)."""
    sanitized = {}
    for key, value in metadata.items():
        if isinstance(value, (str, int, float, bool)):
            sanitized[key] = value
        elif value is None:
            sanitized[key] = ""
        elif isinstance(value, (list, dict)):
            sanitized[key] = json.dumps(value, default=str)
        else:
            sanitized[key] = str(value)
    return sanitized


class ChromaLongTermMemory:
    """Langzeit-Gedächtnis basierend auf ChromaDB.
    
    Nutzt bestehende chroma_store.py für:
    - Code-Patterns Speicherung
    - Semantische Suche nach ähnlichen Patterns
    - Lösungen für wiederkehrende Probleme
    
    Usage:
        chroma_client = ChromaMemoryStore(persist_directory="./chroma_db")
        memory = ChromaLongTermMemory(customer_id="alp-shopware", chroma_client=chroma_client)
        
        # Pattern speichern
        memory.store_code_pattern(
            pattern="Service decoration pattern",
            metadata={"file": "services.xml", "plugin": "SwagPayPal"}
        )
        
        # Ähnliche Patterns finden
        similar = memory.find_similar_patterns("How to decorate a service?")
    """
    
    def __init__(self, customer_id: str, chroma_client: ChromaMemoryStore):
        """Initialize Long Term Memory.
        
        Args:
            customer_id: Customer identifier for isolation
            chroma_client: ChromaMemoryStore instance
        """
        self.customer_id = customer_id
        self.chroma = chroma_client
        
        # Collection-Names für verschiedene Datentypen
        self._patterns_collection = f"{customer_id}_patterns"
        self._solutions_collection = f"{customer_id}_solutions"
    
    def _generate_id(self, content: str, prefix: str = "") -> str:
        """Generate unique ID for content."""
        hash_input = f"{prefix}:{content[:200]}"
        return hashlib.md5(hash_input.encode()).hexdigest()
    
    # === Code Patterns ===
    
    def store_code_pattern(
        self, 
        pattern: str, 
        metadata: Dict = None,
        embedding: List[float] = None
    ) -> str:
        """Speichert ein Code-Pattern.
        
        Args:
            pattern: Das Code-Pattern als String (z.B. Code-Beispiel, Beschreibung)
            metadata: Zusätzliche Metadaten wie file, plugin, etc.
            embedding: Optional pre-computed embedding
            
        Returns:
            Pattern ID
        """
        pattern_id = self._generate_id(pattern, "pattern")
        
        doc_metadata = _sanitize_metadata({
            "type": "code_pattern",
            "customer": self.customer_id,
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        })
        
        # Wenn kein embedding, wird es von Chroma berechnet
        self.chroma._get_collection(self._patterns_collection).add(
            ids=[pattern_id],
            documents=[pattern],
            metadatas=[doc_metadata],
            embeddings=[embedding] if embedding else None
        )
        
        return pattern_id
    
    def find_similar_patterns(
        self, 
        query: str, 
        limit: int = 5,
        filter_metadata: Dict = None
    ) -> List[Dict]:
        """Findet ähnliche Code-Patterns.
        
        Args:
            query: Suchquery (z.B. "How to decorate a service?")
            limit: Anzahl der Ergebnisse
            filter_metadata: Optional metadata filter
            
        Returns:
            List von Patterns mit content, metadata, distance
        """
        try:
            collection = self.chroma._get_collection(self._patterns_collection)
            
            results = collection.query(
                query_texts=[query],
                n_results=limit,
                where=filter_metadata,
                include=["documents", "metadatas", "distances"]
            )
            
            patterns = []
            if results["ids"] and results["ids"][0]:
                for i, pattern_id in enumerate(results["ids"][0]):
                    patterns.append({
                        "id": pattern_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i]
                    })
            
            return patterns
        except Exception:
            # Collection existiert noch nicht
            return []
    
    # === Solutions ===
    
    def store_solution(
        self, 
        problem: str, 
        solution: str, 
        ticket_id: str,
        metadata: Dict = None
    ) -> str:
        """Speichert eine Problemlösung.
        
        Args:
            problem: Problembeschreibung
            solution: Die Lösung
            ticket_id: Referenz-Ticket
            metadata: Zusätzliche Metadaten
            
        Returns:
            Solution ID
        """
        # Kombiniere Problem + Lösung für Embedding
        content = f"## Problem\n{problem}\n\n## Solution\n{solution}"
        solution_id = self._generate_id(content, f"solution:{ticket_id}")
        
        doc_metadata = _sanitize_metadata({
            "type": "solution",
            "customer": self.customer_id,
            "ticket_id": ticket_id,
            "problem_summary": problem[:200],
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        })
        
        self.chroma._get_collection(self._solutions_collection).add(
            ids=[solution_id],
            documents=[content],
            metadatas=[doc_metadata]
        )
        
        return solution_id
    
    def find_solutions(
        self, 
        problem_query: str, 
        limit: int = 5
    ) -> List[Dict]:
        """Findet ähnliche Lösungen für ein Problem.
        
        Args:
            problem_query: Problembeschreibung
            limit: Anzahl der Ergebnisse
            
        Returns:
            List von Solutions mit content, metadata, distance
        """
        try:
            collection = self.chroma._get_collection(self._solutions_collection)
            
            results = collection.query(
                query_texts=[problem_query],
                n_results=limit,
                include=["documents", "metadatas", "distances"]
            )
            
            solutions = []
            if results["ids"] and results["ids"][0]:
                for i, solution_id in enumerate(results["ids"][0]):
                    solutions.append({
                        "id": solution_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i]
                    })
            
            return solutions
        except Exception:
            return []
    
    # === Generic Memory Operations ===
    
    def add_memory(
        self,
        content: str,
        memory_type: str = "generic",
        metadata: Dict = None
    ) -> str:
        """Generic memory storage.
        
        Args:
            content: Memory content
            memory_type: Type of memory
            metadata: Additional metadata
            
        Returns:
            Memory ID
        """
        collection_name = f"{self.customer_id}_{memory_type}"
        memory_id = self._generate_id(content, memory_type)
        
        doc_metadata = _sanitize_metadata({
            "type": memory_type,
            "customer": self.customer_id,
            "created_at": datetime.utcnow().isoformat(),
            **(metadata or {})
        })
        
        self.chroma._get_collection(collection_name).add(
            ids=[memory_id],
            documents=[content],
            metadatas=[doc_metadata]
        )
        
        return memory_id
    
    def search(
        self,
        query: str,
        memory_type: str = None,
        limit: int = 5
    ) -> List[Dict]:
        """Generic search across memories.
        
        Args:
            query: Search query
            memory_type: Optional filter by type
            limit: Number of results
            
        Returns:
            List of memories
        """
        try:
            if memory_type:
                collection_name = f"{self.customer_id}_{memory_type}"
                collection = self.chroma._get_collection(collection_name)
                
                results = collection.query(
                    query_texts=[query],
                    n_results=limit,
                    include=["documents", "metadatas", "distances"]
                )
            else:
                # Suche in allen customer collections
                # TODO: Implement multi-collection search
                return []
            
            memories = []
            if results["ids"] and results["ids"][0]:
                for i, memory_id in enumerate(results["ids"][0]):
                    memories.append({
                        "id": memory_id,
                        "content": results["documents"][0][i],
                        "metadata": results["metadatas"][0][i],
                        "distance": results["distances"][0][i]
                    })
            
            return memories
        except Exception:
            return []
    
    # === Stats ===
    
    def get_stats(self) -> Dict[str, Any]:
        """Gibt Statistiken über das Langzeitgedächtnis zurück."""
        stats = {
            "customer_id": self.customer_id,
            "collections": []
        }
        
        # Liste der customer-spezifischen collections
        prefix = f"{self.customer_id}_"
        try:
            collections = self.chroma.client.list_collections()
            for coll in collections:
                if coll.name.startswith(prefix):
                    count = coll.count()
                    stats["collections"].append({
                        "name": coll.name,
                        "count": count
                    })
        except Exception:
            pass
        
        return stats
    
    def __repr__(self) -> str:
        return f"ChromaLongTermMemory(customer={self.customer_id})"
