"""
AIRIS Backend API
Flask server with streaming chat endpoint and TTS support
"""
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
from datetime import datetime
import json

from backend.config import Config
from backend.models.ollama_client import OllamaClient
from backend.core.persona import M3GANPersona
from backend.core.memory import Memory
from backend.core.vector_memory import VectorMemory
from backend.core.user_profile import UserProfile
from backend.core.document_rag import DocumentRAG
from backend.core.episodic_memory import EpisodicMemory
from backend.core.interruption_memory import InterruptionMemory
from backend.voice.tts import TTSEngine
from backend.voice.stt import STTEngine
from backend.tools.xauusd import XAUUSDData

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=Config.CORS_ORIGINS)

# Initialize components
ollama = OllamaClient()
memory = Memory()
vector_memory = VectorMemory()  # Conversation memory
user_profile = UserProfile()  # User knowledge
document_rag = DocumentRAG()  # Document knowledge
episodic_memory = EpisodicMemory(ollama_client=ollama)  # Meeting/conversation logs (NEW!)
tts = TTSEngine()
stt = STTEngine(model_size="small")  # Good accuracy, fast on CPU
interruption_mem = InterruptionMemory()
xauusd = XAUUSDData() if Config.EOD_API_KEY else None

print("\n" + "="*60)
print("🧠 AIRIS Backend Starting...")
print("="*60)
Config.validate()
if xauusd:
    xauusd_ok, xauusd_msg = xauusd.health_check()
    print(xauusd_msg)
print("="*60 + "\n")

# Health check endpoints
@app.route('/api/health', methods=['GET'])
def health():
    """System health check"""
    ollama_ok, ollama_msg = ollama.health_check()
    tts_ok, tts_msg = tts.health_check()
    stt_ok, stt_msg = stt.health_check()
    vmem_ok, vmem_msg = vector_memory.health_check()
    profile_ok, profile_msg = user_profile.health_check()
    doc_ok, doc_msg = document_rag.health_check()
    episodic_ok, episodic_msg = episodic_memory.health_check()
    mem_summary = memory.get_memory_summary()
    
    components = {
        "ollama": {"status": "ok" if ollama_ok else "error", "message": ollama_msg},
        "tts": {"status": "ok" if tts_ok else "error", "message": tts_msg},
        "stt": {"status": "ok" if stt_ok else "error", "message": stt_msg},
        "memory": {"status": "ok", "summary": mem_summary},
        "vector_memory": {"status": "ok" if vmem_ok else "error", "message": vmem_msg},
        "user_profile": {"status": "ok" if profile_ok else "error", "message": profile_msg},
        "document_rag": {"status": "ok" if doc_ok else "error", "message": doc_msg},
        "episodic_memory": {"status": "ok" if episodic_ok else "error", "message": episodic_msg}
    }
    
    if xauusd:
        xauusd_ok, xauusd_msg = xauusd.health_check()
        components["xauusd"] = {"status": "ok" if xauusd_ok else "error", "message": xauusd_msg}
    
    return jsonify({
        "status": "online",
        "components": components
    })

