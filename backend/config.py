"""
AIRIS Configuration Module
Loads environment variables and provides centralized config access
"""
import os
from dotenv import load_dotenv

# Load .env file
load_dotenv()

class Config:
    """Centralized configuration for AIRIS backend"""
    
    # ElevenLabs TTS
    ELEVENLABS_API_KEY = os.getenv('ELEVENLABS_API_KEY')
    ELEVENLABS_VOICE_ID = os.getenv('ELEVENLABS_VOICE_ID')
    
    # Ollama - Single or Multi-Node
    OLLAMA_HOST = os.getenv('OLLAMA_HOST', 'http://localhost:11434')
    OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', 'qwen2.5:235b')
    
    # Multi-node configuration (comma-separated)
    OLLAMA_NODES_STR = os.getenv('OLLAMA_NODES', None)
    if OLLAMA_NODES_STR:
        OLLAMA_NODES = [node.strip() for node in OLLAMA_NODES_STR.split(',')]
    else:
        OLLAMA_NODES = None
    
    # EOD Historical Data
    EOD_API_KEY = os.getenv('EOD_API_KEY')
    
    # Database
    DATABASE_PATH = os.getenv('DATABASE_PATH', './data/airis_memory.db')
    
    # Flask
    FLASK_HOST = os.getenv('FLASK_HOST', '0.0.0.0')
    FLASK_PORT = int(os.getenv('FLASK_PORT', 5000))
    FLASK_DEBUG = os.getenv('FLASK_DEBUG', 'True').lower() == 'true'
    
    # CORS
    CORS_ORIGINS = os.getenv('CORS_ORIGINS', 'http://localhost:5173,http://localhost:5174').split(',')
    
    @staticmethod
    def validate():
        """Validate critical configuration"""
        if not Config.ELEVENLABS_API_KEY:
            print("⚠️  Warning: ELEVENLABS_API_KEY not set")
        if not Config.ELEVENLABS_VOICE_ID:
            print("⚠️  Warning: ELEVENLABS_VOICE_ID not set")
        
        print(f"✓ Ollama model: {Config.OLLAMA_MODEL}")
        
        if Config.OLLAMA_NODES:
            print(f"✓ Multi-node mode: {len(Config.OLLAMA_NODES)} nodes")
            for i, node in enumerate(Config.OLLAMA_NODES):
                print(f"   Node {i+1}: {node}")
        else:
            print(f"✓ Single-node mode: {Config.OLLAMA_HOST}")
        
        if Config.EOD_API_KEY:
            print(f"✓ EOD Historical Data: Connected")
        else:
            print("⚠️  Warning: EOD_API_KEY not set (XAUUSD data disabled)")
        
        print(f"✓ Database: {Config.DATABASE_PATH}")
        print(f"✓ Flask: {Config.FLASK_HOST}:{Config.FLASK_PORT}")