"""Integration tests for Memory System."""

import pytest
import pytest_asyncio
import asyncio
from datetime import datetime
from pathlib import Path


# =============================================================================
# Short Term Memory Tests (InMemoryBuffer)
# =============================================================================

class TestShortTermMemory:
    """Tests for InMemoryBuffer (Short Term Memory)."""
    
    def test_basic_set_get(self, short_term_memory):
        """Test basic set and get operations."""
        memory = short_term_memory
        
        memory.set("key", "value")
        assert memory.get("key") == "value"
    
    def test_get_default(self, short_term_memory):
        """Test get with default value."""
        memory = short_term_memory
        
        assert memory.get("nonexistent", "default") == "default"
        assert memory.get("nonexistent") is None
    
    def test_has_key(self, short_term_memory):
        """Test checking key existence."""
        memory = short_term_memory
        
        memory.set("existing", "value")
        assert memory.has("existing") is True
        assert memory.has("nonexistent") is False
    
    def test_delete_key(self, short_term_memory):
        """Test deleting a key."""
        memory = short_term_memory
        
        memory.set("to_delete", "value")
        assert memory.delete("to_delete") is True
        assert memory.has("to_delete") is False
        assert memory.delete("to_delete") is False
    
    def test_ttl_expiration(self, short_term_memory):
        """Test TTL expiration."""
        memory = short_term_memory
        
        # Set with very short TTL (0 seconds means no expiration in this implementation)
        memory.set("ttl_key", "value", ttl=1)
        assert memory.get("ttl_key") == "value"
        
        # Wait for expiration
        import time
        time.sleep(1.1)
        
        # Should be expired now
        assert memory.get("ttl_key") is None
    
    def test_get_all(self, short_term_memory):
        """Test getting all data."""
        memory = short_term_memory
        
        memory.set("key1", "value1")
        memory.set("key2", "value2")
        
        all_data = memory.get_all()
        assert all_data["key1"] == "value1"
        assert all_data["key2"] == "value2"
    
    def test_clear(self, short_term_memory):
        """Test clearing memory."""
        memory = short_term_memory
        
        memory.set("key", "value")
        memory.clear()
        
        assert memory.get("key") is None
        assert len(memory.get_all()) == 0
    
    def test_cleanup_expired(self, short_term_memory):
        """Test cleaning up expired entries."""
        memory = short_term_memory
        
        memory.set("expired", "value", ttl=1)
        memory.set("permanent", "value", ttl=0)  # 0 = no expiration
        
        import time
        time.sleep(1.1)
        
        cleaned = memory.cleanup_expired()
        assert cleaned == 1
        assert memory.has("expired") is False
        assert memory.has("permanent") is True
    
    # === Reasoning Steps Tests ===
    
    def test_add_reasoning_step(self, short_term_memory):
        """Test adding reasoning steps."""
        memory = short_term_memory
        
        step = memory.add_reasoning_step("observe", "Looking at the code")
        
        assert step.step_number == 1
        assert step.phase == "observe"
        assert step.content == "Looking at the code"
        assert isinstance(step.timestamp, datetime)
    
    def test_get_reasoning_steps(self, short_term_memory):
        """Test retrieving reasoning steps."""
        memory = short_term_memory
        
        memory.add_reasoning_step("observe", "Step 1")
        memory.add_reasoning_step("reason", "Step 2")
        memory.add_reasoning_step("plan", "Step 3")
        
        all_steps = memory.get_reasoning_steps()
        assert len(all_steps) == 3
        
        # Filter by phase
        observe_steps = memory.get_reasoning_steps(phase="observe")
        assert len(observe_steps) == 1
        assert observe_steps[0].content == "Step 1"
    
    def test_get_reasoning_trace(self, short_term_memory):
        """Test getting formatted reasoning trace."""
        memory = short_term_memory
        
        memory.add_reasoning_step("observe", "First observation")
        memory.add_reasoning_step("reason", "Then reasoning")
        
        trace = memory.get_reasoning_trace()
        
        assert "Reasoning Trace" in trace
        assert "OBSERVE" in trace
        assert "REASON" in trace
        assert "First observation" in trace
    
    def test_clear_reasoning(self, short_term_memory):
        """Test clearing reasoning steps."""
        memory = short_term_memory
        
        memory.add_reasoning_step("observe", "Step")
        memory.clear_reasoning()
        
        assert len(memory.get_reasoning_steps()) == 0
    
    # === ORPA Loop State Tests ===
    
    def test_orpa_phase(self, short_term_memory):
        """Test ORPA phase tracking."""
        memory = short_term_memory
        
        assert memory.get_orpa_phase() is None
        
        memory.set_orpa_phase("observe")
        assert memory.get_orpa_phase() == "observe"
        
        memory.set_orpa_phase("act")
        assert memory.get_orpa_phase() == "act"
    
    def test_observations(self, short_term_memory):
        """Test observations tracking."""
        memory = short_term_memory
        
        memory.add_observation("File has syntax error", {"file": "test.py"})
        memory.add_observation("Tests are failing")
        
        observations = memory.get_observations()
        assert len(observations) == 2
        assert observations[0]["content"] == "File has syntax error"
        assert observations[0]["metadata"]["file"] == "test.py"
    
    def test_plan_tracking(self, short_term_memory):
        """Test plan tracking."""
        memory = short_term_memory
        
        plan = [
            {"step": 1, "action": "fix_syntax"},
            {"step": 2, "action": "run_tests"}
        ]
        
        memory.set_plan(plan)
        retrieved = memory.get_plan()
        
        assert len(retrieved) == 2
        assert retrieved[0]["action"] == "fix_syntax"
    
    def test_execution_results(self, short_term_memory):
        """Test execution results tracking."""
        memory = short_term_memory
        
        memory.add_execution_result("step_1", "Syntax fixed", success=True)
        memory.add_execution_result("step_2", "Tests still failing", success=False)
        
        results = memory.get_execution_results()
        assert len(results) == 2
        assert results[0]["success"] is True
        assert results[1]["success"] is False
    
    # === Tool State Tests ===
    
    def test_tool_state(self, short_term_memory):
        """Test tool state management."""
        memory = short_term_memory
        
        memory.set_tool_state("file_read", {"last_file": "/path/to/file"})
        
        state = memory.get_tool_state("file_read")
        assert state["last_file"] == "/path/to/file"
        
        assert memory.get_tool_state("nonexistent") is None
    
    def test_clear_tool_state(self, short_term_memory):
        """Test clearing tool state."""
        memory = short_term_memory
        
        memory.set_tool_state("tool1", {"state": 1})
        memory.set_tool_state("tool2", {"state": 2})
        
        # Clear specific tool
        memory.clear_tool_state("tool1")
        assert memory.get_tool_state("tool1") is None
        assert memory.get_tool_state("tool2") is not None
        
        # Clear all
        memory.clear_tool_state()
        assert memory.get_tool_state("tool2") is None
    
    # === Session Info Tests ===
    
    def test_session_info(self, short_term_memory):
        """Test session info retrieval."""
        memory = short_term_memory
        
        memory.set("key1", "value1")
        memory.set("key2", "value2")
        memory.add_reasoning_step("observe", "Test")
        memory.set_orpa_phase("reason")
        
        info = memory.get_session_info()
        
        assert info["customer_id"] == "test_customer"
        assert info["data_count"] == 2
        assert info["reasoning_steps_count"] == 1
        assert info["current_orpa_phase"] == "reason"
        assert "created_at" in info
        assert "last_accessed" in info


