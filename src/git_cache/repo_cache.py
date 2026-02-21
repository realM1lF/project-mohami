"""Redis-based cache for Git repository state."""

import json
import hashlib
from typing import Dict, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass, asdict

import redis.asyncio as redis


@dataclass
class RepoSnapshot:
    """Snapshot of a repository state."""
    repository: str
    default_branch: str
    branches: List[str]
    files: Dict[str, str]  # path -> content_hash (or first 500 chars for small files)
    readme_content: Optional[str]
    has_commits: bool
    is_empty: bool
    timestamp: str
    commit_count: int = 0


class GitRepoCache:
    """Redis-based cache for Git repository information.
    
    Caches:
    - Repository structure (branches, files)
    - README content
    - Commit history summary
    
    TTL: 1 hour (configurable)
    """
    
    def __init__(
        self,
        redis_url: str = "redis://redis:6379",
        ttl_seconds: int = 3600  # 1 hour
    ):
        self.redis_url = redis_url
        self.ttl = ttl_seconds
        self._redis: Optional[redis.Redis] = None
    
    async def _get_redis(self) -> redis.Redis:
        """Get or create Redis connection."""
        if self._redis is None:
            self._redis = await redis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True
            )
        return self._redis
    
    def _make_key(self, repository: str, key_type: str) -> str:
        """Generate Redis key."""
        # Hash repository name for clean key
        repo_hash = hashlib.md5(repository.encode()).hexdigest()[:12]
        return f"git:{repo_hash}:{key_type}"
    
    async def get_snapshot(self, repository: str) -> Optional[RepoSnapshot]:
        """Get cached repository snapshot.
        
        Args:
            repository: Full repo name (e.g., "owner/repo")
            
        Returns:
            RepoSnapshot if cached and not expired, None otherwise
        """
        try:
            r = await self._get_redis()
            key = self._make_key(repository, "snapshot")
            
            data = await r.get(key)
            if data:
                snapshot_dict = json.loads(data)
                return RepoSnapshot(**snapshot_dict)
            return None
        except Exception as e:
            print(f"Redis get error: {e}")
            return None
    
    async def set_snapshot(self, snapshot: RepoSnapshot):
        """Cache repository snapshot.
        
        Args:
            snapshot: Repository snapshot to cache
        """
        try:
            r = await self._get_redis()
            key = self._make_key(snapshot.repository, "snapshot")
            
            data = json.dumps(asdict(snapshot))
            await r.setex(key, self.ttl, data)
        except Exception as e:
            print(f"Redis set error: {e}")
    
    async def get_file_content(self, repository: str, file_path: str) -> Optional[str]:
        """Get cached file content.
        
        Args:
            repository: Repository name
            file_path: File path within repo
            
        Returns:
            File content if cached, None otherwise
        """
        try:
            r = await self._get_redis()
            key = self._make_key(repository, f"file:{file_path}")
            
            return await r.get(key)
        except Exception as e:
            print(f"Redis get file error: {e}")
            return None
    
    async def set_file_content(
        self,
        repository: str,
        file_path: str,
        content: str,
        max_size: int = 50000  # Max 50KB per file
    ):
        """Cache file content.
        
        Args:
            repository: Repository name
            file_path: File path
            content: File content
            max_size: Maximum content size to cache
        """
        try:
            if len(content) > max_size:
                # Only cache first part of large files
                content = content[:max_size] + "\n\n[...truncated]"
            
            r = await self._get_redis()
            key = self._make_key(repository, f"file:{file_path}")
            
            await r.setex(key, self.ttl, content)
        except Exception as e:
            print(f"Redis set file error: {e}")
    
    async def invalidate(self, repository: str):
        """Invalidate all cached data for a repository.
        
        Call this when you know the repo has changed.
        """
        try:
            r = await self._get_redis()
            pattern = self._make_key(repository, "*")
            
            # Find and delete all keys matching pattern
            cursor = 0
            while True:
                cursor, keys = await r.scan(cursor, match=pattern, count=100)
                if keys:
                    await r.delete(*keys)
                if cursor == 0:
                    break
        except Exception as e:
            print(f"Redis invalidate error: {e}")
    
    async def is_cached(self, repository: str) -> bool:
        """Check if repository has cached snapshot."""
        snapshot = await self.get_snapshot(repository)
        return snapshot is not None
    
    async def get_cache_age(self, repository: str) -> Optional[float]:
        """Get age of cached data in seconds.
        
        Returns:
            Age in seconds, or None if not cached
        """
        try:
            r = await self._get_redis()
            key = self._make_key(repository, "snapshot")
            
            ttl = await r.ttl(key)
            if ttl > 0:
                # Calculate age from TTL
                return self.ttl - ttl
            return None
        except Exception:
            return None
    
    async def refresh_if_needed(
        self,
        repository: str,
        git_provider,
        max_age_seconds: int = 300  # Refresh if older than 5 minutes
    ) -> RepoSnapshot:
        """Get snapshot from cache or refresh from GitHub.
        
        This is the main method to use. It:
        1. Checks cache first
        2. If stale or missing, fetches from GitHub
        3. Updates cache
        
        Args:
            repository: Repository name
            git_provider: GitProvider instance
            max_age_seconds: Max age before refresh
            
        Returns:
            RepoSnapshot (cached or fresh)
        """
        # Try cache first
        cached = await self.get_snapshot(repository)
        
        if cached:
            age = await self.get_cache_age(repository)
            if age and age < max_age_seconds:
                print(f"Using cached snapshot for {repository} (age: {age:.0f}s)")
                return cached
        
        # Fetch fresh data
        print(f"Fetching fresh data for {repository}")
        snapshot = await self._fetch_snapshot(repository, git_provider)
        
        # Cache it
        await self.set_snapshot(snapshot)
        
        return snapshot
    
    async def _fetch_snapshot(
        self,
        repository: str,
        git_provider
    ) -> RepoSnapshot:
        """Fetch repository snapshot from Git provider."""
        try:
            # Get repo info
            repo_info = await git_provider.get_repository_info(repository)
            default_branch = repo_info.default_branch
            
            # Get branches
            try:
                branches = await git_provider.list_branches(repository)
            except:
                branches = []
            
            # Check if empty
            is_empty = len(branches) == 0
            has_commits = not is_empty
            
            # Get README
            readme_content = None
            try:
                readme_content = await git_provider.get_file_content(
                    repository, "README.md", default_branch
                )
            except:
                pass
            
            # Build file list (just top-level for now)
            files = {}
            if has_commits:
                # Cache README separately
                if readme_content:
                    await self.set_file_content(repository, "README.md", readme_content)
                    files["README.md"] = readme_content[:500]
            
            return RepoSnapshot(
                repository=repository,
                default_branch=default_branch,
                branches=branches,
                files=files,
                readme_content=readme_content[:2000] if readme_content else None,
                has_commits=has_commits,
                is_empty=is_empty,
                timestamp=datetime.utcnow().isoformat()
            )
            
        except Exception as e:
            print(f"Error fetching snapshot: {e}")
            # Return minimal snapshot on error
            return RepoSnapshot(
                repository=repository,
                default_branch="main",
                branches=[],
                files={},
                readme_content=None,
                has_commits=False,
                is_empty=True,
                timestamp=datetime.utcnow().isoformat()
            )
    
    async def close(self):
        """Close Redis connection."""
        if self._redis:
            await self._redis.close()
            self._redis = None
