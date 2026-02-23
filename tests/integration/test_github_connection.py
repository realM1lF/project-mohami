#!/usr/bin/env python3
"""Test script to verify GitHub connection."""

import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv

from src.git_provider import GitHubProvider

# Load .env file
env_path = Path(__file__).parent / ".env"
load_dotenv(env_path)


async def test_connection():
    """Test GitHub connection and repository access."""
    
    token = os.getenv("GITHUB_TOKEN")
    repo = os.getenv("TEST_REPO")
    
    if not token:
        print("❌ GITHUB_TOKEN not found in .env file")
        return
    
    if not repo:
        print("❌ TEST_REPO not found in .env file")
        print("   Add: TEST_REPO=your-username/your-repo")
        return
    
    print(f"🔑 Token found: {token[:10]}...")
    print(f"📁 Repository: {repo}")
    print()
    
    # Create provider
    provider = GitHubProvider(token)
    
    try:
        # Test 1: List repositories
        print("Test 1: Listing accessible repositories...")
        repos = await provider.list_repositories()
        print(f"✅ Found {len(repos)} repositories")
        
        # Check if our repo is in the list
        repo_names = [r.full_name for r in repos]
        if repo in repo_names:
            print(f"✅ Target repository '{repo}' is accessible")
        else:
            print(f"⚠️  Repository '{repo}' not found in accessible repos")
            print(f"   Available: {', '.join(repo_names[:5])}...")
        
        print()
        
        # Test 2: Get repository info
        print(f"Test 2: Getting repository info for {repo}...")
        info = await provider.get_repository_info(repo)
        print(f"✅ Repository: {info.name}")
        print(f"   URL: {info.url}")
        print(f"   Default branch: {info.default_branch}")
        print(f"   Private: {info.private}")
        
        print()
        
        # Test 3: List branches
        print("Test 3: Listing branches...")
        branches = await provider.list_branches(repo)
        print(f"✅ Found branches: {', '.join(branches[:5])}")
        
        print()
        
        # Test 4: Read a file (if README.md exists)
        print("Test 4: Trying to read README.md...")
        try:
            content = await provider.get_file_content(repo, "README.md", info.default_branch)
            print(f"✅ README.md found ({len(content)} characters)")
            print(f"   Preview: {content[:100]}...")
        except Exception as e:
            print(f"⚠️  Could not read README.md: {e}")
        
        print()
        print("=" * 50)
        print("🎉 All tests passed! GitHub connection is working.")
        print("=" * 50)
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print()
        print("Troubleshooting:")
        print("1. Check if token is valid and not expired")
        print("2. Check if repository name is correct (format: username/repo)")
        print("3. Check if token has 'repo' scope")


if __name__ == "__main__":
    asyncio.run(test_connection())
