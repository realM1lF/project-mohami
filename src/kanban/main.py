"""
FastAPI application for Kanban Board Backend
"""
import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict, Any

import yaml
from fastapi import FastAPI, Depends, HTTPException, Query, status
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from .models import Base, Ticket, Comment, ensure_kanban_schema
from .models import TicketIteration, LearningRecord  # Phase 1: Learning System
from .schemas import (
    TicketCreate, TicketUpdate, TicketResponse, TicketDetailResponse,
    CommentCreate, CommentResponse, TicketFilter, AgentQueueResponse,
    TicketStatus, TicketPriority, WebhookTicketCreated,
    ChatMessageRequest, ChatMessageResponse,
    # Phase 1: Learning System Schemas
    TicketApproval, ChangeRequest, IterationRecord, LearningRecordResponse,
    TicketUpdateEnhanced, TicketResponseEnhanced,
)
from .crud import (
    create_ticket, get_ticket, get_ticket_with_comments, get_tickets,
    update_ticket, assign_ticket, delete_ticket, get_agent_queue,
    create_comment, get_comments, get_ticket_stats
)
from .crud_async import TicketIterationCRUD, LearningRecordCRUD  # Phase 1: Learning System CRUD

# Database setup
DATABASE_URL = "sqlite:///./kanban.db"
engine = create_engine(DATABASE_URL, connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


# Create tables
Base.metadata.create_all(bind=engine)
ensure_kanban_schema(engine)


# Dependency to get DB session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _get_agent_assigned_customers(agent_id: str) -> List[str]:
    """Return assigned customers from agents/{agent_id}/config.yaml (clients: [...])."""
    if not agent_id:
        return []
    agents_dir = Path(__file__).parent.parent.parent / "agents"
    cfg_path = agents_dir / agent_id / "config.yaml"
    if not cfg_path.exists():
        return []
    try:
        cfg_raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
        clients = cfg_raw.get("clients", [])
        if isinstance(clients, list):
            return [str(c).strip() for c in clients if str(c).strip()]
    except Exception:
        pass
    return []


def _agent_can_handle_customer(agent_id: str, customer_id: str) -> bool:
    """Check if an agent is allowed to work for a customer.

    Rule: empty/missing clients list means unrestricted (backward compatible).
    """
    if not agent_id or not customer_id:
        return True
    assigned = _get_agent_assigned_customers(agent_id)
    if not assigned:
        return True
    return customer_id in assigned


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
    # Enforce agent/customer assignment when agent is (re)assigned via PATCH
    if ticket_update.agent:
        existing = get_ticket(db, ticket_id)
        if existing and not _agent_can_handle_customer(ticket_update.agent, existing.customer):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Agent '{ticket_update.agent}' is not assigned to customer "
                    f"'{existing.customer}'"
                ),
            )

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
    if agent:
        existing = get_ticket(db, ticket_id)
        if not existing:
            raise HTTPException(status_code=404, detail="Ticket not found")
        if not _agent_can_handle_customer(agent, existing.customer):
            raise HTTPException(
                status_code=400,
                detail=(
                    f"Agent '{agent}' is not assigned to customer "
                    f"'{existing.customer}'"
                ),
            )

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
# Chat endpoints (freeform chat with KI agents)
# ============================================================================

# In-memory chat history: session_id -> list of {role, content}
_chat_sessions: Dict[str, List[Dict[str, str]]] = {}


def _get_available_agent_ids() -> List[str]:
    """Return list of valid agent IDs from config."""
    agents = []
    if AGENTS_DIR.exists():
        for agent_dir in sorted(AGENTS_DIR.iterdir()):
            if agent_dir.is_dir() and not agent_dir.name.startswith("."):
                if (agent_dir / "soul.md").exists():
                    agents.append(agent_dir.name)
    return agents if agents else ["mohami"]


