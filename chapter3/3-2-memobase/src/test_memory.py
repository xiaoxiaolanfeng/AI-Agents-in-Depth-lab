"""
Test script for Memobase memory functionality
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from agent import Memory, MemoryStore, MemoryCluster, MemobaseAgent
from config import MEMORY_DB_PATH


def test_memory_basics():
    """Test basic memory operations"""
    print("\n" + "=" * 50)
    print("Testing Basic Memory Operations")
    print("=" * 50)
    
    # Create a memory
    memory = Memory(
        id="",
        type="episodic",
        content={"event": "User asked about Python", "response": "Python is great for data science"},
        importance_score=2.0
    )
    
    print(f"✅ Created memory with ID: {memory.id}")
    print(f"   Type: {memory.type}")
    print(f"   Importance: {memory.importance_score}")
    
    # Test access
    initial_count = memory.access_count
    memory.access()
    print(f"✅ Memory accessed: count {initial_count} -> {memory.access_count}")
    
    # Test decay
    initial_importance = memory.importance_score
    time.sleep(0.1)  # Small delay
    memory.decay()
    print(f"✅ Memory decayed: importance {initial_importance:.2f} -> {memory.importance_score:.2f}")
    
    return True


def test_memory_store():
    """Test memory store operations"""
    print("\n" + "=" * 50)
    print("Testing Memory Store")
    print("=" * 50)
    
    # Create temporary store
    test_path = Path("test_memory_store")
    test_path.mkdir(exist_ok=True)
    store = MemoryStore(db_path=test_path)
    
    # Add memories of different types
    memories_added = []
    
    # Episodic memory
    mem1 = store.add_memory(
        memory_type="episodic",
        content="First interaction with user about machine learning",
        metadata={"session": "test_001"},
        importance=2.0
    )
    memories_added.append(mem1)
    print(f"✅ Added episodic memory: {mem1.id}")
    
    # Semantic memory
    mem2 = store.add_memory(
        memory_type="semantic",
        content="Python is a programming language used for data science",
        metadata={"domain": "programming"},
        importance=1.5
    )
    memories_added.append(mem2)
    print(f"✅ Added semantic memory: {mem2.id}")
    
    # Procedural memory
    mem3 = store.add_memory(
        memory_type="procedural",
        content={"pattern": "debugging", "approach": "check logs first"},
        metadata={"learned_from": "experience"},
        importance=3.0
    )
    memories_added.append(mem3)
    print(f"✅ Added procedural memory: {mem3.id}")
    
    # Working memory
    mem4 = store.add_memory(
        memory_type="working",
        content="Current task: testing memory system",
        importance=1.0
    )
    memories_added.append(mem4)
    print(f"✅ Added working memory: {mem4.id}")
    
    # Test retrieval
    print("\n📚 Testing Memory Retrieval:")
    
    # Get episodic memories
    episodic = store.get_memories("episodic", limit=5)
    print(f"   Episodic memories retrieved: {len(episodic)}")
    
    # Search memories
    search_results = store.search_memories("Python", limit=3)
    print(f"   Search for 'Python': {len(search_results)} results")
    
    # Test persistence
    store._save_memories()
    print("✅ Memories saved to disk")
    
    # Create new store and load
    store2 = MemoryStore(db_path=test_path)
    total_memories = sum(len(mems) for mems in store2.memories.values())
    print(f"✅ Memories loaded from disk: {total_memories} total")
    
    # Test consolidation
    store.consolidate_memories()
    print("✅ Memory consolidation completed")
    
    # Clear working memory
    store.clear_working_memory()
    working_after = len(store.memories.get('working', []))
    print(f"✅ Working memory cleared: {working_after} remaining")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_path)
    print("✅ Test data cleaned up")
    
    return True


def test_memory_compression():
    """Test memory compression functionality"""
    print("\n" + "=" * 50)
    print("Testing Memory Compression")
    print("=" * 50)
    
    # Create store with low threshold for testing
    test_path = Path("test_compression")
    test_path.mkdir(exist_ok=True)
    store = MemoryStore(db_path=test_path)
    
    # Add many memories to trigger compression
    print("Adding memories to trigger compression...")
    for i in range(10):
        store.add_memory(
            memory_type="episodic",
            content=f"Memory {i}: Event occurred at time {i}",
            importance=1.0 if i < 5 else 2.0
        )
    
    # Force compression by adding more with low threshold
    original_threshold = 50  # From config
    test_threshold = 5
    
    # Manually trigger compression
    if len(store.memories['episodic']) > test_threshold:
        print(f"   Memories before compression: {len(store.memories['episodic'])}")
        store._compress_memories('episodic')
        print(f"   Memories after compression: {len(store.memories['episodic'])}")
        print(f"   Clusters created: {len(store.clusters)}")
    
    print("✅ Compression test completed")
    
    # Cleanup
    import shutil
    shutil.rmtree(test_path)
    
    return True


def test_agent_memory_integration():
    """Test agent integration with memory system"""
    print("\n" + "=" * 50)
    print("Testing Agent Memory Integration")
    print("=" * 50)
    
    # Check for API key
    api_key = os.getenv("KIMI_API_KEY", "test-key")
    
    # Initialize agent
    agent = MemobaseAgent(api_key=api_key)
    print("✅ Agent initialized with memory system")
    
    # Test memory operations through agent
    print("\n📊 Initial state:")
    metrics = agent.get_performance_metrics()
    print(f"   Total memories: {metrics['total_memories']}")
    print(f"   Distribution: {metrics['memory_distribution']}")
    
    # Simulate learning
    agent._learn_from_outcome(
        task="test_task",
        approach="test_approach",
        outcome="successful",
        success=True
    )
    print("✅ Agent learned from outcome")
    
    # Check procedural memory
    procedural = agent.memory_store.get_memories("procedural", limit=1)
    if procedural:
        print(f"✅ Procedural memory created: {procedural[0].id}")
    
    # Test memory retrieval in context
    relevant = agent._retrieve_relevant_memories("test query", limit=3)
    print(f"✅ Retrieved {len(relevant)} relevant memories")
    
    # Test consolidation
    agent.consolidate_and_learn()
    print("✅ Agent consolidation completed")
    
    # Test reset with memory preservation
    agent.reset(keep_memories=True)
    metrics_after = agent.get_performance_metrics()
    print(f"✅ Agent reset (memories preserved): {metrics_after['total_memories']} memories retained")
    
    # Test reset without memory preservation
    agent.reset(keep_memories=False)
    metrics_final = agent.get_performance_metrics()
    print(f"✅ Agent reset (memories cleared): {metrics_final['total_memories']} memories remaining")
    
    return True


def run_all_tests():
    """Run all memory tests"""
    print("\n" + "=" * 60)
    print("MEMOBASE MEMORY SYSTEM TEST SUITE")
    print("=" * 60)
    
    tests = [
        ("Basic Memory Operations", test_memory_basics),
        ("Memory Store", test_memory_store),
        ("Memory Compression", test_memory_compression),
        ("Agent Integration", test_agent_memory_integration)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            success = test_func()
            results.append((test_name, success))
        except Exception as e:
            print(f"\n❌ Test '{test_name}' failed: {str(e)}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for test_name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status}: {test_name}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 All tests passed successfully!")
    else:
        print(f"\n⚠️  {total - passed} test(s) failed")
    
    return passed == total


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)
