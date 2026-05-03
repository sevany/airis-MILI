"""
AIRIS Backend API
Flask server with streaming chat endpoint and TTS support
"""
from flask import Flask, request, jsonify, Response, stream_with_context
from flask_cors import CORS
import json

from backend.config import Config
from backend.models.ollama_client import OllamaClient
from backend.core.persona import M3GANPersona
from backend.core.memory import Memory
from backend.voice.tts import TTSEngine
from backend.tools.xauusd import XAUUSDData

# Initialize Flask app
app = Flask(__name__)
CORS(app, origins=Config.CORS_ORIGINS)

# Initialize components
ollama = OllamaClient()
memory = Memory()
tts = TTSEngine()
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
    mem_summary = memory.get_memory_summary()
    
    components = {
        "ollama": {"status": "ok" if ollama_ok else "error", "message": ollama_msg},
        "tts": {"status": "ok" if tts_ok else "error", "message": tts_msg},
        "memory": {"status": "ok", "summary": mem_summary}
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
        
        # Build messages with M3GAN persona
        messages = M3GANPersona.build_messages(
            user_message=user_message,
            conversation_history=conversation_history,
            memory_context=xauusd_context,
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

if __name__ == '__main__':
    print(f"\n🚀 AIRIS running on http://{Config.FLASK_HOST}:{Config.FLASK_PORT}\n")
    app.run(
        host=Config.FLASK_HOST,
        port=Config.FLASK_PORT,
        debug=Config.FLASK_DEBUG
    )