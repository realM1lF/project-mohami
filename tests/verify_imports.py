#!/usr/bin/env python3
"""Verify all imports work correctly.

This script tests that all critical imports in the Mohami project work,
especially when running in Docker containers where relative imports fail.
"""

import sys
import os

# Ensure the current directory is in the path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_import(module_path: str, description: str) -> bool:
    """Test a single import and report result."""
    try:
        __import__(module_path)
        print(f"  ✓ {description}")
        return True
    except Exception as e:
        print(f"  ✗ {description}: {e}")
        return False

def main():
    """Run all import tests."""
    print("=" * 60)
    print("MOHAMI IMPORT VERIFICATION")
    print("=" * 60)
    
    results = []
    
    # Test 1: Core agent types
    print("\n1. Testing agent types...")
    results.append(test_import("src.agents.agent_types", "agent_types"))
    
    # Test 2: ORPA states
    print("\n2. Testing ORPA states...")
    results.append(test_import("src.agents.orpa_states", "orpa_states"))
    
    # Test 3: Tools modules
    print("\n3. Testing tools modules...")
    results.append(test_import("src.tools.base", "tools.base"))
    results.append(test_import("src.tools.registry", "tools.registry"))
    results.append(test_import("src.tools.executor", "tools.executor"))
    results.append(test_import("src.tools.file_tools", "tools.file_tools"))
    results.append(test_import("src.tools.code_tools", "tools.code_tools"))
    results.append(test_import("src.tools.git_tools", "tools.git_tools"))
    
    # Test 4: Memory modules
    print("\n4. Testing memory modules...")
    results.append(test_import("src.memory.base", "memory.base"))
    results.append(test_import("src.memory.unified_manager", "memory.unified_manager"))
    
    # Test 5: Infrastructure
    print("\n5. Testing infrastructure modules...")
    results.append(test_import("src.infrastructure.workspace_manager", "infrastructure.workspace_manager"))
    results.append(test_import("src.infrastructure.repository_manager", "infrastructure.repository_manager"))
    
    # Test 6: LLM
    print("\n6. Testing LLM modules...")
    results.append(test_import("src.llm.kimi_client", "llm.kimi_client"))
    
    # Test 7: The critical one - IntelligentAgent
    print("\n7. Testing IntelligentAgent (CRITICAL)...")
    results.append(test_import("src.agents.intelligent_agent", "intelligent_agent"))
    
    # Try to instantiate it
    print("\n8. Testing IntelligentAgent instantiation...")
    try:
        from src.agents.intelligent_agent import IntelligentAgent
        from src.agents.agent_types import AgentConfig
        config = AgentConfig(customer_id="test")
        agent = IntelligentAgent("test-agent", config)
        print(f"  ✓ IntelligentAgent instantiated: {agent.agent_id}")
        results.append(True)
    except Exception as e:
        print(f"  ✗ IntelligentAgent instantiation failed: {e}")
        results.append(False)
    
    # Summary
    print("\n" + "=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"RESULTS: {passed}/{total} tests passed")
    
    if passed == total:
        print("✓ ALL IMPORTS OK - Production ready!")
        return 0
    else:
        print("✗ SOME IMPORTS FAILED - Check errors above")
        return 1

if __name__ == "__main__":
    sys.exit(main())
