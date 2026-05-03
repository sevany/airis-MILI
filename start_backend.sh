#!/bin/bash
# AIRIS Backend Quick Start

echo "🧠 Starting AIRIS Backend..."
echo ""

# Check if .env exists
if [ ! -f .env ]; then
    echo "⚠️  .env file not found. Copying from .env.example..."
    cp .env.example .env
    echo "✓ .env created. Please edit it with your API keys."
    exit 1
fi

# Check if Ollama is running
if ! curl -s http://localhost:11434/api/tags > /dev/null; then
    echo "❌ Ollama is not running. Start it with:"
    echo "   ollama serve"
    exit 1
fi

# Check if model exists
if ! ollama list | grep -q "qwen2.5:235b"; then
    echo "⚠️  Qwen 235B not found. Pulling model..."
    echo "   This will take a while (model is ~140GB)..."
    ollama pull qwen2.5:235b
fi

echo "✓ Ollama ready"
echo ""

# Start Flask app
echo "🚀 Starting Flask server on port 5000..."
python3 -m backend.app
