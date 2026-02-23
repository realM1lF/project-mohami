#!/usr/bin/env python3
"""Integration test for the complete KI-Mitarbeiter system."""

import asyncio
import sys
from pathlib import Path

# Load env
from dotenv import load_dotenv
load_dotenv(Path(__file__).parent / ".env", override=True)

print("=" * 70)
print("🤖 KI-Mitarbeiter System - Integration Test")
print("=" * 70)

# Test 1: Environment
print("\n1️⃣  Testing Environment Variables...")
import os

github_token = os.getenv("GITHUB_TOKEN")
test_repo = os.getenv("TEST_REPO")
router_key = os.getenv("OPEN_ROUTER_API_KEY")

if not github_token:
    print("   ❌ GITHUB_TOKEN missing")
    sys.exit(1)
print(f"   ✅ GITHUB_TOKEN: {github_token[:10]}...")

if not test_repo:
    print("   ❌ TEST_REPO missing")
    sys.exit(1)
print(f"   ✅ TEST_REPO: {test_repo}")

if not router_key:
    print("   ❌ OPEN_ROUTER_API_KEY missing")
    sys.exit(1)
print(f"   ✅ OPEN_ROUTER_API_KEY: {router_key[:15]}...")

# Test 2: Database
print("\n2️⃣  Testing Database Connection...")
from sqlalchemy import create_engine
from src.kanban.models import Base

engine = create_engine("sqlite:///./kanban.db", connect_args={"check_same_thread": False})
Base.metadata.create_all(bind=engine)
print("   ✅ Database initialized")

# Test 3: Git Provider
print("\n3️⃣  Testing GitHub Connection...")
from src.git_provider import GitHubProvider

git = GitHubProvider(github_token)

async def test_git():
    try:
        repos = await git.list_repositories()
        print(f"   ✅ Found {len(repos)} repositories")
        
        # Check if test repo is accessible
        repo_names = [r.full_name for r in repos]
        if test_repo in repo_names:
            print(f"   ✅ Test repo '{test_repo}' is accessible")
        else:
            print(f"   ⚠️  Test repo '{test_repo}' not in list, but might still work")
        return True
    except Exception as e:
        print(f"   ❌ GitHub error: {e}")
        return False

if not asyncio.run(test_git()):
    sys.exit(1)

# Test 4: LLM Client
print("\n4️⃣  Testing OpenRouter/Kimi Connection...")
from src.llm import KimiClient

async def test_llm():
    try:
        client = KimiClient()
        from src.llm.kimi_client import Message
        
        response = await client.chat(
            [Message(role="user", content="Say 'Test successful' and nothing else.")],
            max_tokens=10
        )
        print(f"   ✅ LLM Response: {response.content[:50]}...")
        return True
    except Exception as e:
        print(f"   ❌ LLM error: {e}")
        return False

if not asyncio.run(test_llm()):
    sys.exit(1)

# Test 5: API Endpoints
print("\n5️⃣  Testing API Endpoints...")
import httpx

async def test_api():
    try:
        # Test health endpoint
        response = httpx.get("http://localhost:8000/health")
        if response.status_code == 200:
            print("   ✅ Backend API is running")
        else:
            print(f"   ⚠️  Backend returned {response.status_code}")
    except Exception as e:
        print(f"   ⚠️  Backend not running on port 8000: {e}")
        print("      Start with: uvicorn src.kanban.main:app --reload")

asyncio.run(test_api())

print("\n" + "=" * 70)
print("✅ Integration test complete!")
print("=" * 70)
print("\n🚀 You can now start the system:")
print("   Terminal 1: uvicorn src.kanban.main:app --reload")
print("   Terminal 2: python agent_worker.py")
print("   Terminal 3: cd frontend && npm start")
print("\n🌐 Then open: http://localhost:3000")
