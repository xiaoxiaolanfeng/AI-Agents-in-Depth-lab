"""
Main entry point for Memobase Agent with LOCOMO Benchmark
"""

import argparse
import logging
import sys
from pathlib import Path
from datetime import datetime
import json
from typing import Optional

from agent import MemobaseAgent
from locomo_benchmark import LOCOMOBenchmark, BenchmarkTask
from config import (
    KIMI_API_KEY, LOG_LEVEL, LOG_FORMAT, 
    MEMORY_DB_PATH, LOCOMO_CONFIG
)

# Configure logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


def run_interactive_mode(agent: MemobaseAgent):
    """Run agent in interactive mode"""
    print("\n" + "="*60)
    print("MEMOBASE AGENT - Interactive Mode")
    print("="*60)
    print("\nCommands:")
    print("  /help     - Show this help message")
    print("  /memory   - Show memory statistics")
    print("  /clear    - Clear working memory")
    print("  /reset    - Reset agent (keep long-term memories)")
    print("  /learn    - Trigger memory consolidation")
    print("  /exit     - Exit interactive mode")
    print("\nType your message or command:\n")
    
    while True:
        try:
            user_input = input("\n👤 You: ").strip()
            
            if not user_input:
                continue
            
            # Handle commands
            if user_input.startswith('/'):
                command = user_input.lower()
                
                if command == '/help':
                    print("\nAvailable commands:")
                    print("  /memory   - Display memory statistics")
                    print("  /clear    - Clear working memory")
                    print("  /reset    - Reset conversation (keep memories)")
                    print("  /learn    - Consolidate and learn from memories")
                    print("  /exit     - Exit interactive mode")
                    
                elif command == '/memory':
                    metrics = agent.get_performance_metrics()
                    print("\n📊 Memory Statistics:")
                    print(f"  Total memories: {metrics['total_memories']}")
                    for mem_type, count in metrics['memory_distribution'].items():
                        print(f"    • {mem_type}: {count}")
                    print(f"  Clusters created: {metrics['clusters_created']}")
                    print(f"  Conversation length: {metrics['conversation_length']}")
                    
                elif command == '/clear':
                    agent.memory_store.clear_working_memory()
                    print("✅ Working memory cleared")
                    
                elif command == '/reset':
                    agent.reset(keep_memories=True)
                    print("✅ Agent reset (memories preserved)")
                    
                elif command == '/learn':
                    print("🧠 Consolidating memories...")
                    agent.consolidate_and_learn()
                    print("✅ Memory consolidation complete")
                    
                elif command == '/exit':
                    print("\n👋 Goodbye!")
                    break
                    
                else:
                    print(f"❌ Unknown command: {command}")
                    print("   Type /help for available commands")
            
            else:
                # Process regular message
                print("\n🤖 Assistant: ", end="", flush=True)
                response = agent.process_message(user_input)
                print(response)
                
        except KeyboardInterrupt:
            print("\n\n👋 Interrupted. Goodbye!")
            break
        except Exception as e:
            logger.error(f"Error in interactive mode: {e}")
            print(f"\n❌ Error: {str(e)}")


def run_benchmark_mode(agent: MemobaseAgent, 
                      category: Optional[str] = None,
                      num_tasks: Optional[int] = None):
    """Run LOCOMO benchmark evaluation"""
    print("\n" + "="*60)
    print("LOCOMO BENCHMARK EVALUATION")
    print("="*60)
    
    # Initialize benchmark
    benchmark = LOCOMOBenchmark()
    
    # Filter tasks if category specified
    tasks = benchmark.tasks
    if category:
        tasks = [t for t in tasks if t.category == category]
        print(f"\nRunning {category} tasks only")
    
    # Limit number of tasks if specified
    if num_tasks:
        tasks = tasks[:num_tasks]
        print(f"Limited to {num_tasks} tasks")
    
    # Run benchmark
    results = benchmark.run_benchmark(agent, tasks=tasks, verbose=True)
    
    # Save results
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    results_dir = Path("benchmark_results")
    results_dir.mkdir(exist_ok=True)
    results_file = results_dir / f"locomo_results_{timestamp}.json"
    
    benchmark.save_results(results_file)
    print(f"\n📊 Results saved to: {results_file}")
    
    return results


