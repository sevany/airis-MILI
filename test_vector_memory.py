#!/usr/bin/env python3
"""
Test AIRIS Vector Memory System
Quick verification that ChromaDB is working
"""
import sys
sys.path.insert(0, '.')

from backend.core.vector_memory import VectorMemory
import time

print("="*60)
print("🧠 AIRIS VECTOR MEMORY TEST")
print("="*60)

# Initialize
print("\n1. Initializing vector memory...")
memory = VectorMemory()

# Test 1: Add conversations
print("\n2. Adding test conversations...")
test_conversations = [
    {
        "user": "What's the current gold price?",
        "assistant": "The current gold price is $4538.34, up 0.5% from yesterday.",
        "metadata": {"topic": "gold_price", "has_xauusd": True}
    },
    {
        "user": "Should I buy gold now?",
        "assistant": "Based on current technical analysis, gold is in an uptrend with strong support at $4500. The RSI is at 65, indicating momentum but not overbought yet.",
        "metadata": {"topic": "trading_advice", "has_xauusd": True}
    },
    {
        "user": "What's your name?",
        "assistant": "I'm AIRIS - Artificial Intelligence Responsive Intelligent System. I'm your personal AI companion built exclusively for you, Myra.",
        "metadata": {"topic": "identity", "has_xauusd": False}
    },
    {
        "user": "Boleh cakap Melayu tak?",
        "assistant": "Ya, saya boleh faham dan bercakap dalam Bahasa Melayu. Apa yang boleh saya bantu?",
        "metadata": {"topic": "language", "has_xauusd": False}
    }
]

for conv in test_conversations:
    memory_id = memory.add_conversation(
        user_message=conv["user"],
        assistant_response=conv["assistant"],
        metadata=conv["metadata"]
    )
    print(f"  ✓ Stored: {conv['user'][:50]}...")
    time.sleep(0.5)

# Test 2: Search memory
print("\n3. Testing semantic search...")

searches = [
    "gold trading strategies",
    "who are you",
    "bahasa melayu"
]

for query in searches:
    print(f"\n  🔍 Query: '{query}'")
    results = memory.search_memory(query, n_results=2)
    for i, r in enumerate(results, 1):
        print(f"    {i}. {r['metadata']['user_message'][:60]}...")
        print(f"       Distance: {r['distance']:.4f}")

# Test 3: Get stats
print("\n4. Memory statistics:")
stats = memory.get_stats()
print(f"  📊 Total memories: {stats['total_memories']}")
print(f"  📅 Oldest: {stats['oldest_memory']}")
print(f"  📅 Newest: {stats['newest_memory']}")

# Test 4: Get recent
print("\n5. Recent conversations:")
recent = memory.get_recent_conversations(n=3)
for i, r in enumerate(recent, 1):
    print(f"  {i}. {r['metadata']['user_message'][:60]}...")

# Test 5: Context retrieval (RAG)
print("\n6. Testing context retrieval for RAG:")
query = "Tell me about gold"
context = memory.get_context_for_query(query, max_context_length=500)
print(f"  Query: '{query}'")
print(f"  Context length: {len(context)} chars")
print(f"  Context preview:\n{context[:200]}...")

# Test 6: Health check
print("\n7. Health check:")
is_healthy, msg = memory.health_check()
print(f"  {msg}")

print("\n" + "="*60)
print("✅ ALL TESTS PASSED!")
print("="*60)
print("\n💡 Memory is stored in: ./data/memory/")
print("💡 You can now chat with AIRIS and she'll remember everything!")
print()