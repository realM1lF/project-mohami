#!/usr/bin/env python3
"""
Agent Worker - Mohami KI-Mitarbeiter.

Unterstützt zwei Modi:
- INTELLIGENT (neu): Tool-Use Framework + 4-Schichten Memory
- LEGACY (Fallback): Basis DeveloperAgent

Usage:
    python agent_worker.py

Environment variables:
    USE_INTELLIGENT_AGENT - "true" für neuen Agent, "false" für Legacy (default: true)
    OPEN_ROUTER_API_KEY - OpenRouter API key for Kimi
    GITHUB_TOKEN - GitHub token for repo access
    REDIS_URL - Redis connection URL
    CHROMA_PERSIST_DIR - ChromaDB persistence directory
    USE_ENHANCED_AGENT - Legacy: Enable enhanced agent with memory (default: false)
"""

import asyncio
import os
import sys
from pathlib import Path
from datetime import datetime
from typing import Optional, Any

from dotenv import load_dotenv

# Load environment variables
load_dotenv(Path(__file__).parent / ".env", override=True)

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.kanban.models import Base
from src.kanban.crud_async import TicketCRUD, CommentCRUD
from src.kanban.schemas import TicketUpdate
from src.git_provider import GitHubProvider
from src.llm import KimiClient

# ============================================================================
# CONFIG SWITCH: Intelligent Agent vs Legacy
# ============================================================================
USE_INTELLIGENT_AGENT = os.getenv("USE_INTELLIGENT_AGENT", "true").lower() == "true"

# Track import errors for logging
INTELLIGENT_ERROR: Optional[str] = None
ENHANCED_ERROR: Optional[str] = None

# Agent class placeholder - will be set based on config
AgentClass: Optional[Any] = None
agent_mode: str = "unknown"

# ============================================================================
# AGENT IMPORT LOGIC with Graceful Fallback
# ============================================================================

if USE_INTELLIGENT_AGENT:
    try:
        # Try to import IntelligentAgent (new Tool-Use + Memory Agent)
        from src.agents.intelligent_agent import IntelligentAgent
        AgentClass = IntelligentAgent
        agent_mode = "INTELLIGENT"
        print("🧠 IntelligentAgent loaded - Tool-Use + 4-Layer Memory enabled")
    except ImportError as e:
        INTELLIGENT_ERROR = str(e)[:100]
        print(f"⚠️  IntelligentAgent not available: {INTELLIGENT_ERROR}")
        print("   Falling back to legacy agents...")
        USE_INTELLIGENT_AGENT = False

# Fallback chain if IntelligentAgent not available
if not USE_INTELLIGENT_AGENT:
    # Try Enhanced Developer Agent (Tool-Use without full memory)
    USE_ENHANCED = os.getenv("USE_ENHANCED_AGENT", "false").lower() == "true"
    
    if USE_ENHANCED:
        try:
            from src.agents.enhanced_developer_agent import ToolUseDeveloperAgent
            AgentClass = ToolUseDeveloperAgent
            agent_mode = "TOOL-USE"
            print("🔧 ToolUseDeveloperAgent loaded - Tool-Use Framework enabled")
        except ImportError as e:
            ENHANCED_ERROR = str(e)[:100]
            print(f"⚠️  ToolUseDeveloperAgent unavailable: {ENHANCED_ERROR}")
            USE_ENHANCED = False
    
    # Final fallback: Basic DeveloperAgent
    if not USE_ENHANCED:
        from src.agents import DeveloperAgent
        AgentClass = DeveloperAgent
        agent_mode = "LEGACY"
        print("📦 DeveloperAgent loaded - Basic mode (limited features)")

# Database setup
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./kanban.db")
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)