@app.post("/chat/message", response_model=ChatMessageResponse, tags=["Chat"])
async def chat_message(request: ChatMessageRequest):
    """Send a message to a KI agent and get a reply."""
    agent_id = request.agent_id
    message = request.message.strip()
    session_id = request.session_id
    
    if not agent_id:
        raise HTTPException(status_code=400, detail="agent_id required")
    if not message:
        raise HTTPException(status_code=400, detail="message required")
    
    available = _get_available_agent_ids()
    if agent_id not in available:
        raise HTTPException(status_code=400, detail=f"Unknown agent. Available: {available}")
    
    if not session_id:
        session_id = str(uuid.uuid4())
    
    if session_id not in _chat_sessions:
        _chat_sessions[session_id] = []
    
    history = _chat_sessions[session_id]
    history.append({"role": "user", "content": message})
    
    # Build system prompt from agent config
    try:
        from src.agent_config.config_loader import AgentConfigLoader
        loader = AgentConfigLoader(str(AGENTS_DIR))
        config = loader.load_config(agent_id)
        system_parts = [
            config.system_prompt,
            "",
            "## Dein Wissen",
            (config.knowledge or "")[:2000],
            "",
            "## Erinnerungen",
            (config.memories or "")[:1500],
        ]
        system_prompt = "\n".join(s for s in system_parts if s)
    except Exception as e:
        system_prompt = f"Du bist {agent_id}, ein KI-Entwickler-Agent. Antworte auf Deutsch."
    
    # Call LLM
    try:
        from src.llm.kimi_client import KimiClient, Message
        llm = KimiClient()
        messages = [Message(role="system", content=system_prompt)]
        for m in history[-20:]:
            messages.append(Message(role=m["role"], content=m["content"]))
        response = await llm.chat(messages=messages, temperature=0.3, max_tokens=2048)
        reply = response.content.strip()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM error: {str(e)}")
    
    history.append({"role": "assistant", "content": reply})
    
    return {"reply": reply, "session_id": session_id}


@app.get("/chat/history/{session_id}", tags=["Chat"])
def get_chat_history(session_id: str):
    """Get chat history for a session."""
    if session_id not in _chat_sessions:
        return {"messages": []}
    return {"messages": _chat_sessions[session_id]}


