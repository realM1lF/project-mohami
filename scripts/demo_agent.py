#!/usr/bin/env python3
"""Demo script to test the Developer Agent with a sample ticket."""

import os
from pathlib import Path
from dotenv import load_dotenv

# Load env FIRST before any other imports
load_dotenv(Path(__file__).parent / ".env", override=True)

import asyncio
import uuid

# Database setup (same as main.py)
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from src.kanban.models import Base, TicketStatus

DATABASE_URL = "sqlite:///./kanban.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Create tables
Base.metadata.create_all(bind=engine)

from src.git_provider import GitHubProvider
from src.llm import KimiClient
from src.agents import DeveloperAgent
from src.kanban.crud_async import TicketCRUD, CommentCRUD
from src.kanban.schemas import TicketCreate, TicketUpdate


async def main():
    """Run agent demo."""
    
    print("=" * 60)
    print("🤖 KI-Mitarbeiter Developer Agent Demo")
    print("=" * 60)
    
    # Create DB session
    print("\n📦 Initializing database...")
    db = SessionLocal()
    
    # Create CRUD instances
    ticket_crud = TicketCRUD(db)
    comment_crud = CommentCRUD(db)
    
    # Init providers
    print("🔌 Connecting to GitHub...")
    import os
    
    github_token = os.getenv("GITHUB_TOKEN")
    test_repo = os.getenv("TEST_REPO")
    
    if not github_token or not test_repo:
        print("❌ Missing GITHUB_TOKEN or TEST_REPO in .env")
        return
    
    git_provider = GitHubProvider(github_token)
    
    # Check API keys
    router_key = os.getenv("OPEN_ROUTER_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    kimi_key = os.getenv("KIMI_API_KEY")
    
    print(f"\n🔑 API Key check:")
    print(f"   OPEN_ROUTER_API_KEY: {'✓' if router_key else '✗'}")
    print(f"   KIMI_API_KEY: {'✓' if kimi_key else '✗'}")
    
    if router_key:
        print("🧠 OpenRouter (Kimi 2.5) connected")
        llm_client = KimiClient()  # Uses env var
        use_llm = True
    elif kimi_key:
        print("🧠 Moonshot Kimi connected")
        llm_client = KimiClient()  # Uses env var
        use_llm = True
    else:
        print("\n⚠️  No API key found in .env")
        print("Demo will run WITHOUT LLM (using mock responses)")
        use_llm = False
    
    # Create a test ticket
    print("\n📝 Creating test ticket...")
    ticket_id = str(uuid.uuid4())[:8]
    
    ticket_data = TicketCreate(
        id=ticket_id,
        title="Add error handling to main function",
        description="""The main function in calculator.py currently doesn't handle division by zero.

Requirements:
- Catch ZeroDivisionError
- Return a user-friendly error message
- Add a test case for this scenario

File: src/calculator.py
Function: calculate()""",
        customer="test-customer",
        repository=test_repo,
        priority="high"
    )
    
    ticket = await ticket_crud.create(ticket_data, ticket_id)
    print(f"✅ Ticket created: {ticket.id}")
    print(f"   Title: {ticket.title}")
    print(f"   Status: {ticket.status}")
    
    # Create agent
    if use_llm:
        agent = DeveloperAgent(
            agent_id="dev-agent-1",
            git_provider=git_provider,
            llm_client=llm_client,
            ticket_crud=ticket_crud,
            comment_crud=comment_crud
        )
    else:
        # Mock run without LLM
        print("\n🎭 Running with MOCK LLM")
        print("=" * 60)
        
        print("\n1️⃣  OBSERVE Phase")
        print("   - Reading ticket...")
        print("   - Fetching repository info...")
        print("   - Checking for README...")
        
        # Update status manually for demo
        await ticket_crud.update(ticket_id, TicketUpdate(status="in_progress", agent="dev-agent-1"))
        
        print("\n2️⃣  REASON Phase")
        print("   - Analyzing requirements...")
        
        print("\n3️⃣  PLAN Phase")
        print("   - Determining approach...")
        
        print("\n4️⃣  ACT Phase")
        
        # Add mock comment
        from src.kanban.schemas import CommentCreate
        await comment_crud.create(ticket_id, CommentCreate(
            author="dev-agent-1",
            content="""🔍 **Observation Phase**

- Ticket: Add error handling to main function
- Customer: test-customer
- Repository: realM1lF/personal-ki-agents
- Files analyzed: README.md"""
        ))
        
        await comment_crud.create(ticket_id, CommentCreate(
            author="dev-agent-1",
            content="""🧠 **Reasoning Phase**

Based on my analysis:

1. **Core Problem**: The calculator.py file lacks error handling for division by zero operations
2. **Missing Information**: 
   - Should I raise a custom exception or return a specific value?
   - What exact error message format is preferred?
   - Should logging be included?
3. **Approach**: Wrap division in try-except, return user-friendly message

Recommendation: Ask clarifying questions before implementation."""
        ))
        
        await comment_crud.create(ticket_id, CommentCreate(
            author="dev-agent-1",
            content="""📋 **Planning Phase**

**Option A: Ask Clarifying Questions**

I need more information before proceeding:

1. Should the function return None, 0, or raise a custom exception when division by zero occurs?
2. What should the exact error message be? (e.g., "Cannot divide by zero" or more detailed?)
3. Should I add logging for this error case?"""
        ))
        
        await comment_crud.create(ticket_id, CommentCreate(
            author="dev-agent-1",
            content="""❓ **Clarification Needed**

I need more information before proceeding:

1. Should the function return None, 0, or raise a custom exception when division by zero occurs?
2. What should the exact error message be? (e.g., "Cannot divide by zero" or more detailed?)
3. Should I add logging for this error case?

Please reply with answers so I can continue."""
        ))
        
        await ticket_crud.update(ticket_id, TicketUpdate(status="clarification"))
        
        print("   - Asking clarifying questions...")
        print("   - Status changed to: clarification")
        
        db.close()
        
        print("\n" + "=" * 60)
        print("📊 Results")
        print("=" * 60 + "\n")
        
        print(f"Ticket Status: clarification")
        print(f"Assigned Agent: dev-agent-1")
        print(f"\n💬 Comments added: 4")
        print("\n   1. dev-agent-1: 🔍 **Observation Phase**")
        print("   2. dev-agent-1: 🧠 **Reasoning Phase**")
        print("   3. dev-agent-1: 📋 **Planning Phase**")
        print("   4. dev-agent-1: ❓ **Clarification Needed**")
        
        print("\n" + "=" * 60)
        print("✅ Demo complete (MOCK mode)")
        print("=" * 60)
        print("\n💡 To use real Kimi 2.5 LLM:")
        print("   Add KIMI_API_KEY to .env file")
        return
    
    # Process ticket with real LLM
    print("\n" + "=" * 60)
    print("🚀 Starting ORPA Workflow...")
    print("=" * 60 + "\n")
    
    await agent.process_ticket(ticket_id)
    
    # Show results
    print("\n" + "=" * 60)
    print("📊 Results")
    print("=" * 60 + "\n")
    
    updated_ticket = await ticket_crud.get(ticket_id)
    print(f"Ticket Status: {updated_ticket.status}")
    print(f"Assigned Agent: {updated_ticket.agent}")
    
    from src.kanban.crud import get_comments
    comments = get_comments(db, ticket_id)
    print(f"\n💬 Comments ({len(comments)}):")
    for i, comment in enumerate(comments, 1):
        print(f"\n   {i}. {comment.author}:")
        preview = comment.content[:150].replace('\n', ' ')
        print(f"      {preview}...")
    
    db.close()
    
    print("\n" + "=" * 60)
    print("✅ Demo complete!")
    print("=" * 60)
    
    print(f"\n📝 You can view/add comments via:")
    print(f"   GET  http://localhost:8000/tickets/{ticket_id}")
    print(f"   POST http://localhost:8000/tickets/{ticket_id}/comments")


if __name__ == "__main__":
    asyncio.run(main())
