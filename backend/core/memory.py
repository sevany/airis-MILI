"""
Memory Module - SQLite Backend
Stores conversation history and basic context
Phase 1: Simple conversation memory
Phase 2: Will migrate to ChromaDB for vector search
"""
import sqlite3
import json
import os
from datetime import datetime
from backend.config import Config

class Memory:
    """SQLite-based conversation memory for AIRIS"""
    
    def __init__(self, db_path=None):
        self.db_path = db_path or Config.DATABASE_PATH
        self._ensure_directory()
        self._init_database()
    
    def _ensure_directory(self):
        """Create data directory if it doesn't exist"""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir)
    
    def _init_database(self):
        """Initialize database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_message TEXT NOT NULL,
                assistant_message TEXT NOT NULL,
                emotional_state TEXT DEFAULT 'neutral',
                metadata TEXT
            )
        ''')
        
        # User context table (for storing persistent facts about Myra)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_context (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                key TEXT NOT NULL,
                value TEXT NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(category, key)
            )
        ''')
        
        conn.commit()
        conn.close()
        print(f"✓ Memory database initialized: {self.db_path}")
    
    def add_conversation(self, user_message, assistant_message, emotional_state="neutral", metadata=None):
        """
        Store a conversation turn
        
        Args:
            user_message: What Myra said
            assistant_message: What AIRIS responded
            emotional_state: Current emotional state
            metadata: Optional dict with additional context
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (user_message, assistant_message, emotional_state, metadata)
            VALUES (?, ?, ?, ?)
        ''', (
            user_message,
            assistant_message,
            emotional_state,
            json.dumps(metadata) if metadata else None
        ))
        
        conn.commit()
        conn.close()
    
    def get_recent_conversations(self, limit=10):
        """
        Retrieve recent conversation history
        
        Args:
            limit: Number of recent turns to retrieve
            
        Returns:
            List of dicts with conversation turns
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT user_message, assistant_message, emotional_state, timestamp
            FROM conversations
            ORDER BY id DESC
            LIMIT ?
        ''', (limit,))
        
        rows = cursor.fetchall()
        conn.close()
        
        # Reverse to get chronological order
        conversations = []
        for row in reversed(rows):
            conversations.append({
                "user": row[0],
                "assistant": row[1],
                "emotional_state": row[2],
                "timestamp": row[3]
            })
        
        return conversations
    
    def get_conversation_history_for_llm(self, limit=5):
        """
        Get conversation history formatted for Ollama messages
        
        Args:
            limit: Number of recent turns
            
        Returns:
            List of message dicts for Ollama
        """
        conversations = self.get_recent_conversations(limit)
        messages = []
        
        for conv in conversations:
            messages.append({"role": "user", "content": conv["user"]})
            messages.append({"role": "assistant", "content": conv["assistant"]})
        
        return messages
    
    def set_user_context(self, category, key, value):
        """
        Store persistent user context (facts about Myra)
        
        Args:
            category: Context category (e.g., "identity", "preferences", "work")
            key: Specific key (e.g., "name", "role", "timezone")
            value: Value to store
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO user_context (category, key, value, updated_at)
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
        ''', (category, key, value))
        
        conn.commit()
        conn.close()
    
    def get_user_context(self, category=None):
        """
        Retrieve user context
        
        Args:
            category: Optional filter by category
            
        Returns:
            Dict of context key-value pairs
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if category:
            cursor.execute('SELECT key, value FROM user_context WHERE category = ?', (category,))
        else:
            cursor.execute('SELECT key, value FROM user_context')
        
        rows = cursor.fetchall()
        conn.close()
        
        return {row[0]: row[1] for row in rows}
    
    def get_memory_summary(self):
        """Get summary of stored memory"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM conversations')
        conv_count = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM user_context')
        context_count = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            "total_conversations": conv_count,
            "user_context_entries": context_count
        }
