"""
Memobase Agent Implementation with Kimi K3 Model
Advanced memory management for LOCOMO benchmark
"""

import json
import logging
import time
import hashlib
import pickle
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from openai import OpenAI

from config import (
    KIMI_API_KEY, KIMI_BASE_URL, KIMI_MODEL,
    MODEL_TEMPERATURE, MODEL_MAX_TOKENS, MODEL_TOP_P,
    MEMOBASE_CONFIG, MEMORY_DB_PATH, AGENT_CONFIG,
    MAX_MEMORY_ENTRIES, MEMORY_COMPRESSION_THRESHOLD,
    LOG_LEVEL, LOG_FORMAT
)


def _reasoning_safe_temperature(model, requested=1.0):
    """Reasoning models (Kimi K3, GPT-5, ...) only accept temperature=1.
    Return 1 for those; otherwise the requested value so non-reasoning
    providers (Doubao, DeepSeek, older Moonshot) are unchanged."""
    m = str(model or "").lower().replace("/", "-")
    return 1 if ("kimi-k3" in m or "gpt-5" in m) else requested


# Configure logging
logging.basicConfig(level=LOG_LEVEL, format=LOG_FORMAT)
logger = logging.getLogger(__name__)


@dataclass
class Memory:
    """Represents a single memory entry"""
    id: str
    type: str  # episodic, semantic, procedural, working
    content: Any
    embedding: Optional[List[float]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.now)
    accessed_at: datetime = field(default_factory=datetime.now)
    access_count: int = 0
    importance_score: float = 1.0
    decay_rate: float = 0.1
    
    def __post_init__(self):
        if not self.id:
            # Generate unique ID based on content
            content_str = json.dumps(self.content, sort_keys=True)
            self.id = hashlib.md5(content_str.encode()).hexdigest()[:12]
    
    def access(self):
        """Update access statistics"""
        self.accessed_at = datetime.now()
        self.access_count += 1
        # Increase importance with access
        self.importance_score = min(10.0, self.importance_score * 1.1)
    
    def decay(self):
        """Apply time-based decay to importance"""
        time_since_access = (datetime.now() - self.accessed_at).total_seconds() / 3600
        self.importance_score *= (1 - self.decay_rate * min(1, time_since_access / 24))
        self.importance_score = max(0.1, self.importance_score)


@dataclass
class MemoryCluster:
    """Represents a cluster of related memories"""
    id: str
    memories: List[Memory]
    summary: Optional[str] = None
    centroid_embedding: Optional[List[float]] = None
    created_at: datetime = field(default_factory=datetime.now)
    
    def add_memory(self, memory: Memory):
        """Add a memory to the cluster"""
        self.memories.append(memory)
        # TODO: Update centroid embedding
    
    def compress(self) -> str:
        """Compress cluster into a summary"""
        if not self.summary:
            # Create summary from memories
            contents = [m.content for m in self.memories]
            self.summary = f"Cluster of {len(self.memories)} related memories: {contents[:3]}..."
        return self.summary