def run_demo_mode(agent: MemobaseAgent):
    """Run demonstration scenarios"""
    print("\n" + "="*60)
    print("MEMOBASE AGENT - Demo Mode")
    print("="*60)
    
    demos = [
        {
            "name": "Memory Retention Demo",
            "messages": [
                "Remember that my favorite programming language is Python and I prefer functional programming style.",
                "What's my favorite programming language?",
                "I'm working on a new project. What programming style should I use?"
            ]
        },
        {
            "name": "Learning from Experience Demo",
            "messages": [
                "Help me debug this issue: my recursive function is causing a stack overflow.",
                "I have another recursive function problem. What should I check first?",
                "What are common causes of stack overflow in recursive functions?"
            ]
        },
        {
            "name": "Context Management Demo",
            "messages": [
                "Let's plan a machine learning project. We need data collection, preprocessing, model training, and deployment phases.",
                "What were the phases we discussed for the ML project?",
                "Add evaluation phase between training and deployment.",
                "Now summarize the complete project plan with all phases."
            ]
        }
    ]
    
    for demo in demos:
        print(f"\n\n{'='*40}")
        print(f"Demo: {demo['name']}")
        print(f"{'='*40}")
        
        for i, message in enumerate(demo['messages'], 1):
            print(f"\n[{i}/{len(demo['messages'])}] User: {message}")
            response = agent.process_message(message)
            print(f"Assistant: {response}")
            
            # Show memory stats after each interaction
            metrics = agent.get_performance_metrics()
            print(f"\n📊 Memory: {metrics['total_memories']} total, Distribution: {metrics['memory_distribution']}")
        
        # Reset for next demo but keep memories
        agent.reset(keep_memories=True)
    
    # Final memory consolidation
    print("\n\n🧠 Consolidating learnings from all demos...")
    agent.consolidate_and_learn()
    
    final_metrics = agent.get_performance_metrics()
    print(f"\n📊 Final Memory Statistics:")
    print(f"  Total memories: {final_metrics['total_memories']}")
    for mem_type, count in final_metrics['memory_distribution'].items():
        print(f"    • {mem_type}: {count}")
    print(f"  Clusters created: {final_metrics['clusters_created']}")


def run_single_task(agent: MemobaseAgent, task_query: str):
    """Run a single task"""
    print("\n" + "="*60)
    print("SINGLE TASK EXECUTION")
    print("="*60)
    
    print(f"\n📝 Task: {task_query}")
    
    result = agent.execute_task({
        "id": f"custom_{int(datetime.now().timestamp())}",
        "type": "custom",
        "query": task_query
    })
    
    print(f"\n🤖 Response: {result['response']}")
    print(f"\n📊 Execution Statistics:")
    print(f"  • Execution time: {result['execution_time']:.2f}s")
    print(f"  • Memories used: {result['memories_used']}")
    print(f"  • Memory distribution: {result['memory_stats']}")


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Memobase Agent with LOCOMO Benchmark"
    )
    
    parser.add_argument(
        "--mode",
        choices=["interactive", "benchmark", "demo", "task"],
        default="interactive",
        help="Execution mode"
    )
    
    parser.add_argument(
        "--api-key",
        type=str,
        default=KIMI_API_KEY,
        help="Kimi API key"
    )
    
    parser.add_argument(
        "--category",
        type=str,
        choices=["multi_turn_reasoning", "long_context_qa", "task_planning", 
                "knowledge_integration", "tool_usage"],
        help="Benchmark category to run (benchmark mode only)"
    )
    
    parser.add_argument(
        "--num-tasks",
        type=int,
        help="Number of benchmark tasks to run"
    )
    
    parser.add_argument(
        "--task",
        type=str,
        help="Single task query to execute (task mode only)"
    )
    
    parser.add_argument(
        "--no-memory",
        action="store_true",
        help="Start with empty memory store"
    )
    
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Initialize agent
    print("\n🚀 Initializing Memobase Agent with Kimi K3...")
    agent = MemobaseAgent(api_key=args.api_key)
    
    if args.no_memory:
        agent.reset(keep_memories=False)
        print("   Started with empty memory store")
    
    # Run selected mode
    try:
        if args.mode == "interactive":
            run_interactive_mode(agent)
            
        elif args.mode == "benchmark":
            results = run_benchmark_mode(
                agent, 
                category=args.category,
                num_tasks=args.num_tasks
            )
            
        elif args.mode == "demo":
            run_demo_mode(agent)
            
        elif args.mode == "task":
            if not args.task:
                print("❌ Error: --task argument required for task mode")
                sys.exit(1)
            run_single_task(agent, args.task)
            
    except KeyboardInterrupt:
        print("\n\n👋 Interrupted. Goodbye!")
    except Exception as e:
        logger.error(f"Fatal error: {e}", exc_info=True)
        print(f"\n❌ Fatal error: {str(e)}")
        sys.exit(1)
    
    # Final cleanup
    print("\n💾 Saving final memory state...")
    agent.memory_store._save_memories()
    print("✅ Memory state saved")


if __name__ == "__main__":
    main()
