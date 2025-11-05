#!/bin/bash

# Droyd Daily Robotics Digest - Production Deployment Script

echo "🚀 Setting up Droyd Daily Robotics Digest for production..."

# Check if Python 3.8+ is installed
python3 --version > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ Python 3.8+ is required but not installed"
    exit 1
fi

# Create virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
echo "🔧 Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "📚 Installing dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found!"
    echo "📝 Please copy env.example to .env and fill in your API keys:"
    echo "   cp env.example .env"
    echo "   nano .env"
    echo ""
    echo "Required API keys:"
    echo "   - GEMINI_API_KEY (from Google AI Studio)"
    echo "   - RESEND_API_KEY (from Resend.com)"
    exit 1
fi

# Test the setup
echo "🧪 Testing the setup..."
python test_light_mode.py

if [ $? -eq 0 ]; then
    echo "✅ Setup completed successfully!"
    echo ""
    echo "📅 The digest will run Monday-Friday at 5:00 PM Eastern Time"
    echo ""
    echo "🔧 Manual commands:"
    echo "   python main.py --force          # Force run now"
    echo "   python main.py --test --force   # Test mode"
    echo "   python main.py --reset-db       # Reset database"
    echo ""
    echo "📧 To set up automated scheduling, add to crontab:"
    echo "   0 17 * * 1-5 cd $(pwd) && source venv/bin/activate && python main.py"
else
    echo "❌ Setup failed. Please check the error messages above."
    exit 1
fi
