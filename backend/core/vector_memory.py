"""
AIRIS Vector Memory System
Uses ChromaDB for long-term conversation memory with semantic search
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from datetime import datetime
import json
import os
import hashlib

class VectorMemory:
    """
    ChromaDB-based vector memory for AIRIS
    Stores conversations with semantic search capability
    """
    
    def __init__(self, persist_directory="./data/memory"):
        """
        Initialize ChromaDB with sentence-transformers embeddings
        
        Args:
            persist_directory: Where to store ChromaDB data
        """
        print("🧠 Initializing AIRIS Vector Memory...")
        
        # Create persist directory
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client (persistent)
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Load embedding model (CPU-based)
        print("📦 Loading embedding model (all-MiniLM-L6-v2)...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Embedding model loaded")
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(
                name="airis_conversations",
            )
            print(f"✓ Loaded existing collection ({self.collection.count()} memories)")
        except:
            self.collection = self.client.create_collection(
                name="airis_conversations",
                metadata={"description": "AIRIS conversation memory"}
            )
            print("✓ Created new memory collection")
        
        print("🧠 Vector Memory ready!\n")
    
    def _generate_embedding(self, text):
        """Generate embedding vector for text using sentence-transformers"""
        return self.embedding_model.encode(text).tolist()
    
    def _generate_id(self, user_msg, assistant_msg, timestamp):
        """Generate unique ID for conversation turn"""
        combined = f"{timestamp}_{user_msg}_{assistant_msg}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def add_conversation(self, user_message, assistant_response, metadata=None):
        """
        Store a conversation turn in memory
        
        Args:
            user_message: What Myra said
            assistant_response: What AIRIS replied
            metadata: Optional dict with context (topic, sentiment, etc.)
            
        Returns:
            Memory ID
        """
        timestamp = datetime.now().isoformat()
        
        # Combine user + assistant for context embedding
        conversation_text = f"User: {user_message}\nAIRIS: {assistant_response}"
        
        # Generate embedding
        embedding = self._generate_embedding(conversation_text)
        
        # Prepare metadata
        meta = {
            "timestamp": timestamp,
            "user_message": user_message,
            "assistant_response": assistant_response,
            "conversation_length": len(user_message) + len(assistant_response)
        }
        
        # Add custom metadata if provided
        if metadata:
            meta.update(metadata)
        
        # Generate unique ID
        memory_id = self._generate_id(user_message, assistant_response, timestamp)
        
        # Store in ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[conversation_text],
            metadatas=[meta]
        )
        
        print(f"💾 Memory stored: {memory_id[:8]}...")
        return memory_id
    
    def search_memory(self, query, n_results=5, filter_metadata=None, date_range=None):
        """
        Search for relevant memories using semantic similarity
        
        Args:
            query: Search query (natural language)
            n_results: How many results to return
            filter_metadata: Optional dict to filter results
            date_range: Optional tuple (start_date, end_date) in ISO format
            
        Returns:
            List of relevant conversation memories
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Build where filter for date range
        where_filter = filter_metadata or {}
        
        if date_range:
            start_date, end_date = date_range
            # ChromaDB metadata filtering
            where_filter = {
                "$and": [
                    {"timestamp": {"$gte": start_date}},
                    {"timestamp": {"$lte": end_date}}
                ]
            }
        
        # Search ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        # Format results
        memories = []
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                memories.append({
                    'id': results['ids'][0][i],
                    'conversation': results['documents'][0][i],
                    'metadata': results['metadatas'][0][i],
                    'distance': results['distances'][0][i] if 'distances' in results else None
                })
        
        print(f"🔍 Found {len(memories)} relevant memories for: '{query}'")
        return memories
    
    def get_memories_by_date(self, target_date):
        """
        Get all memories from a specific date
        
        Args:
            target_date: Date string in YYYY-MM-DD format
            
        Returns:
            List of memories from that date
        """
        from datetime import datetime, timedelta
        
        # Parse date
        date_obj = datetime.fromisoformat(target_date)
        
        # Create date range (entire day)
        start = date_obj.isoformat()
        end = (date_obj + timedelta(days=1)).isoformat()
        
        # Get all memories
        all_memories = self.collection.get()
        
        if not all_memories['metadatas']:
            return []
        
        # Filter by date
        memories_on_date = []
        for i in range(len(all_memories['ids'])):
            timestamp = all_memories['metadatas'][i]['timestamp']
            if start <= timestamp < end:
                memories_on_date.append({
                    'id': all_memories['ids'][i],
                    'conversation': all_memories['documents'][i],
                    'metadata': all_memories['metadatas'][i],
                    'timestamp': timestamp
                })
        
        # Sort by timestamp
        memories_on_date.sort(key=lambda x: x['timestamp'])
        
        print(f"📅 Found {len(memories_on_date)} memories on {target_date}")
        return memories_on_date
    
    def get_memories_by_date_range(self, start_date, end_date):
        """
        Get all memories within a date range
        
        Args:
            start_date: Start date in YYYY-MM-DD format
            end_date: End date in YYYY-MM-DD format
            
        Returns:
            Dict grouped by date
        """
        from datetime import datetime, timedelta
        from collections import defaultdict
        
        # Get all memories
        all_memories = self.collection.get()
        
        if not all_memories['metadatas']:
            return {}
        
        # Parse dates
        start = datetime.fromisoformat(start_date).isoformat()
        end = (datetime.fromisoformat(end_date) + timedelta(days=1)).isoformat()
        
        # Group by date
        grouped = defaultdict(list)
        
        for i in range(len(all_memories['ids'])):
            timestamp = all_memories['metadatas'][i]['timestamp']
            
            if start <= timestamp < end:
                # Extract date only (YYYY-MM-DD)
                date_only = timestamp.split('T')[0]
                
                grouped[date_only].append({
                    'id': all_memories['ids'][i],
                    'conversation': all_memories['documents'][i],
                    'metadata': all_memories['metadatas'][i],
                    'timestamp': timestamp
                })
        
        # Sort each day's memories by timestamp
        for date in grouped:
            grouped[date].sort(key=lambda x: x['timestamp'])
        
        print(f"📅 Found memories across {len(grouped)} days")
        return dict(grouped)
    
    def get_recent_conversations(self, n=10):
        """
        Get N most recent conversations
        
        Args:
            n: Number of recent conversations to retrieve
            
        Returns:
            List of recent memories (sorted by timestamp)
        """
        # Get all memories
        all_memories = self.collection.get()
        
        if not all_memories['metadatas']:
            return []
        
        # Sort by timestamp (descending)
        memories_with_time = [
            {
                'id': all_memories['ids'][i],
                'conversation': all_memories['documents'][i],
                'metadata': all_memories['metadatas'][i],
                'timestamp': all_memories['metadatas'][i]['timestamp']
            }
            for i in range(len(all_memories['ids']))
        ]
        
        sorted_memories = sorted(
            memories_with_time,
            key=lambda x: x['timestamp'],
            reverse=True
        )
        
        return sorted_memories[:n]
    
    def get_context_for_query(self, query, max_context_length=2000):
        """
        Get relevant context from memory for a user query
        Useful for RAG (Retrieval Augmented Generation)
        
        Args:
            query: User's current message
            max_context_length: Max chars of context to return
            
        Returns:
            String of relevant past conversations
        """
        # Search for relevant memories
        relevant_memories = self.search_memory(query, n_results=5)
        
        if not relevant_memories:
            return ""
        
        # Build context string
        context_parts = []
        total_length = 0
        
        for memory in relevant_memories:
            conversation = memory['conversation']
            timestamp = memory['metadata']['timestamp']
            
            # Format: [Date] conversation
            formatted = f"[{timestamp.split('T')[0]}] {conversation}"
            
            if total_length + len(formatted) > max_context_length:
                break
            
            context_parts.append(formatted)
            total_length += len(formatted)
        
        context = "\n\n".join(context_parts)
        print(f"📋 Generated {len(context)} chars of context")
        return context
    
    def delete_memory(self, memory_id):
        """Delete a specific memory by ID"""
        self.collection.delete(ids=[memory_id])
        print(f"🗑️ Deleted memory: {memory_id}")
    
    def clear_all_memories(self):
        """⚠️ DELETE ALL MEMORIES - Use with caution!"""
        count = self.collection.count()
        self.client.delete_collection("airis_conversations")
        self.collection = self.client.create_collection(
            name="airis_conversations",
            metadata={"description": "AIRIS conversation memory"}
        )
        print(f"🗑️ Cleared {count} memories")
    
    def get_stats(self):
        """Get memory statistics"""
        total = self.collection.count()
        
        if total == 0:
            return {
                'total_memories': 0,
                'oldest_memory': None,
                'newest_memory': None
            }
        
        # Get all to find oldest/newest
        all_memories = self.collection.get()
        timestamps = [m['timestamp'] for m in all_memories['metadatas']]
        
        return {
            'total_memories': total,
            'oldest_memory': min(timestamps) if timestamps else None,
            'newest_memory': max(timestamps) if timestamps else None
        }
    
    def export_memories(self, output_file="memory_export.json"):
        """Export all memories to JSON file"""
        all_memories = self.collection.get()
        
        export_data = {
            'exported_at': datetime.now().isoformat(),
            'total_memories': len(all_memories['ids']),
            'memories': [
                {
                    'id': all_memories['ids'][i],
                    'conversation': all_memories['documents'][i],
                    'metadata': all_memories['metadatas'][i]
                }
                for i in range(len(all_memories['ids']))
            ]
        }
        
        with open(output_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"📦 Exported {len(all_memories['ids'])} memories to {output_file}")
        return output_file
    
    def health_check(self):
        """Check if memory system is working"""
        try:
            count = self.collection.count()
            return True, f"✓ Vector Memory healthy ({count} memories stored)"
        except Exception as e:
            return False, f"✗ Vector Memory error: {str(e)}"

# For testing
if __name__ == "__main__":
    print("="*60)
    print("AIRIS Vector Memory Test")
    print("="*60)
    
    # Initialize
    memory = VectorMemory()
    
    # Test: Add conversation
    print("\n1. Adding test conversation...")
    memory.add_conversation(
        user_message="What's the gold price today?",
        assistant_response="The current gold price is $4538.34, up 0.5% from yesterday.",
        metadata={"topic": "gold_price"}
    )
    
    # Test: Search
    print("\n2. Searching for 'gold trading'...")
    results = memory.search_memory("gold trading strategies", n_results=3)
    for r in results:
        print(f"  - {r['conversation'][:100]}...")
    
    # Test: Stats
    print("\n3. Memory stats:")
    stats = memory.get_stats()
    print(f"  Total memories: {stats['total_memories']}")
    
    print("\n" + "="*60)
    print("✓ Memory system test complete!")
    print("="*60)