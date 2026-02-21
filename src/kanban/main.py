"""
FastAPI application for Kanban Board Backend
"""
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Optional, List

import yaml
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Ticket, Comment
from .schemas import (
    TicketCreate, TicketUpdate, TicketResponse, TicketDetailResponse,
    CommentCreate, CommentResponse, TicketFilter, AgentQueueResponse,
    TicketStatus, TicketPriority, WebhookTicketCreated
)
from .crud import (
    create_ticket, get_ticket, get_ticket_with_comments, get_tickets,
    update_ticket, assign_ticket, delete_ticket, get_agent_queue,
    create_comment, get_comments, get_ticket_stats
)

# Database setup
DATABASE_URL = "sqlite:///./kanban.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create tables
Base.metadata.create_all(bind=engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# Lifespan context manager
@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Kanban Board Backend starting up...")
    yield
    # Shutdown
    print("🛑 Kanban Board Backend shutting down...")


# FastAPI app
app = FastAPI(
    title="Kanban Board API",
    description="Simple Kanban Board backend for KI-Agent MVP",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Health check
@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy", "service": "kanban-board"}


# Ticket endpoints
@app.post("/tickets", response_model=TicketResponse, status_code=status.HTTP_201_CREATED, tags=["Tickets"])
def create_new_ticket(ticket: TicketCreate, db: Session = Depends(get_db)):
    """Create a new ticket"""
    db_ticket = create_ticket(db, ticket)
    # Add comments count
    return {
        **db_ticket.__dict__,
        "comments_count": 0
    }


@app.get("/tickets", response_model=List[TicketResponse], tags=["Tickets"])
def list_tickets(
    status: Optional[TicketStatus] = None,
    agent: Optional[str] = None,
    customer: Optional[str] = None,
    repository: Optional[str] = None,
    priority: Optional[TicketPriority] = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """List tickets with optional filters"""
    tickets = get_tickets(
        db,
        status=status,
        agent=agent,
        customer=customer,
        repository=repository,
        priority=priority.value if priority else None,
        skip=skip,
        limit=limit
    )
    
    # Add comments count for each ticket
    result = []
    for ticket in tickets:
        ticket_dict = {
            **ticket.__dict__,
            "comments_count": len(ticket.comments)
        }
        result.append(ticket_dict)
    
    return result


@app.get("/tickets/{ticket_id}", response_model=TicketDetailResponse, tags=["Tickets"])
def get_single_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Get a single ticket with comments"""
    ticket = get_ticket_with_comments(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    # Convert comments to list of dicts
    comments_list = [{
        "id": c.id,
        "ticket_id": c.ticket_id,
        "author": c.author,
        "content": c.content,
        "created_at": c.created_at
    } for c in ticket.comments]
    
    return {
        **ticket.__dict__,
        "comments": comments_list,
        "comments_count": len(ticket.comments)
    }


@app.patch("/tickets/{ticket_id}", response_model=TicketResponse, tags=["Tickets"])
def update_existing_ticket(
    ticket_id: str,
    ticket_update: TicketUpdate,
    db: Session = Depends(get_db)
):
    """Update a ticket (status, assignment, etc.)"""
    db_ticket = update_ticket(db, ticket_id, ticket_update)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {
        **db_ticket.__dict__,
        "comments_count": len(db_ticket.comments)
    }


@app.post("/tickets/{ticket_id}/assign", response_model=TicketResponse, tags=["Tickets"])
def assign_ticket_to_agent(
    ticket_id: str,
    agent: Optional[str] = None,
    db: Session = Depends(get_db)
):
    """Assign a ticket to an agent (or unassign if agent is null)"""
    db_ticket = assign_ticket(db, ticket_id, agent)
    if not db_ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return {
        **db_ticket.__dict__,
        "comments_count": len(db_ticket.comments)
    }


@app.delete("/tickets/{ticket_id}", status_code=status.HTTP_204_NO_CONTENT, tags=["Tickets"])
def delete_existing_ticket(ticket_id: str, db: Session = Depends(get_db)):
    """Delete a ticket"""
    success = delete_ticket(db, ticket_id)
    if not success:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return None


# Comment endpoints
@app.post("/tickets/{ticket_id}/comments", response_model=CommentResponse, status_code=status.HTTP_201_CREATED, tags=["Comments"])
def add_comment(ticket_id: str, comment: CommentCreate, db: Session = Depends(get_db)):
    """Add a comment to a ticket"""
    db_comment = create_comment(db, ticket_id, comment)
    if not db_comment:
        raise HTTPException(status_code=404, detail="Ticket not found")
    return db_comment


@app.get("/tickets/{ticket_id}/comments", response_model=List[CommentResponse], tags=["Comments"])
def list_comments(
    ticket_id: str,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=1000),
    db: Session = Depends(get_db)
):
    """Get all comments for a ticket"""
    # Check if ticket exists
    ticket = get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    return get_comments(db, ticket_id, skip=skip, limit=limit)


# Agent Queue endpoint
@app.get("/queue/{agent_id}", response_model=AgentQueueResponse, tags=["Agent Queue"])
def get_agent_queue_endpoint(agent_id: str, db: Session = Depends(get_db)):
    """Get all open tickets assigned to an agent"""
    tickets = get_agent_queue(db, agent_id)
    
    ticket_responses = []
    for ticket in tickets:
        ticket_dict = {
            **ticket.__dict__,
            "comments_count": len(ticket.comments)
        }
        ticket_responses.append(ticket_dict)
    
    return {
        "agent_id": agent_id,
        "tickets": ticket_responses,
        "count": len(ticket_responses)
    }


# Stats endpoint
@app.get("/stats", tags=["Stats"])
def get_stats(db: Session = Depends(get_db)):
    """Get ticket statistics"""
    return get_ticket_stats(db)


# Webhook endpoint (for external integrations)
@app.post("/webhooks/ticket-created", status_code=status.HTTP_200_OK, tags=["Webhooks"])
def webhook_ticket_created(data: WebhookTicketCreated, db: Session = Depends(get_db)):
    """Webhook endpoint called when a ticket is created externally"""
    # This can be used to trigger notifications or sync with external systems
    return {
        "received": True,
        "ticket_id": data.id,
        "action": "ticket_created_notification"
    }


# ============================================================================
# Config endpoints (customers, agents)
# ============================================================================

CONFIG_DIR = Path(__file__).parent.parent.parent / "config"
AGENTS_DIR = Path(__file__).parent.parent.parent / "agents"


def _load_customers_yaml() -> dict:
    """Load and parse customers.yaml with legacy compatibility."""
    yaml_path = CONFIG_DIR / "customers.yaml"
    if not yaml_path.exists():
        return {}
    with open(yaml_path, "r") as f:
        data = yaml.safe_load(f) or {}
    return data.get("customers", {})


def _normalize_customer(cid: str, raw: dict) -> dict:
    """Normalize a customer entry to a stable API response format."""
    repos = []
    if "repositories" in raw:
        for r in raw["repositories"]:
            repos.append({
                "repo": r.get("repo", ""),
                "default_branch": r.get("default_branch", "main"),
            })
    elif "repo_url" in raw:
        url = raw["repo_url"]
        repo_slug = "/".join(url.rstrip("/").split("/")[-2:]) if "/" in url else url
        repos.append({
            "repo": repo_slug,
            "default_branch": raw.get("default_branch", "main"),
        })
    return {
        "id": cid,
        "name": raw.get("name", cid),
        "repositories": repos,
    }


@app.get("/config/customers", tags=["Config"])
def get_customers():
    """List all configured customers with their repositories."""
    raw_customers = _load_customers_yaml()
    return [
        _normalize_customer(cid, data)
        for cid, data in raw_customers.items()
    ]


@app.get("/config/agents", tags=["Config"])
def get_agents():
    """List all available KI agents."""
    agents = []
    if AGENTS_DIR.exists():
        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if not agent_dir.is_dir() or agent_dir.name.startswith("."):
                continue
            soul_path = agent_dir / "soul.md"
            if not soul_path.exists():
                continue
            description = ""
            first_lines = soul_path.read_text(encoding="utf-8").strip().split("\n")
            for line in first_lines:
                stripped = line.strip().lstrip("#").strip()
                if stripped:
                    description = stripped
                    break
            agents.append({
                "id": agent_dir.name,
                "name": agent_dir.name.capitalize(),
                "description": description,
            })
    if not agents:
        agents.append({"id": "mohami", "name": "Mohami", "description": "KI-Entwickler"})
    return agents


# Run with: uvicorn src.kanban.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
