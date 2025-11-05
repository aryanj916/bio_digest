#!/bin/bash

# Setup script for new Robotics Digest features
# This script creates the new directories and files needed

echo "🚀 Setting up new features for Robotics Digest..."

# Create new directories
echo "📁 Creating directories..."
mkdir -p media
mkdir -p social
mkdir -p llm
mkdir -p web/assets

# Create __init__.py files
echo "📝 Creating module files..."

# media/__init__.py
cat > media/__init__.py << 'EOF'
from .figure_extractor import FigureExtractor

__all__ = ['FigureExtractor']
EOF

# social/__init__.py
cat > social/__init__.py << 'EOF'
from .x_finder import XFinder

__all__ = ['XFinder']
EOF

# Check if files were created
echo ""
echo "✅ New directory structure:"
echo "  media/"
echo "    ├── __init__.py"
echo "    └── figure_extractor.py (add manually)"
echo "  social/"
echo "    ├── __init__.py"
echo "    └── x_finder.py (add manually)"
echo "  llm/"
echo "    └── summarize.py (add manually)"
echo "  render/"
echo "    ├── web_template.html (add manually)"
echo "    └── web_renderer.py (add manually)"
echo ""

# Update Python dependencies
echo "📦 Installing new Python dependencies..."
pip install requests==2.32.3
pip install pdf2image==1.17.0
pip install Pillow==10.4.0

# Check for system dependencies
echo ""
echo "⚠️  System dependencies check:"
if command -v pdftoppm &> /dev/null; then
    echo "  ✅ poppler-utils is installed"
else
    echo "  ❌ poppler-utils is NOT installed"
    echo "     Run: sudo apt-get install poppler-utils (Ubuntu/Debian)"
    echo "     Or:  brew install poppler (macOS)"
fi

echo ""
echo "📋 Next steps:"
echo "1. Copy the new module files to their directories:"
echo "   - media/figure_extractor.py"
echo "   - social/x_finder.py"
echo "   - llm/summarize.py"
echo "   - render/web_renderer.py"
echo "   - render/web_template.html"
echo ""
echo "2. Replace these existing files:"
echo "   - render/email_template.html (backup the old one first!)"
echo "   - main.py (backup the old one first!)"
echo "   - config.yaml (backup the old one first!)"
echo ""
echo "3. Update .github/workflows/daily-digest.yml"
echo ""
echo "4. Enable GitHub Pages in your repo settings:"
echo "   Settings > Pages > Source: GitHub Actions"
echo ""
echo "5. Test locally with:"
echo "   python main.py --test --verbose"
echo ""
echo "🎉 Setup complete!"


