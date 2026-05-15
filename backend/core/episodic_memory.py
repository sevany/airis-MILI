"""
AIRIS Episodic Memory System
Stores and retrieves structured meeting/conversation logs with intelligent summarization
"""
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
from datetime import datetime
import json
import os
import re

class EpisodicMemory:
    """
    Episodic memory for meetings, conversations, and important discussions
    Stores structured summaries with intelligent retrieval
    """
    
    # Summarization prompt template
    SUMMARIZATION_PROMPT = """You are a senior executive assistant. Convert this raw meeting/conversation text into a structured JSON summary.

RAW TEXT:
{text}

TAG: {tag}

Extract and return ONLY valid JSON (no markdown, no explanation) with this exact structure:
{{
  "type": "meeting|conversation|discussion",
  "topic": "brief topic (max 100 chars)",
  "summary": "comprehensive summary (200-500 chars)",
  "key_points": ["point 1", "point 2", "point 3"],
  "decisions": "key decisions made (or 'None')",
  "action_items": ["action 1", "action 2"],
  "risks": "identified risks (or 'None')",
  "opportunities": "identified opportunities (or 'None')",
  "people_mentioned": ["person 1", "person 2"],
  "companies_mentioned": ["company 1", "company 2"],
  "importance": "low|medium|high"
}}

Focus on:
- Business context and strategic implications
- Technical details if relevant
- Decision points and rationale
- Risks and opportunities
- Action items and ownership

Return ONLY the JSON object."""

    def __init__(self, persist_directory="./data/episodic_memory", ollama_client=None):
        """
        Initialize episodic memory system
        
        Args:
            persist_directory: Path to persist ChromaDB
            ollama_client: OllamaClient instance for summarization
        """
        print("🧠 Initializing Episodic Memory System...")
        
        self.ollama_client = ollama_client
        os.makedirs(persist_directory, exist_ok=True)
        
        # Initialize ChromaDB client (separate from other collections)
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Load embedding model (same as other systems for consistency)
        print("📦 Loading embedding model...")
        self.embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
        print("✓ Embedding model loaded")
        
        # Get or create collection
        try:
            self.collection = self.client.get_collection(name="airis_episodic_memory")
            print(f"✓ Loaded episodic memory collection ({self.collection.count()} entries)")
        except:
            self.collection = self.client.create_collection(
                name="airis_episodic_memory",
                metadata={"description": "AIRIS episodic memory - meetings and conversations"}
            )
            print("✓ Created new episodic memory collection")
        
        print("🧠 Episodic Memory ready!\n")
    
    def _generate_embedding(self, text):
        """Generate embedding for text"""
        return self.embedding_model.encode(text).tolist()
    
    def _extract_json_from_response(self, text):
        """
        Extract JSON from LLM response, handling markdown and other formatting
        """
        # Remove markdown code blocks
        text = re.sub(r'```json\s*', '', text)
        text = re.sub(r'```\s*', '', text)
        
        # Find JSON object
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError as e:
                print(f"⚠️ JSON decode error: {e}")
                return None
        return None
    
    def summarize_memory(self, text, tag="General"):
        """
        Use Ollama to summarize raw text into structured JSON
        
        Args:
            text: Raw conversation/meeting text
            tag: Tag for categorization (PRSB, Petronas, etc.)
            
        Returns:
            Structured dictionary or None if failed
        """
        if not self.ollama_client:
            print("❌ Ollama client not available for summarization")
            return None
        
        print(f"📝 Summarizing memory (tag: {tag})...")
        
        # Format prompt
        prompt = self.SUMMARIZATION_PROMPT.format(text=text, tag=tag)
        
        try:
            # Call Ollama for summarization
            messages = [{"role": "user", "content": prompt}]
            response = self.ollama_client.chat(messages, stream=False)
            
            if not response or 'message' not in response:
                print("❌ No response from Ollama")
                return None
            
            response_text = response['message']['content']
            
            # Extract JSON from response
            structured = self._extract_json_from_response(response_text)
            
            if structured:
                print("✓ Successfully structured memory")
                return structured
            else:
                print("⚠️ Failed to extract valid JSON, using fallback")
                # Fallback to basic structure
                return {
                    "type": "conversation",
                    "topic": f"{tag} discussion",
                    "summary": text[:500],
                    "key_points": [],
                    "decisions": "None",
                    "action_items": [],
                    "risks": "None",
                    "opportunities": "None",
                    "people_mentioned": [],
                    "companies_mentioned": [],
                    "importance": "medium"
                }
        
        except Exception as e:
            print(f"❌ Summarization error: {e}")
            return None
    
    def store_memory(self, text, tag="General", structured_data=None):
        """
        Store episodic memory
        
        Args:
            text: Raw text (if structured_data is None, will be summarized)
            tag: Tag for categorization
            structured_data: Pre-structured data (optional, bypasses summarization)
            
        Returns:
            Memory ID or None if failed
        """
        # Summarize if not already structured
        if structured_data is None:
            structured_data = self.summarize_memory(text, tag)
            if structured_data is None:
                return None
        
        # Generate unique ID
        memory_id = f"episodic_{tag}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        
        # Prepare searchable text (for embedding)
        searchable_text = f"""
        Topic: {structured_data.get('topic', '')}
        Summary: {structured_data.get('summary', '')}
        Key Points: {', '.join(structured_data.get('key_points', []))}
        Decisions: {structured_data.get('decisions', '')}
        Risks: {structured_data.get('risks', '')}
        Opportunities: {structured_data.get('opportunities', '')}
        """
        
        # Generate embedding
        embedding = self._generate_embedding(searchable_text)
        
        # Prepare metadata
        metadata = {
            "tag": tag,
            "type": structured_data.get('type', 'conversation'),
            "topic": structured_data.get('topic', '')[:100],  # ChromaDB string limit
            "importance": structured_data.get('importance', 'medium'),
            "timestamp": datetime.now().isoformat(),
            "has_decisions": "yes" if structured_data.get('decisions', 'None') != 'None' else "no",
            "has_risks": "yes" if structured_data.get('risks', 'None') != 'None' else "no",
            "people_count": len(structured_data.get('people_mentioned', [])),
            "companies_count": len(structured_data.get('companies_mentioned', []))
        }
        
        # Store full structured data as document
        document = json.dumps(structured_data, ensure_ascii=False)
        
        # Add to ChromaDB
        self.collection.add(
            ids=[memory_id],
            embeddings=[embedding],
            documents=[document],
            metadatas=[metadata]
        )
        
        print(f"💾 Stored episodic memory: {memory_id}")
        print(f"   Topic: {structured_data.get('topic', '')}")
        print(f"   Importance: {structured_data.get('importance', 'medium')}")
        
        return memory_id
    
    def retrieve_memory(self, query, n_results=3, tag_filter=None, importance_filter=None):
        """
        Retrieve relevant episodic memories
        
        Args:
            query: Search query
            n_results: Number of results to return
            tag_filter: Filter by tag (e.g., "PRSB", "Petronas")
            importance_filter: Filter by importance ("low", "medium", "high")
            
        Returns:
            List of memory dictionaries
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        # Build where filter
        where_filter = {}
        if tag_filter:
            where_filter["tag"] = tag_filter
        if importance_filter:
            where_filter["importance"] = importance_filter
        
        # Query ChromaDB
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where_filter if where_filter else None
        )
        
        memories = []
        
        if results['documents'] and results['documents'][0]:
            for i in range(len(results['documents'][0])):
                try:
                    structured = json.loads(results['documents'][0][i])
                    memories.append({
                        'structured': structured,
                        'metadata': results['metadatas'][0][i],
                        'distance': results['distances'][0][i] if 'distances' in results else None
                    })
                except json.JSONDecodeError:
                    continue
        
        print(f"🔍 Retrieved {len(memories)} episodic memories")
        return memories
    
    def get_context_for_query(self, query, max_memories=3):
        """
        Get formatted context from episodic memories for a query
        
        Args:
            query: User query
            max_memories: Max memories to retrieve
            
        Returns:
            Formatted context string
        """
        memories = self.retrieve_memory(query, n_results=max_memories)
        
        if not memories:
            return ""
        
        context_parts = []
        context_parts.append("=== RELEVANT PAST MEETINGS & DISCUSSIONS ===")
        
        for mem in memories:
            structured = mem['structured']
            metadata = mem['metadata']
            
            context_parts.append(f"\n[{metadata['tag']} - {metadata['type'].upper()}]")
            context_parts.append(f"Topic: {structured.get('topic', 'N/A')}")
            context_parts.append(f"Summary: {structured.get('summary', 'N/A')}")
            
            if structured.get('key_points'):
                context_parts.append("Key Points:")
                for point in structured['key_points'][:3]:  # Top 3 points
                    context_parts.append(f"  • {point}")
            
            if structured.get('decisions', 'None') != 'None':
                context_parts.append(f"Decisions: {structured['decisions']}")
            
            if structured.get('risks', 'None') != 'None':
                context_parts.append(f"Risks: {structured['risks']}")
            
            context_parts.append(f"Importance: {metadata['importance'].upper()}")
        
        context_parts.append("=== END EPISODIC MEMORY ===")
        
        return "\n".join(context_parts)
    
    def get_memories_by_tag(self, tag, limit=10):
        """Get all memories with a specific tag"""
        all_data = self.collection.get(where={"tag": tag})
        
        memories = []
        if all_data['documents']:
            for i, doc in enumerate(all_data['documents'][:limit]):
                try:
                    structured = json.loads(doc)
                    memories.append({
                        'structured': structured,
                        'metadata': all_data['metadatas'][i]
                    })
                except json.JSONDecodeError:
                    continue
        
        return memories
    
    def get_all_tags(self):
        """Get list of all unique tags"""
        all_data = self.collection.get()
        tags = set()
        
        if all_data['metadatas']:
            for meta in all_data['metadatas']:
                if 'tag' in meta:
                    tags.add(meta['tag'])
        
        return sorted(list(tags))
    
    def get_stats(self):
        """Get episodic memory statistics"""
        all_data = self.collection.get()
        
        stats = {
            "total_memories": len(all_data['ids']) if all_data['ids'] else 0,
            "tags": {},
            "importance_distribution": {"low": 0, "medium": 0, "high": 0},
            "with_decisions": 0,
            "with_risks": 0
        }
        
        if all_data['metadatas']:
            for meta in all_data['metadatas']:
                # Count by tag
                tag = meta.get('tag', 'Unknown')
                stats['tags'][tag] = stats['tags'].get(tag, 0) + 1
                
                # Count importance
                importance = meta.get('importance', 'medium')
                if importance in stats['importance_distribution']:
                    stats['importance_distribution'][importance] += 1
                
                # Count decisions/risks
                if meta.get('has_decisions') == 'yes':
                    stats['with_decisions'] += 1
                if meta.get('has_risks') == 'yes':
                    stats['with_risks'] += 1
        
        return stats
    
    def delete_memory(self, memory_id):
        """Delete a specific memory"""
        try:
            self.collection.delete(ids=[memory_id])
            print(f"🗑️ Deleted memory: {memory_id}")
            return True
        except Exception as e:
            print(f"❌ Delete error: {e}")
            return False
    
    def health_check(self):
        """Check if episodic memory is working"""
        try:
            count = self.collection.count()
            stats = self.get_stats()
            return True, f"✓ Episodic Memory ready ({count} memories, {len(stats['tags'])} tags)"
        except Exception as e:
            return False, f"✗ Episodic Memory error: {str(e)}"