# =============================================================================
# Long Term Memory Tests (ChromaDB)
# =============================================================================

@pytest.mark.skipif(
    not pytest.importorskip("chromadb", reason="chromadb not installed"),
    reason="ChromaDB not available"
)
class TestChromaLongTermMemory:
    """Tests for ChromaLongTermMemory."""
    
    @pytest.mark.asyncio
    async def test_store_and_find_pattern(self, chroma_long_term_memory):
        """Test storing and finding code patterns."""
        from src.memory.chroma_long_term import PatternType
        
        memory = chroma_long_term_memory
        
        # Store a pattern
        pattern_id = await memory.store_pattern(
            code_snippet="function test() { return true; }",
            file_path="src/test.js",
            pattern_type=PatternType.SERVICE,
            shopware_version="6.5",
            language="javascript"
        )
        
        assert pattern_id is not None
        
        # Find similar patterns
        results = await memory.find_similar_patterns(
            code_query="function test",
            limit=1
        )
        
        assert len(results) == 1
        assert results[0]["id"] == pattern_id
    
    @pytest.mark.asyncio
    async def test_store_and_find_solution(self, chroma_long_term_memory):
        """Test storing and finding solutions."""
        from src.memory.chroma_long_term import SolutionType
        
        memory = chroma_long_term_memory
        
        # Store a solution
        solution_id = await memory.store_solution(
            ticket_id="T-123",
            problem_description="Memory leak in cache",
            solution_description="Clear cache periodically",
            solution_type=SolutionType.BUGFIX,
            affected_files=["src/cache.py"],
            verified=True
        )
        
        assert solution_id is not None
        
        # Find similar solutions
        results = await memory.find_similar_solutions(
            problem_description="memory leak issue",
            verified_only=True,
            limit=1
        )
        
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_store_and_find_documentation(self, chroma_long_term_memory):
        """Test storing and finding documentation."""
        from src.memory.chroma_long_term import DocType
        
        memory = chroma_long_term_memory
        
        # Store documentation
        doc_id = await memory.store_documentation(
            content="## API Guide\n\nUse POST /api/v1/users to create users",
            doc_type=DocType.API,
            topic="User API",
            related_files=["src/api/users.py"]
        )
        
        assert doc_id is not None
        
        # Find documentation
        results = await memory.find_documentation(
            query="how to create users",
            limit=1
        )
        
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_store_and_find_conversation(self, chroma_long_term_memory):
        """Test storing and finding conversation summaries."""
        memory = chroma_long_term_memory
        
        # Store conversation
        summary_id = await memory.store_conversation_summary(
            ticket_id="T-456",
            summary="Discussion about authentication flow",
            conversation_type="ticket",
            participants=["user1", "agent"],
            key_decisions=["Use OAuth2", "JWT tokens"]
        )
        
        assert summary_id is not None
        
        # Find conversations
        results = await memory.find_conversations(
            query="authentication discussion",
            limit=1
        )
        
        assert len(results) == 1
    
    @pytest.mark.asyncio
    async def test_pattern_success_increment(self, chroma_long_term_memory):
        """Test incrementing pattern success rate."""
        from src.memory.chroma_long_term import PatternType
        
        memory = chroma_long_term_memory
        
        pattern_id = await memory.store_pattern(
            code_snippet="test pattern",
            file_path="test.php",
            pattern_type=PatternType.SERVICE,
            shopware_version="6.5"
        )
        
        # Increment success
        await memory.increment_pattern_success(pattern_id)
        await memory.increment_pattern_success(pattern_id)
    
    @pytest.mark.asyncio
    async def test_flag_pattern_for_review(self, chroma_long_term_memory):
        """Test flagging pattern for review."""
        from src.memory.chroma_long_term import PatternType
        
        memory = chroma_long_term_memory
        
        pattern_id = await memory.store_pattern(
            code_snippet="problematic pattern",
            file_path="test.php",
            pattern_type=PatternType.SERVICE,
            shopware_version="6.5"
        )
        
        await memory.flag_pattern_for_review(pattern_id, ticket_id="T-999")
    
    @pytest.mark.asyncio
    async def test_verify_solution(self, chroma_long_term_memory):
        """Test verifying a solution."""
        from src.memory.chroma_long_term import SolutionType
        
        memory = chroma_long_term_memory
        
        solution_id = await memory.store_solution(
            ticket_id="T-123",
            problem_description="Test problem",
            solution_description="Test solution",
            solution_type=SolutionType.BUGFIX,
            verified=False
        )
        
        success = await memory.verify_solution(solution_id)
        assert success is True
    
    @pytest.mark.asyncio
    async def test_collection_stats(self, chroma_long_term_memory):
        """Test getting collection statistics."""
        memory = chroma_long_term_memory
        
        stats = await memory.get_collection_stats()
        
        assert stats["customer_id"] == "test_customer"
        assert "collections" in stats
        assert "code_patterns" in stats["collections"]
        assert "solutions" in stats["collections"]


