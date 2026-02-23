#!/usr/bin/env python3
"""Detaillierter Import-Test, der das Worker-Verhalten simuliert."""

import sys
import os

print("=" * 60)
print("DETAILEIRTER IMPORT TEST")
print("=" * 60)
print(f"\nPython path: {sys.path}")
print(f"CWD: {os.getcwd()}")
print(f"\nDateien in /app/src:")
if os.path.exists('/app/src'):
    for item in os.listdir('/app/src'):
        print(f"  - {item}")
else:
    print("  /app/src existiert NICHT!")

print("\n" + "=" * 60)
print("TEST 1: Relativer Import (wie in intelligent_agent.py)")
print("=" * 60)

# Simuliere das Verhalten von intelligent_agent.py
# Das File ist in /app/src/agents/, also müssen wir von dort importieren

print("\nVersuche relativen Import 'from ..tools.registry import ToolRegistry':")
print("(Dies würde aus src/agents/ heraus passieren)")

# Wir müssen das Modul so laden, als wären wir in src/agents/
sys.path.insert(0, '/app/src/agents')

try:
    # Das ist der relative Import, der in intelligent_agent.py verwendet wird
    from tools.registry import ToolRegistry
    print("✅ tools.registry OK (absolut von src/agents)")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST 2: Absoluter Import von /app")
print("=" * 60)

sys.path.insert(0, '/app')

try:
    from src.tools.registry import ToolRegistry
    print("✅ src.tools.registry OK")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST 3: Vollständiger IntelligentAgent Import")
print("=" * 60)

try:
    from src.agents.intelligent_agent import IntelligentAgent
    print("✅ IntelligentAgent import OK")
    print(f"   TOOLS_AVAILABLE: {IntelligentAgent.__module__}")
except Exception as e:
    print(f"❌ FAILED: {e}")
    import traceback
    traceback.print_exc()

print("\n" + "=" * 60)
print("TEST 4: Import wie im Worker (agent_worker.py)")
print("=" * 60)

# Reset path to simulate fresh start
sys.path = [p for p in sys.path if p not in ['/app', '/app/src/agents']]

print(f"\nCleaned Python path: {sys.path[:3]}...")
print("\nVersuche Worker-Import (ohne /app in path):")

try:
    from src.agents.intelligent_agent import IntelligentAgent
    print("✅ Worker-Import OK")
except Exception as e:
    print(f"❌ Worker-Import FAILED: {e}")
    import traceback
    traceback.print_exc()