class AgentWorker:
    """Worker that continuously processes tickets with configurable agent."""
    
    def __init__(self):
        self.db = SessionLocal()
        self.ticket_crud = TicketCRUD(self.db)
        self.comment_crud = CommentCRUD(self.db)
        
        # Initialize providers
        github_token = os.getenv("GITHUB_TOKEN")
        if not github_token:
            raise ValueError("GITHUB_TOKEN not set in environment")
        
        self.git_provider = GitHubProvider(github_token)
        
        # Check for API key
        router_key = os.getenv("OPEN_ROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
        kimi_key = os.getenv("KIMI_API_KEY")
        
        if not (router_key or kimi_key):
            raise ValueError("No API key found. Set OPEN_ROUTER_API_KEY or KIMI_API_KEY")
        
        self.llm_client = KimiClient()
        
        # Initialize agent based on selected mode
        self.agent = self._create_agent()
        self.running = False
    
    def _create_agent(self):
        """Create the appropriate agent based on mode."""
        if agent_mode == "INTELLIGENT":
            return self._create_intelligent_agent()
        elif agent_mode == "TOOL-USE":
            return self._create_tool_use_agent()
        else:
            return self._create_legacy_agent()
    
    def _create_intelligent_agent(self):
        """Create the new IntelligentAgent with full capabilities."""
        from src.agents.intelligent_agent import IntelligentAgent
        
        # IntelligentAgent has integrated memory and tool management
        return IntelligentAgent(
            agent_id="mohami",
            git_provider=self.git_provider,
            llm_client=self.llm_client,
            ticket_crud=self.ticket_crud,
            comment_crud=self.comment_crud,
        )
    
    def _create_tool_use_agent(self):
        """Create ToolUseDeveloperAgent (fallback level 1)."""
        from src.agents.enhanced_developer_agent import ToolUseDeveloperAgent
        
        return ToolUseDeveloperAgent(
            agent_id="mohami",
            git_provider=self.git_provider,
            llm_client=self.llm_client,
            ticket_crud=self.ticket_crud,
            comment_crud=self.comment_crud,
        )
    
    def _create_legacy_agent(self):
        """Create basic DeveloperAgent (fallback level 2)."""
        from src.agents import DeveloperAgent
        
        return DeveloperAgent(
            agent_id="mohami",
            git_provider=self.git_provider,
            llm_client=self.llm_client,
            ticket_crud=self.ticket_crud,
            comment_crud=self.comment_crud,
        )
    
    async def run(self):
        """Main worker loop."""
        self.running = True
        
        print("=" * 60)
        print("🤖 Mohami Agent Worker")
        print("=" * 60)
        print(f"\n⏰ Started at: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("📡 Polling for tickets every 5 seconds...")
        
        # Show which mode is active
        print("\n🎛️  Agent Mode:")
        if agent_mode == "INTELLIGENT":
            print("   🧠 INTELLIGENT (Tool-Use + 4-Layer Memory)")
            print("   ✓ Tool Registry with 8+ Tools")
            print("   ✓ Short, Session, Long & Episodic Memory")
            print("   ✓ Workspace Management (DDEV)")
        elif agent_mode == "TOOL-USE":
            print("   🔧 TOOL-USE (Tool Framework)")
            print("   ✓ Dynamic Tool Selection")
            print("   ✓ Tool Execution Loop")
            print("   ⚠ Limited Memory Features")
        else:
            print("   📦 LEGACY (Basic)")
            print("   ✓ Core ORPA Workflow")
            print("   ⚠ No Tool-Use")
            print("   ⚠ No Advanced Memory")
        
        # Show fallback info if applicable
        if INTELLIGENT_ERROR:
            print(f"\n⚠️  Fallback reason: IntelligentAgent import failed")
            print(f"   Error: {INTELLIGENT_ERROR}")
        if ENHANCED_ERROR:
            print(f"\n⚠️  Fallback reason: EnhancedAgent import failed")
            print(f"   Error: {ENHANCED_ERROR}")
        
        print("\n🛑 Press Ctrl+C to stop\n")
        
        try:
            while self.running:
                await self._process_cycle()
                await asyncio.sleep(5)  # Poll every 5 seconds
        except KeyboardInterrupt:
            print("\n\n👋 Shutting down...")
        finally:
            self.db.close()
    
    async def _process_cycle(self):
        """Process one cycle of tickets."""
        try:
            # 1. Check for new tickets in backlog
            new_tickets = await self.ticket_crud.list(
                status="backlog",
                agent=None
            )
            
            for ticket in new_tickets:
                print(f"\n📨 New ticket: {ticket.id[:8]} - {ticket.title}")
                print(f"   Customer: {ticket.customer}")
                print(f"   Repository: {ticket.repository}")
                print(f"   Agent: {agent_mode} mode")
                print("   → Starting ORPA workflow...")
                
                await self.agent.process_ticket(ticket.id)
                
                print("   ✅ Complete")
            
            # 2. Check for clarification tickets with new responses
            clarification_tickets = await self.ticket_crud.list(
                status="clarification"
            )
            
            for ticket in clarification_tickets:
                if ticket.agent == "mohami":
                    # Check if there are new comments from user
                    comments = await self.comment_crud.get_by_ticket(ticket.id)
                    
                    # Get last (most recent) comment
                    if comments and len(comments) > 0:
                        last_comment = comments[0]
                        
                        # If last comment is from user (not agent), continue
                        if not last_comment.author.startswith("mohami"):
                            print(f"\n💬 Clarification answered: {ticket.id[:8]}")
                            print(f"   User: {last_comment.author}")
                            print("   → Continuing workflow...")
                            
                            await self.agent.process_ticket(ticket.id)
                            
                            print("   ✅ Complete")
            
            # 3. Check for in_progress tickets with new user feedback
            in_progress_tickets = await self.ticket_crud.list(
                status="in_progress"
            )
            
            for ticket in in_progress_tickets:
                if ticket.agent == "mohami":
                    comments = await self.comment_crud.get_by_ticket(ticket.id)
                    
                    # Get last (most recent) comment
                    if comments and len(comments) > 0:
                        last_comment = comments[0]
                        
                        # If last comment is from user (not agent), re-process
                        if not last_comment.author.startswith("mohami"):
                            print(f"\n🔄 User feedback on in_progress: {ticket.id[:8]}")
                            print(f"   User: {last_comment.author}")
                            print(f"   Feedback: {last_comment.content[:50]}...")
                            print("   → Re-processing...")
                            
                            await self.agent.process_ticket(ticket.id)
                            
                            print("   ✅ Complete")
            
        except Exception as e:
            print(f"\n❌ Error in processing cycle: {e}")
            import traceback
            traceback.print_exc()
    
    async def process_single_ticket(self, ticket_id: str):
        """Process a single ticket immediately."""
        print(f"\n🎯 Processing single ticket: {ticket_id}")
        print(f"   Agent mode: {agent_mode}")
        await self.agent.process_ticket(ticket_id)
        print("✅ Complete")


async def main():
    """Main entry point."""
    worker = AgentWorker()
    await worker.run()


if __name__ == "__main__":
    asyncio.run(main())