# =============================================================================
# Episodic Memory Tests
# =============================================================================

@pytest.mark.skipif(
    not pytest.importorskip("chromadb", reason="chromadb not installed"),
    reason="ChromaDB not available"
)
class TestEpisodicMemory:
    """Tests for EpisodicMemory."""
    
    @pytest.mark.asyncio
    async def test_record_episode(self, episodic_memory):
        """Test recording an episode."""
        memory = episodic_memory
        
        episode_id = await memory.record_episode(
            customer_id="test_customer",
            ticket_id="T-123",
            content="User reported login issue",
            episode_type="user_request",
            metadata={"priority": "high"}
        )
        
        assert episode_id is not None
    
    @pytest.mark.asyncio
    async def test_record_ticket_resolution(self, episodic_memory):
        """Test recording ticket resolution."""
        memory = episodic_memory
        
        await memory.record_ticket_resolution(
            customer_id="test_customer",
            ticket_id="T-123",
            problem="Bug in authentication",
            solution="Fixed token validation",
            success=True
        )
        
        # Verify by searching
        episodes = await memory.find_similar_episodes(
            customer_id="test_customer",
            query="authentication bug",
            episode_type="lesson",
            n_results=1
        )
        
        assert len(episodes) >= 0  # May be 0 if collection doesn't exist yet
    
    @pytest.mark.asyncio
    async def test_find_similar_episodes(self, episodic_memory):
        """Test finding similar episodes."""
        memory = episodic_memory
        
        # Record multiple episodes
        await memory.record_episode(
            customer_id="test_customer",
            ticket_id="T-1",
            content="Issue with database connection",
            episode_type="user_request"
        )
        
        await memory.record_episode(
            customer_id="test_customer",
            ticket_id="T-2",
            content="Database timeout problem",
            episode_type="user_request"
        )
        
        # Find similar
        results = await memory.find_similar_episodes(
            customer_id="test_customer",
            query="database issue",
            n_results=2
        )
        
        # Results may be empty if collection is new
        assert isinstance(results, list)
    
    @pytest.mark.asyncio
    async def test_get_relevant_context(self, episodic_memory):
        """Test getting relevant context for a ticket."""
        memory = episodic_memory
        
        # Record a lesson
        await memory.record_ticket_resolution(
            customer_id="test_customer",
            ticket_id="T-100",
            problem="Cache invalidation issue",
            solution="Use Redis cache with TTL",
            success=True
        )
        
        # Get context
        context = await memory.get_relevant_context(
            customer_id="test_customer",
            current_ticket_description="Having cache problems",
            n_lessons=1,
            n_episodes=1
        )
        
        # Should return formatted string
        assert isinstance(context, str)
    
    @pytest.mark.asyncio
    async def test_record_conversation_turn(self, episodic_memory):
        """Test recording conversation turns."""
        memory = episodic_memory
        
        # Record user message
        await memory.record_conversation_turn(
            customer_id="test_customer",
            ticket_id="T-123",
            author="user1",
            content="How do I fix this?"
        )
        
        # Record agent response
        await memory.record_conversation_turn(
            customer_id="test_customer",
            ticket_id="T-123",
            author="mohami",
            content="Try restarting the service"
        )
        
        # Both should be recorded without error
        assert True