# XAUUSD endpoints
@app.route('/api/xauusd/price', methods=['GET'])
def xauusd_price():
    """Get current XAUUSD price"""
    if not xauusd:
        return jsonify({"error": "XAUUSD data not configured"}), 503
    
    try:
        data = xauusd.get_real_time_price()
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/xauusd/intraday', methods=['GET'])
def xauusd_intraday():
    """Get intraday XAUUSD data"""
    if not xauusd:
        return jsonify({"error": "XAUUSD data not configured"}), 503
    
    interval = request.args.get('interval', '5m')
    limit = int(request.args.get('limit', 50))
    
    try:
        data = xauusd.get_intraday_data(interval=interval, limit=limit)
        return jsonify({"candles": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/xauusd/eod', methods=['GET'])
def xauusd_eod():
    """Get end-of-day XAUUSD data"""
    if not xauusd:
        return jsonify({"error": "XAUUSD data not configured"}), 503
    
    days = int(request.args.get('days', 30))
    
    try:
        data = xauusd.get_eod_data(days=days)
        return jsonify({"candles": data})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/xauusd/analysis', methods=['GET'])
def xauusd_analysis():
    """Get comprehensive XAUUSD trading analysis with news sentiment"""
    if not xauusd:
        return jsonify({"error": "XAUUSD data not configured"}), 503
    
    try:
        # Get full analysis (cached EOD + real-time price + technical indicators)
        analysis = xauusd.get_full_analysis()
        
        # Load sentiment if available
        from backend.tools.xauusd_news import XAUUSDNews
        news = XAUUSDNews()
        sentiment = news.load_cached_sentiment()
        
        if not sentiment:
            # Fetch fresh if no cache
            sentiment = news.get_sentiment_summary()
        
        # Combine everything
        return jsonify({
            **analysis,
            'sentiment': sentiment
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/chat', methods=['POST'])
def chat():
    """
    Main chat endpoint with streaming support
    
    Request body:
    {
        "message": "user message here",
        "stream": true/false (optional, default true)
    }
    
    Response:
    - If stream=true: Server-sent events with chunks
    - If stream=false: JSON with full response
    """
    data = request.json
    user_message = data.get('message', '').strip()
    stream_response = data.get('stream', True)
    
    if not user_message:
        return jsonify({"error": "Message is required"}), 400
    
    try:
        # Check if user is asking about XAUUSD
        xauusd_context = ""
        if xauusd and any(keyword in user_message.lower() for keyword in ['xauusd', 'gold', 'xau', 'trading', 'buy', 'sell']):
            try:
                # Get full analysis with sentiment
                analysis = xauusd.get_full_analysis()
                ta = analysis['technical_analysis']
                
                # Load sentiment
                from backend.tools.xauusd_news import XAUUSDNews
                news = XAUUSDNews()
                sentiment = news.load_cached_sentiment() or news.get_sentiment_summary()
                
                # Build context for AIRIS
                xauusd_context = f"""
Current XAUUSD Market Data:
• Price: ${analysis['current_price']:.2f} ({analysis['change_percent']:+.2f}%)
• Trend: {ta['trend']}
• Support: ${ta['support_resistance']['support']:.2f}
• Resistance: ${ta['support_resistance']['resistance']:.2f}
• SMA 20: ${ta['sma']['sma_20']:.2f}
• SMA 50: ${ta['sma']['sma_50']:.2f}
• News Sentiment: {sentiment['sentiment']} ({sentiment['score']:+.2f})
• Sentiment Summary: {sentiment['summary']}
"""
            except Exception as e:
                print(f"⚠️  XAUUSD context error: {str(e)}")
                pass
        
        # Get conversation history from memory
        conversation_history = memory.get_conversation_history_for_llm(limit=5)
        
        # Get USER PROFILE context (smart retrieval based on query)
        profile_context = user_profile.get_context_for_query(user_message)
        if profile_context:
            profile_context = f"\n\n=== USER PROFILE ===\n{profile_context}\n=== END PROFILE ===\n"
        
        # Get DOCUMENT context (search uploaded documents)
        document_context = ""
        doc_keywords = ['document', 'pdf', 'file', 'uploaded', 'proposal', 'tender', 
                       'summarize', 'summary', 'what did', 'tell me about', 'explain',
                       'dokumen', 'fail', 'ringkasan']
        
        # Always search documents if they exist
        doc_stats = document_rag.get_stats()
        if doc_stats['total_documents'] > 0:
            # Search documents for relevant context
            doc_context_raw = document_rag.get_context_for_query(user_message, max_chunks=5)
            if doc_context_raw:
                document_context = f"\n\n=== UPLOADED DOCUMENTS ===\n{doc_context_raw}\n=== END DOCUMENTS ===\n"
                print(f"📄 Injected document context ({len(doc_context_raw)} chars)")
        
        # Get EPISODIC MEMORY context (past meetings/conversations)
        episodic_context = ""
        episodic_stats = episodic_memory.get_stats()
        if episodic_stats['total_memories'] > 0:
            # Search episodic memories for relevant context
            episodic_context_raw = episodic_memory.get_context_for_query(user_message, max_memories=3)
            if episodic_context_raw:
                episodic_context = f"\n\n{episodic_context_raw}\n"
                print(f"🧠 Injected episodic context ({len(episodic_context_raw)} chars)")
        
        # Check for REMEMBER/FORGET commands
        remember_keywords = ['remember that', 'ingat yang', 'jangan lupa', 'please remember']
        forget_keywords = ['forget about', 'lupa tentang', 'delete memory']
        
        if any(kw in user_message.lower() for kw in remember_keywords):
            # Extract what to remember
            msg_lower = user_message.lower()
            for kw in remember_keywords:
                if kw in msg_lower:
                    # Get text after the keyword
                    parts = user_message.split(kw, 1)
                    if len(parts) > 1:
                        memory_text = parts[1].strip()
                        user_profile.add_custom_memory(memory_text)
                        print(f"💾 Stored custom memory: {memory_text[:50]}...")
                    break
        
        # Get relevant context from vector memory (ONLY when user asks)
        vector_context = ""
        memory_keywords = ['remember', 'recall', 'discussed', 'talked about', 'mentioned', 
                          'yesterday', 'last time', 'before', 'earlier', 'previous',
                          'what did we', 'remind me', 'ingat tak', 'semalam', 'hari ni',
                          'today', 'this week', 'last week', 'this month']
        
        # ONLY search if user explicitly asks about past conversations
        user_asking_about_memory = any(keyword in user_message.lower() for keyword in memory_keywords)
        
        if user_asking_about_memory:
            print(f"🧠 User asking about memory, searching: '{user_message[:50]}...'")
            
            # Smart date detection
            from datetime import datetime, timedelta
            date_range = None
            target_date = None
            
            msg_lower = user_message.lower()
            today = datetime.now()
            
            if 'yesterday' in msg_lower or 'semalam' in msg_lower:
                target_date = (today - timedelta(days=1)).strftime('%Y-%m-%d')
                print(f"📅 Detected: yesterday ({target_date})")
            elif 'today' in msg_lower or 'hari ni' in msg_lower:
                target_date = today.strftime('%Y-%m-%d')
                print(f"📅 Detected: today ({target_date})")
            elif 'last week' in msg_lower:
                start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')
                date_range = (start_date, end_date)
                print(f"📅 Detected: last week ({start_date} to {end_date})")
            elif 'this week' in msg_lower:
                # Start of week (Monday)
                start_of_week = today - timedelta(days=today.weekday())
                start_date = start_of_week.strftime('%Y-%m-%d')
                end_date = today.strftime('%Y-%m-%d')
                date_range = (start_date, end_date)
                print(f"📅 Detected: this week ({start_date} to {end_date})")
            
            # Search with date filter if detected
            if target_date:
                # Get memories from specific date
                day_memories = vector_memory.get_memories_by_date(target_date)
                if day_memories:
                    print(f"✓ Found {len(day_memories)} memories on {target_date}")
                    # Build context from that day
                    context_parts = [f"[{m['timestamp'].split('T')[1][:5]}] {m['conversation']}" 
                                   for m in day_memories[:5]]
                    vector_context = "\n\n".join(context_parts)
                    vector_context = f"\n\n=== CONVERSATIONS ON {target_date} ===\n{vector_context}\n=== END ===\n"
                else:
                    vector_context = f"\n\nNo conversations found on {target_date}.\n"
            elif date_range:
                # Get memories from date range
                grouped_memories = vector_memory.get_memories_by_date_range(date_range[0], date_range[1])
                if grouped_memories:
                    total = sum(len(mems) for mems in grouped_memories.values())
                    print(f"✓ Found {total} memories across {len(grouped_memories)} days")
                    # Build context grouped by date
                    context_parts = []
                    for date, mems in sorted(grouped_memories.items()):
                        context_parts.append(f"=== {date} ===")
                        for m in mems[:3]:  # Max 3 per day
                            context_parts.append(f"[{m['timestamp'].split('T')[1][:5]}] {m['conversation']}")
                    vector_context = "\n".join(context_parts)
                    vector_context = f"\n\n=== CONVERSATIONS {date_range[0]} to {date_range[1]} ===\n{vector_context}\n=== END ===\n"
                else:
                    vector_context = f"\n\nNo conversations found in that date range.\n"
            else:
                # Regular semantic search
                relevant_memories = vector_memory.search_memory(user_message, n_results=3)
                
                if relevant_memories:
                    print(f"✓ Found {len(relevant_memories)} relevant memories")
                    vector_context = vector_memory.get_context_for_query(user_message, max_context_length=1500)
                    vector_context = f"\n\n=== RELEVANT PAST CONVERSATIONS ===\n{vector_context}\n=== END PAST CONVERSATIONS ===\n"
                else:
                    print("ℹ️ No relevant memories found")
        else:
            print("⚡ Skipping memory search (not needed)")
        
        # Get interruption emotional context
        interruption_context = interruption_mem.get_emotional_context()
        if interruption_context:
            xauusd_context = (xauusd_context or "") + f"\n\n{interruption_context}"
        
        # Combine ALL contexts: XAUUSD + Profile + Documents + Episodic + Vector Memory
        combined_context = xauusd_context
        if profile_context:
            combined_context = (combined_context or "") + profile_context
        if document_context:
            combined_context = (combined_context or "") + document_context
        if episodic_context:
            combined_context = (combined_context or "") + episodic_context
        if vector_context:
            combined_context = (combined_context or "") + vector_context
        
        # Build messages with M3GAN persona
        messages = M3GANPersona.build_messages(
            user_message=user_message,
            conversation_history=conversation_history,
            memory_context=combined_context,
            emotional_state="neutral"
        )
        
        if stream_response:
            # Streaming response
            def generate():
                full_response = ""
                
                for chunk in ollama.chat(messages, stream=True):
                    full_response += chunk
                    # Send chunk as SSE
                    yield f"data: {json.dumps({'type': 'chunk', 'content': chunk})}\n\n"
                
                # Save to memory after full response
                memory.add_conversation(user_message, full_response, emotional_state="neutral")
                
                # Save to vector memory for long-term semantic search
                from datetime import datetime as dt_now
                vector_memory.add_conversation(
                    user_message=user_message,
                    assistant_response=full_response,
                    metadata={
                        "timestamp": str(dt_now.now()),
                        "has_xauusd": bool(xauusd_context),
                        "interrupted": False
                    }
                )
                
                # Send completion signal
                yield f"data: {json.dumps({'type': 'done', 'full_response': full_response})}\n\n"
            
            return Response(
                stream_with_context(generate()),
                content_type='text/event-stream'
            )
        
        else:
            # Non-streaming response
            response_text = ""
            for chunk in ollama.chat(messages, stream=True):
                response_text += chunk
            
            # Save to memory
            memory.add_conversation(user_message, response_text, emotional_state="neutral")
            
            # Save to vector memory for long-term semantic search
            from datetime import datetime as dt_now
            vector_memory.add_conversation(
                user_message=user_message,
                assistant_response=response_text,
                metadata={
                    "timestamp": str(dt_now.now()),
                    "has_xauusd": bool(xauusd_context),
                    "interrupted": False
                }
            )
            
            return jsonify({
                "response": response_text,
                "emotional_state": "neutral"
            })
    
    except Exception as e:
        print(f"❌ Chat error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/tts', methods=['POST'])
def text_to_speech():
    """
    Convert text to speech using ElevenLabs
    
    Request body:
    {
        "text": "text to synthesize"
    }
    
    Response:
    {
        "audio_base64": "base64 encoded audio"
    }
    """
    data = request.json
    text = data.get('text', '').strip()
    
    if not text:
        return jsonify({"error": "Text is required"}), 400
    
    try:
        audio_base64 = tts.synthesize_base64(text)
        return jsonify({"audio_base64": audio_base64})
    
    except Exception as e:
        print(f"❌ TTS error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/stt', methods=['POST'])
def speech_to_text():
    """
    Convert speech to text using Whisper
    
    Request: multipart/form-data with audio file
    
    Response:
    {
        "text": "transcribed text",
        "language": "detected language",
        "confidence": 1.0
    }
    """
    if 'audio' not in request.files:
        return jsonify({"error": "Audio file is required"}), 400
    
    audio_file = request.files['audio']
    
    if audio_file.filename == '':
        return jsonify({"error": "No audio file selected"}), 400
    
    try:
        # Read audio data
        audio_data = audio_file.read()
        
        # Transcribe with Whisper
        result = stt.transcribe(audio_data)
        
        return jsonify(result)
    
    except Exception as e:
        print(f"❌ STT error: {str(e)}")
        return jsonify({"error": str(e)}), 500

@app.route('/api/interrupt', methods=['POST'])
def handle_interruption():
    """
    Handle user interrupting AIRIS while speaking
    Records interruption and returns emotional response
    
    Request body:
    {
        "context": "what AIRIS was saying"
    }
    
    Response:
    {
        "count": 2,
        "emotional_state": "slightly_annoyed",
        "response_prefix": "Myra... can I finish?"
    }
    """
    data = request.json
    context = data.get('context', 'unknown')
    
    result = interruption_mem.record_interruption(context)
    
    return jsonify(result)

@app.route('/api/apology', methods=['POST'])
def handle_apology():
    """
    Handle user apologizing for interruptions
    Resets counter with grace
    
    Response:
    {
        "emotional_state": "forgiving",
        "response": "Okay okay..."
    }
    """
    result = interruption_mem.record_apology()
    return jsonify(result)

@app.route('/api/interruption/stats', methods=['GET'])
def get_interruption_stats():
    """Get interruption statistics and patterns"""
    stats = interruption_mem.get_stats()
    return jsonify(stats)

@app.route('/api/memory/stats', methods=['GET'])
def memory_stats():
    """Get memory statistics"""
    summary = memory.get_memory_summary()
    recent_convs = memory.get_recent_conversations(limit=5)
    
    return jsonify({
        "summary": summary,
        "recent_conversations": recent_convs
    })

@app.route('/api/memory/context', methods=['POST'])
def set_context():
    """
    Set user context
    
    Request body:
    {
        "category": "identity",
        "key": "name",
        "value": "Myra"
    }
    """
    data = request.json
    category = data.get('category')
    key = data.get('key')
    value = data.get('value')
    
    if not all([category, key, value]):
        return jsonify({"error": "category, key, and value are required"}), 400
    
    memory.set_user_context(category, key, value)
    return jsonify({"status": "ok", "message": "Context saved"})

@app.route('/api/memory/context', methods=['GET'])
def get_context():
    """Get all user context"""
    context = memory.get_user_context()
    return jsonify({"context": context})

# ============================================
# VECTOR MEMORY ENDPOINTS (ChromaDB)
# ============================================

@app.route('/api/vector-memory/search', methods=['POST'])
def search_vector_memory():
    """
    Search vector memory for relevant past conversations
    
    Request body:
    {
        "query": "What did we discuss about gold trading?",
        "n_results": 5
    }
    """
    data = request.json
    query = data.get('query', '').strip()
    n_results = data.get('n_results', 5)
    
    if not query:
        return jsonify({"error": "Query is required"}), 400
    
    try:
        results = vector_memory.search_memory(query, n_results=n_results)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vector-memory/recent', methods=['GET'])
def get_recent_vector_memories():
    """Get N most recent conversations from vector memory"""
    n = request.args.get('n', default=10, type=int)
    
    try:
        recent = vector_memory.get_recent_conversations(n=n)
        return jsonify({"recent_conversations": recent})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vector-memory/stats', methods=['GET'])
def get_vector_memory_stats():
    """Get vector memory statistics"""
    try:
        stats = vector_memory.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vector-memory/export', methods=['POST'])
def export_vector_memory():
    """Export all vector memories to JSON"""
    data = request.json or {}
    output_file = data.get('output_file', 'data/memory_export.json')
    
    try:
        file_path = vector_memory.export_memories(output_file)
        return jsonify({"status": "ok", "file": file_path})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vector-memory/delete', methods=['DELETE'])
def delete_vector_memory():
    """Delete a specific memory by ID"""
    data = request.json
    memory_id = data.get('memory_id')
    
    if not memory_id:
        return jsonify({"error": "memory_id is required"}), 400
    
    try:
        vector_memory.delete_memory(memory_id)
        return jsonify({"status": "ok", "message": "Memory deleted"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vector-memory/by-date/<date>', methods=['GET'])
def get_memories_by_date(date):
    """
    Get all memories from a specific date
    
    URL: /api/vector-memory/by-date/2026-05-05
    """
    try:
        memories = vector_memory.get_memories_by_date(date)
        return jsonify({
            "date": date,
            "count": len(memories),
            "memories": memories
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/vector-memory/date-range', methods=['POST'])
def get_memories_by_range():
    """
    Get memories within a date range, grouped by day
    
    Request body:
    {
        "start_date": "2026-05-01",
        "end_date": "2026-05-05"
    }
    """
    data = request.json
    start_date = data.get('start_date')
    end_date = data.get('end_date')
    
    if not start_date or not end_date:
        return jsonify({"error": "start_date and end_date are required"}), 400
    
    try:
        grouped = vector_memory.get_memories_by_date_range(start_date, end_date)
        total_memories = sum(len(mems) for mems in grouped.values())
        
        return jsonify({
            "start_date": start_date,
            "end_date": end_date,
            "days": len(grouped),
            "total_memories": total_memories,
            "memories_by_date": grouped
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# USER PROFILE ENDPOINTS
# ============================================

@app.route('/api/profile/summary', methods=['GET'])
def get_profile_summary():
    """Get user profile summary"""
    try:
        summary = user_profile.get_full_profile_summary()
        return jsonify({"summary": summary})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile/custom-memories', methods=['GET'])
def get_custom_memories():
    """Get all custom memories"""
    try:
        memories = user_profile.get_custom_memories()
        return jsonify({"memories": memories, "count": len(memories)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile/custom-memories', methods=['POST'])
def add_custom_memory():
    """
    Add a custom memory
    
    Request body:
    {
        "memory": "Planning to hire 3 new AI engineers"
    }
    """
    data = request.json
    memory_text = data.get('memory', '').strip()
    
    if not memory_text:
        return jsonify({"error": "memory text is required"}), 400
    
    try:
        user_profile.add_custom_memory(memory_text)
        return jsonify({"status": "ok", "message": "Memory added"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile/custom-memories/<int:index>', methods=['DELETE'])
def delete_custom_memory(index):
    """Delete a custom memory by index"""
    try:
        success = user_profile.remove_custom_memory(index)
        if success:
            return jsonify({"status": "ok", "message": "Memory deleted"})
        else:
            return jsonify({"error": "Memory not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/profile/update', methods=['POST'])
def update_profile_field():
    """
    Update a profile field
    
    Request body:
    {
        "path": "user_profile.role",
        "value": "Chief AI Officer"
    }
    """
    data = request.json
    path = data.get('path')
    value = data.get('value')
    
    if not path or value is None:
        return jsonify({"error": "path and value are required"}), 400
    
    try:
        user_profile.update_profile_field(path, value)
        return jsonify({"status": "ok", "message": "Profile updated"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# DOCUMENT RAG ENDPOINTS
# ============================================

@app.route('/api/documents/upload', methods=['POST'])
def upload_document():
    """
    Upload and ingest a document
    Supports: PDF, DOCX, TXT, MD
    """
    if 'file' not in request.files:
        return jsonify({"error": "No file provided"}), 400
    
    file = request.files['file']
    
    if file.filename == '':
        return jsonify({"error": "Empty filename"}), 400
    
    try:
        import tempfile
        import os
        
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=os.path.splitext(file.filename)[1]) as tmp:
            file.save(tmp.name)
            tmp_path = tmp.name
        
        # Ingest document
        result = document_rag.ingest_document(
            file_path=tmp_path,
            filename=file.filename,
            doc_type=request.form.get('doc_type', 'unknown')
        )
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        if 'error' in result:
            return jsonify(result), 400
        
        return jsonify(result)
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/list', methods=['GET'])
def list_documents():
    """Get list of all ingested documents"""
    try:
        docs = document_rag.get_all_documents()
        return jsonify({"documents": docs, "count": len(docs)})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/search', methods=['POST'])
def search_documents():
    """
    Search documents
    
    Request body:
    {
        "query": "ADAM performance specs",
        "n_results": 5
    }
    """
    data = request.json
    query = data.get('query', '').strip()
    n_results = data.get('n_results', 5)
    
    if not query:
        return jsonify({"error": "query is required"}), 400
    
    try:
        results = document_rag.search_documents(query, n_results=n_results)
        return jsonify({"results": results})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/stats', methods=['GET'])
def get_document_stats():
    """Get document knowledge base statistics"""
    try:
        stats = document_rag.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/documents/<doc_id>', methods=['DELETE'])
def delete_document(doc_id):
    """Delete a document"""
    try:
        success = document_rag.delete_document(doc_id)
        if success:
            return jsonify({"status": "ok", "message": "Document deleted"})
        else:
            return jsonify({"error": "Document not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ============================================
# EPISODIC MEMORY ENDPOINTS (NEW!)
# ============================================

@app.route('/api/log_memory', methods=['POST'])
def log_memory():
    """
    Log a new episodic memory (meeting/conversation)
    
    Request body:
    {
        "text": "Raw meeting notes or conversation",
        "tag": "PRSB|Petronas|Boustead|MINDEF|Personal|General"
    }
    
    Returns:
    {
        "status": "ok",
        "memory_id": "episodic_PRSB_20260511_143022",
        "structured": { ... structured JSON ... }
    }
    """
    data = request.json
    text = data.get('text', '').strip()
    tag = data.get('tag', 'General').strip()
    
    if not text:
        return jsonify({"error": "text is required"}), 400
    
    try:
        # Summarize and store
        memory_id = episodic_memory.store_memory(text, tag)
        
        if not memory_id:
            return jsonify({"error": "Failed to process memory"}), 500
        
        # Get the stored memory to return
        all_data = episodic_memory.collection.get(ids=[memory_id])
        structured = None
        if all_data['documents']:
            import json
            structured = json.loads(all_data['documents'][0])
        
        return jsonify({
            "status": "ok",
            "memory_id": memory_id,
            "structured": structured,
            "message": f"Memory logged with tag: {tag}"
        })
    
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/episodic_memory/search', methods=['POST'])
def search_episodic_memory():
    """
    Search episodic memories
    
    Request body:
    {
        "query": "PRSB simulation challenges",
        "n_results": 3,
        "tag_filter": "PRSB" (optional),
        "importance_filter": "high" (optional)
    }
    """
    data = request.json
    query = data.get('query', '').strip()
    n_results = data.get('n_results', 3)
    tag_filter = data.get('tag_filter')
    importance_filter = data.get('importance_filter')
    
    if not query:
        return jsonify({"error": "query is required"}), 400
    
    try:
        memories = episodic_memory.retrieve_memory(
            query=query,
            n_results=n_results,
            tag_filter=tag_filter,
            importance_filter=importance_filter
        )
        
        return jsonify({
            "results": memories,
            "count": len(memories)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/episodic_memory/by_tag/<tag>', methods=['GET'])
def get_memories_by_tag(tag):
    """Get all memories with a specific tag"""
    try:
        limit = request.args.get('limit', 10, type=int)
        memories = episodic_memory.get_memories_by_tag(tag, limit=limit)
        
        return jsonify({
            "tag": tag,
            "memories": memories,
            "count": len(memories)
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/episodic_memory/tags', methods=['GET'])
def get_all_tags():
    """Get list of all available tags"""
    try:
        tags = episodic_memory.get_all_tags()
        return jsonify({"tags": tags})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/episodic_memory/stats', methods=['GET'])
def get_episodic_stats():
    """Get episodic memory statistics"""
    try:
        stats = episodic_memory.get_stats()
        return jsonify(stats)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/episodic_memory/<memory_id>', methods=['DELETE'])
def delete_episodic_memory(memory_id):
    """Delete a specific episodic memory"""
    try:
        success = episodic_memory.delete_memory(memory_id)
        if success:
            return jsonify({"status": "ok", "message": "Memory deleted"})
        else:
            return jsonify({"error": "Memory not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    print(f"\n🚀 AIRIS running on http://{Config.FLASK_HOST}:{Config.FLASK_PORT}\n")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )