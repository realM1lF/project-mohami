"""Developer Agent - Mohami - Implements ORPA workflow with real Git operations."""

import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from ..git_provider import GitProvider
from ..kanban.crud_async import TicketCRUD, CommentCRUD
from ..kanban.schemas import TicketUpdate, CommentCreate
from ..llm.kimi_client import KimiClient, Message


class AgentState(Enum):
    """Agent execution states."""
    IDLE = "idle"
    OBSERVING = "observing"
    REASONING = "reasoning"
    PLANNING = "planning"
    ACTING = "acting"


@dataclass
class AgentContext:
    """Context for the agent execution."""
    customer: str
    repository: str
    ticket_id: str
    ticket_title: str
    ticket_description: str
    project_type: str = "python"
    tech_stack: Dict = field(default_factory=dict)
    conversation_history: List[Dict] = field(default_factory=list)
    files_read: List[str] = field(default_factory=list)
    repo_structure: str = ""
    is_empty_repo: bool = True
    plan: Optional[str] = None


class DeveloperAgent:
    """Developer Agent - Mohami - Makes real commits and PRs."""
    
    def __init__(
        self,
        git_provider: GitProvider,
        llm_client: KimiClient,
        ticket_crud: TicketCRUD,
        comment_crud: CommentCRUD,
        agent_id: str = "mohami"
    ):
        self.agent_id = agent_id  # "mohami"
        self.git = git_provider
        self.llm = llm_client
        self.tickets = ticket_crud
        self.comments = comment_crud
        self.state = AgentState.IDLE
        self.current_context: Optional[AgentContext] = None
    
    async def process_ticket(self, ticket_id: str, ticket_data: Optional[Dict] = None) -> None:
        """Process a ticket through ORPA workflow."""
        try:
            self.state = AgentState.OBSERVING
            context = await self._observe(ticket_id)
            self.current_context = context
            
            self.state = AgentState.REASONING
            analysis = await self._reason(context)
            
            self.state = AgentState.PLANNING
            plan = await self._plan(context, analysis)
            context.plan = plan
            
            self.state = AgentState.ACTING
            await self._act(context, analysis, plan)
            
        except Exception as e:
            await self._handle_error(ticket_id, e)
        finally:
            self.state = AgentState.IDLE
            self.current_context = None
    
    async def _observe(self, ticket_id: str) -> AgentContext:
        """OBSERVE: Analyze repository and ticket."""
        ticket = await self.tickets.get(ticket_id)
        if not ticket:
            raise ValueError(f"Ticket {ticket_id} not found")
        
        # Set to in_progress
        await self.tickets.update(
            ticket_id,
            TicketUpdate(status="in_progress", agent=self.agent_id)
        )
        
        comments = await self.comments.get_by_ticket(ticket_id)
        
        context = AgentContext(
            customer=ticket.customer,
            repository=ticket.repository,
            ticket_id=ticket_id,
            ticket_title=ticket.title,
            ticket_description=ticket.description,
            conversation_history=[
                {"from": c.author, "text": c.content, "at": c.created_at}
                for c in comments
            ]
        )
        
        # Check repository state
        try:
            repo_info = await self.git.get_repository_info(ticket.repository)
            context.tech_stack["default_branch"] = repo_info.default_branch
            
            # List files to check if empty
            branches = await self.git.list_branches(ticket.repository)
            
            # Try to read existing README
            try:
                readme = await self.git.get_file_content(
                    ticket.repository, "README.md", repo_info.default_branch
                )
                context.files_read.append("README.md")
                context.is_empty_repo = False
                context.repo_structure = "Repository hat bereits README.md"
            except:
                context.is_empty_repo = True
                context.repo_structure = "Leeres Repository (keine README.md)"
                
        except Exception as e:
            context.repo_structure = f"Konnte Repo nicht analysieren: {e}"
        
        return context
    
    async def _reason(self, context: AgentContext) -> str:
        """REASON: Analyze what needs to be done."""
        system_prompt = """Du bist Mohami, ein KI-Entwickler. 
Analysiere das Ticket und entscheide: Kann ich direkt implementieren oder brauche ich eine Rückfrage?
Antworte kurz und auf Deutsch."""
        
        user_prompt = f"""Ticket: {context.ticket_title}
Beschreibung: {context.ticket_description}
Repository-Status: {context.repo_structure}

Was muss gemacht werden? Soll ich direkt loslegen oder eine Rückfrage stellen?"""
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = await self.llm.chat(messages, temperature=0.3, max_tokens=300)
        return response.content
    
    async def _plan(self, context: AgentContext, analysis: str) -> str:
        """PLAN: Create implementation plan."""
        system_prompt = "Du bist Mohami. Erstelle einen kurzen Plan (2-3 Punkte). Antworte auf Deutsch."
        
        user_prompt = f"""Analyse: {analysis}

Erstelle einen Implementierungsplan:
1. Was muss ich tun?
2. Welche Dateien ändere/erstelle ich?
3. Was ist die Commit-Message?"""
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = await self.llm.chat(messages, temperature=0.3, max_tokens=400)
        return response.content
    
    async def _act(self, context: AgentContext, analysis: str, plan: str) -> None:
        """ACT: Implement or ask. This makes REAL commits."""
        # Decide if we need clarification
        needs_clarification = self._check_needs_clarification(analysis, plan, context)
        
        if needs_clarification:
            # Ask ONE focused question
            question = await self._generate_question(context, analysis)
            await self._add_comment(
                context.ticket_id,
                f"❓ {question}\n\nAntworte kurz, dann mache ich weiter."
            )
            await self.tickets.update(
                context.ticket_id,
                TicketUpdate(status="clarification")
            )
        else:
            # IMPLEMENT - Make real commits
            await self._implement(context, plan)
    
    def _check_needs_clarification(self, analysis: str, plan: str, context: AgentContext) -> bool:
        """Check if we really need to ask or can proceed."""
        # For simple tasks like "add README with COMING SOON", just do it
        desc_lower = context.ticket_description.lower()
        
        # Simple README tasks don't need clarification
        if "readme" in desc_lower and ("coming soon" in desc_lower or "initial" in desc_lower):
            return False
        
        # Check if analysis suggests questions
        analysis_lower = analysis.lower()
        if any(word in analysis_lower for word in ["unklar", "frage", "rückfrage", "?"]):
            return True
        
        return False
    
    async def _generate_question(self, context: AgentContext, analysis: str) -> str:
        """Generate ONE focused question."""
        system_prompt = "Du bist Mohami. Stelle EINE konkrete Rückfrage. Maximal 2 Sätze. Deutsch."
        
        user_prompt = f"""Analyse: {analysis}

Stelle EINE kurze, präzise Frage an den Kunden. Was ist das wichtigste Unklare?"""
        
        messages = [
            Message(role="system", content=system_prompt),
            Message(role="user", content=user_prompt)
        ]
        
        response = await self.llm.chat(messages, temperature=0.3, max_tokens=200)
        return response.content.strip()
    
    async def _implement(self, context: AgentContext, plan: str) -> None:
        """Actually implement - create branch, commit, push, PR (or direct commit for empty repo)."""
        ticket_id_short = context.ticket_id[:8]
        
        try:
            # Check if repo is empty
            repo_info = await self.git.get_repository_info(context.repository)
            default_branch = repo_info.default_branch
            
            # Try to get latest commit - if fails, repo is empty
            is_empty_repo = False
            try:
                branches = await self.git.list_branches(context.repository)
                if not branches or len(branches) == 0:
                    is_empty_repo = True
            except:
                is_empty_repo = True
            
            # Generate files
            files_to_commit = await self._generate_files(context)
            
            if not files_to_commit:
                await self._add_comment(
                    context.ticket_id,
                    "⚠️ Konnte keine Dateien generieren. Bitte präzisiere die Anforderung."
                )
                await self.tickets.update(
                    context.ticket_id,
                    TicketUpdate(status="clarification")
                )
                return
            
            commit_message = f"[{context.ticket_id[:8]}] {context.ticket_title}"
            
            if is_empty_repo:
                # EMPTY REPO: Direct commit to main
                await self._add_comment(
                    context.ticket_id,
                    f"⚡ Repository ist leer. Erstelle Initial-Commit auf `{default_branch}`..."
                )
                
                # For empty repo, we need to use a different approach
                # GitHub API allows creating files in empty repos which auto-creates the branch
                for file_path, content in files_to_commit.items():
                    await self._create_file_in_empty_repo(
                        context.repository,
                        file_path,
                        content,
                        commit_message
                    )
                
                await self._add_comment(
                    context.ticket_id,
                    f"✅ **Fertig!**\n\n"
                    f"Ich habe einen Initial-Commit auf `{default_branch}` erstellt:\n"
                    f"- README.md hinzugefügt\n"
                    f"- .gitignore hinzugefügt\n\n"
                    f"Das Repository ist jetzt bereit! 🎉"
                )
                
                await self.tickets.update(
                    context.ticket_id,
                    TicketUpdate(status="done")
                )
                
            else:
                # NORMAL FLOW: Branch + PR
                branch_name = f"feature/{ticket_id_short}-{self._slugify(context.ticket_title)}"
                
                await self._add_comment(
                    context.ticket_id,
                    f"⚡ Ich implementiere das jetzt. Erstelle Branch `{branch_name}`..."
                )
                
                # Create branch (delete if exists to allow retry)
                try:
                    await self.git.create_branch(context.repository, branch_name, default_branch)
                except Exception as branch_error:
                    if "already exists" in str(branch_error) or "Reference already exists" in str(branch_error):
                        # Branch exists, try to delete and recreate
                        try:
                            await self.git.delete_branch(context.repository, branch_name)
                            await self.git.create_branch(context.repository, branch_name, default_branch)
                        except:
                            # If we can't delete, just use the existing branch
                            pass
                    else:
                        raise
                
                # Commit files
                await self.git.create_commit(
                    context.repository,
                    branch_name,
                    commit_message,
                    files_to_commit,
                    author_name="Mohami",
                    author_email="mohami@ki-agent.dev"
                )
                
                # Create PR
                pr_title = f"[{context.ticket_id[:8]}] {context.ticket_title}"
                pr_body = f"""## Änderungen
{plan}

## Ticket
{context.ticket_id}

## Prüfung
- [ ] Code Review durchgeführt
- [ ] Tests erfolgreich"""
                
                pr = await self.git.create_pr(
                    context.repository,
                    pr_title,
                    pr_body,
                    branch_name,
                    default_branch
                )
                
                # 7. Success message
                await self._add_comment(
                    context.ticket_id,
                    f"✅ **Fertig!**\n\n"
                    f"Ich habe einen Pull Request erstellt:\n"
                    f"🔗 [{pr.title}]({pr.url})\n\n"
                    f"Branch: `{branch_name}`\n"
                    f"Bitte reviewen und mergen."
                )
                
                # 8. Update ticket status
                await self.tickets.update(
                    context.ticket_id,
                    TicketUpdate(status="testing")
                )
            
        except Exception as e:
            await self._add_comment(
                context.ticket_id,
                f"❌ Fehler beim Implementieren: {str(e)}\n\n"
                f"Ich setze das Ticket auf 'Rückfrage'."
            )
            await self.tickets.update(
                context.ticket_id,
                TicketUpdate(status="clarification")
            )
    
    async def _generate_files(self, context: AgentContext) -> Dict[str, str]:
        """Generate file contents based on ticket description."""
        files = {}
        desc_lower = context.ticket_description.lower()
        
        # README.md generation
        if "readme" in desc_lower:
            # Extract content if specified
            content = "COMING SOON"  # default
            
            # Try to find content in quotes
            import re
            quotes = re.findall(r'["\']([^"\']+)["\']', context.ticket_description)
            if quotes:
                content = quotes[0]
            else:
                # Try to find content after colon (e.g., "Zeile 2: Bald entsteht hier ein Projekt")
                colon_match = re.search(r':\s*(.+)$', context.ticket_description.strip())
                if colon_match:
                    content = colon_match.group(1).strip()
            
            # Check if README.md exists and we need to append/modify
            try:
                existing_content = await self.git.get_file_content(
                    context.repository, "README.md", "main"
                )
                # If we have existing content and need to add a line
                if existing_content and ("ergänz" in desc_lower or "hinzufüg" in desc_lower):
                    # Add new content as second line
                    lines = existing_content.split('\n')
                    lines.insert(1, content)  # Insert at line 2 (index 1)
                    content = '\n'.join(lines)
                # If file exists but we want to replace, use new content as-is
            except:
                # File doesn't exist, use new content
                pass
            
            files["README.md"] = content
        
        # .gitignore for Python projects
        if not context.files_read:  # Empty repo
            files[".gitignore"] = """# Python
__pycache__/
*.py[cod]
*$py.class
*.so
.Python
env/
venv/
.env
.venv
pip-log.txt

# IDE
.vscode/
.idea/
*.swp
*.swo

# OS
.DS_Store
Thumbs.db
"""
        
        return files
    
    def _slugify(self, text: str) -> str:
        """Convert title to branch-safe slug."""
        import re
        slug = re.sub(r'[^\w\s-]', '', text.lower())
        slug = re.sub(r'[-\s]+', '-', slug)
        return slug[:30]
    
    async def _create_file_in_empty_repo(self, repo: str, path: str, content: str, message: str) -> None:
        """Create a file in an empty repo using GitHub API.
        
        This uses the contents API which automatically creates the branch.
        """
        import base64
        import httpx
        
        # Parse owner/repo
        parts = repo.split('/')
        if len(parts) != 2:
            raise ValueError(f"Invalid repo format: {repo}")
        owner, repo_name = parts
        
        # Encode content to base64
        content_bytes = content.encode('utf-8')
        content_b64 = base64.b64encode(content_bytes).decode('utf-8')
        
        # GitHub API endpoint
        url = f"https://api.github.com/repos/{owner}/{repo_name}/contents/{path}"
        
        headers = {
            "Authorization": f"Bearer {self.git.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json"
        }
        
        payload = {
            "message": message,
            "content": content_b64
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.put(url, headers=headers, json=payload, timeout=30.0)
            
            if response.status_code not in [200, 201]:
                raise Exception(f"GitHub API error: {response.status_code} - {response.text}")
    
    async def _add_comment(self, ticket_id: str, content: str) -> None:
        """Add a comment to the ticket."""
        comment = CommentCreate(
            author=self.agent_id,
            content=content
        )
        await self.comments.create(ticket_id, comment)
    
    async def _handle_error(self, ticket_id: str, error: Exception) -> None:
        """Handle errors."""
        await self._add_comment(ticket_id, f"❌ Fehler: {str(error)[:200]}")
        print(f"Agent {self.agent_id} error on ticket {ticket_id}: {error}")
    
    async def run_auto_mode(self, poll_interval: int = 30) -> None:
        """Auto-mode: continuously check for new tickets."""
        print(f"🤖 {self.agent_id} gestartet")
        while True:
            try:
                from ..kanban.models import TicketStatus
                
                # Check for new tickets
                open_tickets = await self.tickets.list(
                    status=TicketStatus.BACKLOG,
                    agent=None
                )
                
                for ticket in open_tickets:
                    print(f"📨 Neues Ticket: {ticket.id}")
                    await self.process_ticket(ticket.id)
                
                # Check for clarification tickets with new responses
                clarification_tickets = await self.tickets.list(
                    status=TicketStatus.CLARIFICATION
                )
                
                for ticket in clarification_tickets:
                    if ticket.agent == self.agent_id:
                        comments = await self.comments.get_by_ticket(ticket.id)
                        
                        if comments and len(comments) > 0:
                            # Comments are sorted DESC (newest first), so check [0]
                            latest_comment = comments[0]
                            
                            # If latest comment is from user (not mohami), process
                            if not latest_comment.author.startswith(self.agent_id):
                                print(f"💬 Rückfrage beantwortet: {ticket.id} (von {latest_comment.author})")
                                await self.process_ticket(ticket.id)
                
            except Exception as e:
                print(f"Error in auto-mode: {e}")
            
            await asyncio.sleep(poll_interval)