class MemoryStore:
    """Manages different types of memories with persistence"""
    
    def __init__(self, db_path: Path = MEMORY_DB_PATH):
        self.db_path = db_path
        self.memories: Dict[str, List[Memory]] = defaultdict(list)
        self.clusters: List[MemoryCluster] = []
        self.embeddings_cache: Dict[str, List[float]] = {}
        self._load_memories()
        logger.info(f"Initialized MemoryStore at {db_path}")
    
    def _load_memories(self):
        """Load memories from persistent storage"""
        memory_file = self.db_path / "memories.pkl"
        if memory_file.exists():
            try:
                with open(memory_file, 'rb') as f:
                    data = pickle.load(f)
                    self.memories = data.get('memories', defaultdict(list))
                    self.clusters = data.get('clusters', [])
                    logger.info(f"Loaded {sum(len(m) for m in self.memories.values())} memories")
            except Exception as e:
                logger.error(f"Failed to load memories: {e}")
    
    def _save_memories(self):
        """Save memories to persistent storage"""
        memory_file = self.db_path / "memories.pkl"
        try:
            with open(memory_file, 'wb') as f:
                pickle.dump({
                    'memories': dict(self.memories),
                    'clusters': self.clusters
                }, f)
            logger.debug("Saved memories to disk")
        except Exception as e:
            logger.error(f"Failed to save memories: {e}")
    
    def add_memory(self, memory_type: str, content: Any, 
                   metadata: Optional[Dict] = None,
                   importance: float = 1.0) -> Memory:
        """Add a new memory"""
        memory = Memory(
            id="",  # Will be auto-generated
            type=memory_type,
            content=content,
            metadata=metadata or {},
            importance_score=importance
        )
        
        self.memories[memory_type].append(memory)
        
        # Apply compression if needed
        if len(self.memories[memory_type]) > MEMORY_COMPRESSION_THRESHOLD:
            self._compress_memories(memory_type)
        
        self._save_memories()
        logger.debug(f"Added {memory_type} memory: {memory.id}")
        return memory
    
    def get_memories(self, memory_type: Optional[str] = None,
                     limit: int = 10,
                     min_importance: float = 0.5) -> List[Memory]:
        """Retrieve memories, optionally filtered by type and importance"""
        if memory_type:
            memories = self.memories.get(memory_type, [])
        else:
            memories = [m for mlist in self.memories.values() for m in mlist]
        
        # Filter by importance and sort by relevance
        memories = [m for m in memories if m.importance_score >= min_importance]
        memories.sort(key=lambda m: (m.importance_score, m.access_count), reverse=True)
        
        # Update access stats
        for memory in memories[:limit]:
            memory.access()
        
        return memories[:limit]
    
    def search_memories(self, query: str, limit: int = 5) -> List[Memory]:
        """Search memories by content similarity"""
        results = []
        query_lower = query.lower()
        
        for memory_list in self.memories.values():
            for memory in memory_list:
                # Simple text matching (would use embeddings in production)
                content_str = str(memory.content).lower()
                if query_lower in content_str:
                    score = content_str.count(query_lower) * memory.importance_score
                    results.append((score, memory))
        
        results.sort(key=lambda x: x[0], reverse=True)
        
        # Update access stats
        for _, memory in results[:limit]:
            memory.access()
        
        return [m for _, m in results[:limit]]
    
    def _compress_memories(self, memory_type: str):
        """Compress old memories to save space"""
        memories = self.memories[memory_type]
        if len(memories) <= MEMORY_COMPRESSION_THRESHOLD:
            return
        
        # Sort by importance and recency
        memories.sort(key=lambda m: (m.importance_score, m.accessed_at.timestamp()))
        
        # Keep top memories, compress others
        to_keep = memories[-MAX_MEMORY_ENTRIES//2:]
        to_compress = memories[:-MAX_MEMORY_ENTRIES//2]
        
        if to_compress:
            # Create a cluster from compressed memories
            cluster = MemoryCluster(
                id=hashlib.md5(f"{memory_type}_{datetime.now()}".encode()).hexdigest()[:12],
                memories=to_compress
            )
            cluster.compress()
            self.clusters.append(cluster)
            
            # Replace with compressed version
            compressed_memory = Memory(
                id=cluster.id,
                type=memory_type,
                content=cluster.summary,
                metadata={"cluster_id": cluster.id, "compressed_count": len(to_compress)},
                importance_score=sum(m.importance_score for m in to_compress) / len(to_compress)
            )
            
            self.memories[memory_type] = [compressed_memory] + to_keep
            logger.info(f"Compressed {len(to_compress)} {memory_type} memories into cluster {cluster.id}")
    
    def consolidate_memories(self):
        """Consolidate and reorganize memories for efficiency"""
        for memory_type in self.memories:
            memories = self.memories[memory_type]
            
            # Apply decay to all memories
            for memory in memories:
                memory.decay()
            
            # Remove very low importance memories
            self.memories[memory_type] = [
                m for m in memories if m.importance_score > 0.1
            ]
        
        self._save_memories()
        logger.info("Consolidated memories")
    
    def clear_working_memory(self):
        """Clear working memory (short-term)"""
        self.memories['working'] = []
        logger.debug("Cleared working memory")


class MemobaseAgent:
    """
    Advanced agent with Memobase memory management for LOCOMO benchmark
    """
    
    def __init__(self, api_key: str = KIMI_API_KEY):
        """Initialize the Memobase agent"""
        self.client = OpenAI(
            api_key=api_key,
            base_url=KIMI_BASE_URL
        )
        self.model = KIMI_MODEL
        self.memory_store = MemoryStore()
        self.conversation_history = []
        self.current_task = None
        self.task_context = {}
        
        # Initialize system prompt
        self._init_system_prompt()
        logger.info(f"Initialized MemobaseAgent with model {self.model}")
    
    def _init_system_prompt(self):
        """Initialize the system prompt with memory capabilities"""
        self.system_prompt = """You are an advanced AI agent with sophisticated memory management capabilities.

You have access to multiple types of memory:
1. **Episodic Memory**: Specific experiences and events from tasks
2. **Semantic Memory**: General knowledge and facts
3. **Procedural Memory**: Learned procedures and problem-solving patterns
4. **Working Memory**: Current task context and temporary information

Memory Management Guidelines:
- Store important information for future reference
- Retrieve relevant memories when solving new problems
- Learn from past experiences to improve performance
- Compress and consolidate memories to maintain efficiency
- Use procedural memories to apply learned strategies

Your goal is to complete tasks efficiently while learning and adapting from experience.
When you encounter similar problems, use your memories to solve them more effectively.

Always think step-by-step and use your memory system strategically."""
    
    def _store_interaction(self, role: str, content: str, memory_type: str = "episodic"):
        """Store an interaction in memory"""
        self.memory_store.add_memory(
            memory_type=memory_type,
            content={
                "role": role,
                "content": content,
                "task": self.current_task,
                "timestamp": datetime.now().isoformat()
            },
            metadata={
                "task_id": self.current_task,
                "turn": len(self.conversation_history)
            }
        )
    
    def _retrieve_relevant_memories(self, query: str, limit: int = 5) -> List[Memory]:
        """Retrieve memories relevant to current query"""
        # Search across all memory types
        relevant_memories = []
        
        # Get recent episodic memories
        episodic = self.memory_store.get_memories("episodic", limit=limit//2)
        relevant_memories.extend(episodic)
        
        # Search for similar content
        searched = self.memory_store.search_memories(query, limit=limit//2)
        relevant_memories.extend(searched)
        
        # Get procedural memories if task-related
        if "solve" in query.lower() or "how" in query.lower():
            procedural = self.memory_store.get_memories("procedural", limit=2)
            relevant_memories.extend(procedural)
        
        # Remove duplicates
        seen = set()
        unique_memories = []
        for memory in relevant_memories:
            if memory.id not in seen:
                seen.add(memory.id)
                unique_memories.append(memory)
        
        return unique_memories[:limit]
    
    def _format_memories_for_context(self, memories: List[Memory]) -> str:
        """Format memories for inclusion in context"""
        if not memories:
            return ""
        
        formatted = "\n=== Relevant Memories ===\n"
        for memory in memories:
            formatted += f"[{memory.type.upper()}] (importance: {memory.importance_score:.2f})\n"
            if isinstance(memory.content, dict):
                formatted += json.dumps(memory.content, indent=2)
            else:
                formatted += str(memory.content)
            formatted += "\n---\n"
        
        return formatted
    
    def _learn_from_outcome(self, task: str, approach: str, outcome: str, success: bool):
        """Learn from task outcomes and store procedural knowledge"""
        # Store the learning as procedural memory
        self.memory_store.add_memory(
            memory_type="procedural",
            content={
                "task_pattern": task,
                "approach": approach,
                "outcome": outcome,
                "success": success,
                "learned_at": datetime.now().isoformat()
            },
            importance=2.0 if success else 1.0,
            metadata={"task_id": self.current_task}
        )
        
        if success:
            logger.info(f"Learned successful approach for task type: {task}")
        else:
            logger.info(f"Learned from failure in task type: {task}")
    
    def process_message(self, message: str, task_id: Optional[str] = None) -> str:
        """
        Process a message with memory-aware reasoning
        
        Args:
            message: User message to process
            task_id: Optional task identifier for context
            
        Returns:
            Agent's response
        """
        self.current_task = task_id or f"task_{int(time.time())}"
        
        # Store the query in working memory
        self.memory_store.add_memory(
            memory_type="working",
            content=message,
            metadata={"task_id": self.current_task}
        )
        
        # Retrieve relevant memories
        relevant_memories = self._retrieve_relevant_memories(message)
        memory_context = self._format_memories_for_context(relevant_memories)
        
        # Build messages with memory context
        messages = [
            {"role": "system", "content": self.system_prompt}
        ]
        
        if memory_context:
            messages.append({
                "role": "system",
                "content": memory_context
            })
        
        # Add conversation history
        messages.extend(self.conversation_history)
        messages.append({"role": "user", "content": message})
        
        try:
            # Call Kimi K3 model
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=_reasoning_safe_temperature(self.model, MODEL_TEMPERATURE),
                max_tokens=MODEL_MAX_TOKENS,
                top_p=MODEL_TOP_P
            )
            
            assistant_response = response.choices[0].message.content
            
            # Store the interaction in episodic memory
            self._store_interaction("user", message)
            self._store_interaction("assistant", assistant_response)
            
            # Update conversation history
            self.conversation_history.append({"role": "user", "content": message})
            self.conversation_history.append({"role": "assistant", "content": assistant_response})
            
            # Keep conversation history manageable
            if len(self.conversation_history) > 20:
                # Move old conversations to episodic memory and compress
                old_convs = self.conversation_history[:10]
                for conv in old_convs:
                    self.memory_store.add_memory(
                        memory_type="episodic",
                        content=conv,
                        importance=0.5
                    )
                self.conversation_history = self.conversation_history[10:]
            
            return assistant_response
            
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            return f"Error: {str(e)}"
    
    def execute_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a LOCOMO benchmark task
        
        Args:
            task: Task dictionary with 'id', 'type', 'query', and optional 'context'
            
        Returns:
            Result dictionary with 'response', 'memories_used', 'execution_time'
        """
        start_time = time.time()
        task_id = task.get('id', f"task_{int(time.time())}")
        task_type = task.get('type', 'unknown')
        query = task['query']
        context = task.get('context', '')
        
        self.current_task = task_id
        
        # Check for similar past tasks in procedural memory
        similar_tasks = self.memory_store.search_memories(f"{task_type} {query[:50]}", limit=3)
        
        # Build enhanced query with context
        enhanced_query = query
        if context:
            enhanced_query = f"Context: {context}\n\nTask: {query}"
        
        # Process the task
        response = self.process_message(enhanced_query, task_id)
        
        # Extract approach and outcome for learning
        approach = f"Used {len(similar_tasks)} similar memories"
        outcome = response[:100]  # First 100 chars as outcome summary
        
        # Learn from this task
        self._learn_from_outcome(
            task=task_type,
            approach=approach,
            outcome=outcome,
            success=True  # Would be determined by evaluation
        )
        
        execution_time = time.time() - start_time
        
        return {
            "task_id": task_id,
            "response": response,
            "memories_used": len(similar_tasks),
            "execution_time": execution_time,
            "memory_stats": {
                "episodic": len(self.memory_store.memories.get('episodic', [])),
                "semantic": len(self.memory_store.memories.get('semantic', [])),
                "procedural": len(self.memory_store.memories.get('procedural', [])),
                "working": len(self.memory_store.memories.get('working', []))
            }
        }
    
    def consolidate_and_learn(self):
        """Consolidate memories and extract learnings"""
        logger.info("Starting memory consolidation...")
        
        # Consolidate memories
        self.memory_store.consolidate_memories()
        
        # Extract patterns from episodic memories
        episodic_memories = self.memory_store.get_memories('episodic', limit=50)
        
        # Group by task type and extract patterns
        task_patterns = defaultdict(list)
        for memory in episodic_memories:
            if isinstance(memory.content, dict):
                task = memory.content.get('task', 'unknown')
                task_patterns[task].append(memory)
        
        # Create procedural memories from patterns
        for task_type, memories in task_patterns.items():
            if len(memories) >= 3:  # Need multiple examples to learn
                # Extract common approach
                pattern = {
                    "task_type": task_type,
                    "successful_approaches": [],
                    "common_challenges": [],
                    "learned_from": len(memories)
                }
                
                self.memory_store.add_memory(
                    memory_type="procedural",
                    content=pattern,
                    importance=2.0,
                    metadata={"consolidation_run": datetime.now().isoformat()}
                )
        
        # Clear working memory
        self.memory_store.clear_working_memory()
        
        logger.info("Memory consolidation complete")
    
    def reset(self, keep_memories: bool = True):
        """Reset the agent state"""
        self.conversation_history = []
        self.current_task = None
        self.task_context = {}
        
        if not keep_memories:
            self.memory_store = MemoryStore()
        else:
            # Only clear working memory
            self.memory_store.clear_working_memory()
        
        logger.info(f"Agent reset (memories kept: {keep_memories})")
    
    def get_performance_metrics(self) -> Dict[str, Any]:
        """Get agent performance metrics"""
        memory_stats = {
            memory_type: len(memories)
            for memory_type, memories in self.memory_store.memories.items()
        }
        
        total_memories = sum(memory_stats.values())
        cluster_count = len(self.memory_store.clusters)
        
        return {
            "total_memories": total_memories,
            "memory_distribution": memory_stats,
            "clusters_created": cluster_count,
            "conversation_length": len(self.conversation_history),
            "current_task": self.current_task
        }
