"""Simple test to verify the Mem0 agent setup."""

import os
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()


def test_imports():
    """Test that all modules can be imported."""
    print("Testing imports...")
    try:
        from agent import Mem0Agent, AgentContext, KimiK3Client
        print("✓ Agent module imported successfully")
        
        from config import Config, KimiConfig, Mem0Config, LOCOMOConfig
        print("✓ Config module imported successfully")
        
        from experiment import LOCOMOBenchmark
        print("✓ Experiment module imported successfully")
        
        import mem0
        print("✓ Mem0 library available")
        
        import openai
        print("✓ OpenAI library available")
        
        return True
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False


def test_configuration():
    """Test configuration loading."""
    print("\nTesting configuration...")
    try:
        from config import Config
        
        config = Config.from_env()
        
        # Check if API key is set
        if not config.kimi.api_key:
            print("⚠ Warning: KIMI_API_KEY not set in environment")
            print("  Please create a .env file from env.example and add your API key")
            return False
        else:
            print(f"✓ Kimi API key configured (length: {len(config.kimi.api_key)})")
        
        print(f"✓ Model: {config.kimi.model_name}")
        print(f"✓ Max tokens: {config.kimi.max_tokens}")
        print(f"✓ Memory backend: {config.mem0.backend}")
        print(f"✓ LOCOMO data path: {config.locomo.data_path}")
        
        # Validate configuration
        config.validate()
        print("✓ Configuration validation passed")
        
        return True
    except Exception as e:
        print(f"✗ Configuration error: {e}")
        return False


async def test_agent_initialization():
    """Test agent initialization."""
    print("\nTesting agent initialization...")
    try:
        from agent import Mem0Agent
        from config import Config
        
        config = Config.from_env()
        
        # Skip if no API key
        if not config.kimi.api_key:
            print("⚠ Skipping agent test (no API key)")
            return False
        
        agent = Mem0Agent(config)
        print("✓ Agent initialized successfully")
        
        # Create a test context
        context = agent.create_context(
            agent_id="test_agent",
            user_id="test_user",
            session_id="test_session"
        )
        print(f"✓ Context created: {context.session_id}")
        
        return True
    except Exception as e:
        print(f"✗ Agent initialization error: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_memory_system():
    """Test memory system initialization."""
    print("\nTesting memory system...")
    try:
        from mem0 import Memory
        from config import Config
        
        config = Config.from_env()
        
        if config.mem0.backend == "local":
            # Test local memory initialization
            mem0_config = {
                "vector_store": {
                    "provider": "chroma",
                    "config": {
                        "collection_name": "test_collection",
                        "path": "./data/test_chroma_db"
                    }
                }
            }
            
            memory = Memory.from_config(mem0_config)
            print("✓ Local memory system initialized")
            
            # Clean up test database
            import shutil
            if os.path.exists("./data/test_chroma_db"):
                shutil.rmtree("./data/test_chroma_db")
                print("✓ Test database cleaned up")
        else:
            print("✓ Cloud memory backend configured")
        
        return True
    except Exception as e:
        print(f"✗ Memory system error: {e}")
        return False


def main():
    """Run all tests."""
    print("=" * 50)
    print("Mem0 Agent Setup Test")
    print("=" * 50)
    
    all_passed = True
    
    # Run tests
    if not test_imports():
        all_passed = False
    
    if not test_configuration():
        all_passed = False
    
    # Run async tests
    loop = asyncio.get_event_loop()
    
    if not loop.run_until_complete(test_agent_initialization()):
        all_passed = False
    
    if not loop.run_until_complete(test_memory_system()):
        all_passed = False
    
    # Summary
    print("\n" + "=" * 50)
    if all_passed:
        print("✅ All tests passed! The agent is ready to use.")
        print("\nNext steps:")
        print("1. Run quickstart examples: python quickstart.py")
        print("2. Try interactive mode: python main.py")
        print("3. Run LOCOMO benchmark: python experiment.py")
    else:
        print("⚠️ Some tests failed. Please check the configuration.")
        print("\nTroubleshooting:")
        print("1. Create .env file from env.example")
        print("2. Add your KIMI_API_KEY to .env")
        print("3. Install all requirements: pip install -r requirements.txt")
    print("=" * 50)


if __name__ == "__main__":
    main()
