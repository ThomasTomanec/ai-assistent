#!/bin/bash
echo "🚀 Setting up Voice Assistant (openWakeWord Edition)..."

if ! command -v python3.11 &> /dev/null; then
    echo "❌ Python 3.11 not found. Install: brew install python@3.11"
    exit 1
fi

echo "📦 Creating virtual environment..."
python3.11 -m venv venv
source venv/bin/activate

pip install --upgrade pip

echo "📚 Installing dependencies..."
pip install -r requirements.txt

mkdir -p logs

if [ ! -f .env ]; then
    cp .env.example .env
fi

echo ""
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "1. source venv/bin/activate"
echo "2. pip install mlx-whisper  # For STT"
echo "3. python main.py"