@app.delete("/chat/session/{session_id}", tags=["Chat"])
def clear_chat_session(session_id: str):
    """Clear chat history for a session."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    return {"ok": True}


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
            assigned_customers = []
            cfg_path = agent_dir / "config.yaml"
            if cfg_path.exists():
                try:
                    cfg_raw = yaml.safe_load(cfg_path.read_text(encoding="utf-8")) or {}
                    clients = cfg_raw.get("clients", [])
                    if isinstance(clients, list):
                        assigned_customers = [str(c).strip() for c in clients if str(c).strip()]
                except Exception:
                    assigned_customers = []
            agents.append({
                "id": agent_dir.name,
                "name": agent_dir.name.capitalize(),
                "description": description,
                "assigned_customers": assigned_customers,
            })
    if not agents:
        agents.append({
            "id": "mohami",
            "name": "Mohami",
            "description": "KI-Entwickler",
            "assigned_customers": [],
        })
    return agents


# === Phase 1: Learning System API Endpoints ===

@app.post("/tickets/{ticket_id}/approve", response_model=TicketResponseEnhanced, tags=["Learning System"])
def approve_ticket(
    ticket_id: str,
    approval: TicketApproval,
    db: Session = Depends(get_db),
    current_user: Optional[str] = "human"  # In echt aus Auth holen
):
    """
    Menschlicher Approval-Prozess fuer ein Ticket.
    
    - approved=true: 👍 Ticket ist erfolgreich, Learning wird gespeichert
    - approved=false: 👎 Ticket hat Fehler, kein Learning
    - feedback: Optionales Feedback fuer den Agenten
    - request_reflection: Soll Agent reflektieren?
    """
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status != "testing":
        raise HTTPException(
            status_code=400, 
            detail=f"Ticket must be in 'testing' status, current: {ticket.status}"
        )
    
    # Update Ticket mit Approval-Info
    update_data = TicketUpdateEnhanced(
        status=TicketStatus.DONE if approval.approved else TicketStatus.CLARIFICATION,
        human_approved=approval.approved,
        human_feedback=approval.feedback,
        approved_by=current_user,
        approved_at=datetime.utcnow()
    )
    
    updated_ticket = crud.update_ticket(db, ticket_id, update_data)
    
    # TODO: Trigger Learning speichern (Phase 3)
    # if approval.approved:
    #     agent.trigger_learning_save(ticket_id, approval.feedback, approval.request_reflection)
    
    return updated_ticket


@app.post("/tickets/{ticket_id}/request-changes", response_model=TicketResponseEnhanced, tags=["Learning System"])
def request_ticket_changes(
    ticket_id: str,
    changes: ChangeRequest,
    db: Session = Depends(get_db)
):
    """
    Fordert Aenderungen an einem Ticket an.
    Setzt Ticket zurueck auf 'in_progress'.
    """
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    if ticket.status not in ["testing", "done"]:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot request changes for ticket in status: {ticket.status}"
        )
    
    update_data = TicketUpdateEnhanced(
        status=TicketStatus(changes.back_to_status),
        testing_notes=changes.feedback,
        agent=None,  # Reset agent assignment
        agent_working_since=None
    )
    
    updated_ticket = crud.update_ticket(db, ticket_id, update_data)
    return updated_ticket


@app.get("/tickets/{ticket_id}/iterations", response_model=List[IterationRecord], tags=["Learning System"])
def get_ticket_iterations(ticket_id: str, db: Session = Depends(get_db)):
    """Holt alle Iterationen (Arbeitsschritte) eines Tickets."""
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    iteration_crud = TicketIterationCRUD(db)
    iterations = iteration_crud.get_by_ticket(ticket_id)
    return iterations


@app.get("/tickets/{ticket_id}/learnings", response_model=List[LearningRecordResponse], tags=["Learning System"])
def get_ticket_learnings(ticket_id: str, db: Session = Depends(get_db)):
    """Holt alle Learning Records eines Tickets."""
    ticket = crud.get_ticket(db, ticket_id)
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket not found")
    
    learning_crud = LearningRecordCRUD(db)
    learnings = learning_crud.get_by_ticket(ticket_id)
    return learnings


@app.get("/learnings", response_model=List[LearningRecordResponse], tags=["Learning System"])
def get_learnings(
    customer_id: Optional[str] = None,
    agent_id: Optional[str] = None,
    learning_type: Optional[str] = None,
    success: Optional[bool] = None,
    limit: int = 10,
    db: Session = Depends(get_db)
):
    """
    Durchsucht gelernte Lessons.
    
    Filter:
    - customer_id: Nur Learnings dieses Kunden
    - agent_id: Nur Learnings dieses Agents
    - learning_type: "success", "correction", "lesson", "anti_pattern"
    - success: True/False
    """
    learning_crud = LearningRecordCRUD(db)
    
    if customer_id:
        learnings = learning_crud.get_by_customer(
            customer_id=customer_id,
            learning_type=learning_type,
            success=success,
            limit=limit
        )
    else:
        # Global query
        query = db.query(LearningRecord)
        if agent_id:
            query = query.filter(LearningRecord.agent_id == agent_id)
        if learning_type:
            query = query.filter(LearningRecord.learning_type == learning_type)
        if success is not None:
            query = query.filter(LearningRecord.success == success)
        learnings = query.order_by(LearningRecord.created_at.desc()).limit(limit).all()
    
    return learnings


@app.get("/learnings/stats", tags=["Learning System"])
def get_learning_stats(db: Session = Depends(get_db)):
    """Statistiken ueber das Learning System."""
    total = db.query(LearningRecord).count()
    successful = db.query(LearningRecord).filter(LearningRecord.success == True).count()
    corrections = db.query(LearningRecord).filter(LearningRecord.learning_type == "correction").count()
    anti_patterns = db.query(LearningRecord).filter(LearningRecord.learning_type == "anti_pattern").count()
    
    return {
        "total_learnings": total,
        "successful": successful,
        "corrections": corrections,
        "anti_patterns": anti_patterns,
        "success_rate": (successful / total * 100) if total > 0 else 0
    }


# Run with: uvicorn src.kanban.main:app --reload
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
