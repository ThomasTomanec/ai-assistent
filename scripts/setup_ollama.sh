#!/bin/bash
# Setup script pro Ollama v Dockeru

set -e

echo "🚀 Starting Ollama Docker setup..."

# Spusť Docker Compose
echo "📦 Starting Ollama container..."
docker compose up -d ollama

# Počkej až se spustí
echo "⏳ Waiting for Ollama to be ready..."
sleep 5

# Kontrola zdraví
until docker compose exec ollama curl -s http://localhost:11434/api/tags > /dev/null 2>&1; do
  echo "Waiting for Ollama..."
  sleep 2
done

echo "✅ Ollama is running!"

# Stáhni model
echo "📥 Downloading Llama 3.3 (3B) model..."
docker exec -it voice-assistant-ollama ollama pull llama3.3:3b

echo "✅ Setup complete!"
echo ""
echo "🎯 Ollama is ready at: http://localhost:11434"
echo "📊 Available models:"
docker exec voice-assistant-ollama ollama list
echo ""
echo "🚀 Start your voice assistant with: python main.py"
