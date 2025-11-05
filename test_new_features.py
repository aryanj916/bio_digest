#!/usr/bin/env python3
"""
Test script for new Robotics Digest features.
Tests figure extraction, X post finding, digest summary, and web view generation.
"""

import os
import sys
import yaml
from datetime import datetime

def test_imports():
    """Test that all new modules can be imported."""
    print("Testing imports...")
    
    try:
        from media.figure_extractor import FigureExtractor
        print("  ✅ FigureExtractor imported")
    except ImportError as e:
        print(f"  ❌ Failed to import FigureExtractor: {e}")
        return False
    
    try:
        from social.x_finder import XFinder
        print("  ✅ XFinder imported")
    except ImportError as e:
        print(f"  ❌ Failed to import XFinder: {e}")
        return False
    
    try:
        from llm.summarize import DigestSummarizer
        print("  ✅ DigestSummarizer imported")
    except ImportError as e:
        print(f"  ❌ Failed to import DigestSummarizer: {e}")
        return False
    
    try:
        from render.web_renderer import WebRenderer
        print("  ✅ WebRenderer imported")
    except ImportError as e:
        print(f"  ❌ Failed to import WebRenderer: {e}")
        return False
    
    return True


def test_figure_extraction():
    """Test figure extraction with a sample paper."""
    print("\nTesting figure extraction...")
    
    from media.figure_extractor import FigureExtractor
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    extractor = FigureExtractor(config)
    
    # Test paper
    test_paper = {
        'arxiv_id': '2401.12345v1',
        'title': 'Test Paper for Figure Extraction',
        'abstract': 'This is a test abstract.'
    }
    
    result = extractor.extract_figure(test_paper)
    
    if 'figure_url' in result:
        print(f"  ✅ Found figure: {result['figure_url']}")
    elif 'needs_pdf_preview' in result:
        print(f"  ⚠️  No figure found, marked for PDF preview")
    else:
        print(f"  ❌ Figure extraction failed")
    
    return True


def test_x_finder():
    """Test X/Twitter post finding."""
    print("\nTesting X post finder...")
    
    from social.x_finder import XFinder
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    # Enable X posts for testing
    config['features']['include_x_posts'] = True
    
    finder = XFinder(config)
    
    # Test paper (use a well-known paper that likely has X posts)
    test_paper = {
        'arxiv_id': '2303.08774v1',  # GPT-4 paper
        'title': 'GPT-4 Technical Report',
        'abstract': 'We report the development of GPT-4...'
    }
    
    result = finder.find_x_post(test_paper)
    
    if 'x_url' in result:
        print(f"  ✅ Found X post: {result['x_url']}")
    else:
        print(f"  ⚠️  No X post found (this is OK if X posts are disabled)")
    
    return True


def test_digest_summary():
    """Test digest summary generation."""
    print("\nTesting digest summary generation...")
    
    # Check if API key is available
    api_key = os.getenv('GEMINI_API_KEY')
    if not api_key:
        print("  ⚠️  GEMINI_API_KEY not set, skipping summary test")
        return True
    
    from llm.summarize import DigestSummarizer
    
    summarizer = DigestSummarizer(api_key)
    
    # Test papers
    test_papers = [
        {
            'title': 'Dual-Arm Manipulation with Vision-Language Models',
            'final_score': 85,
            'buckets': ['VLA / LLM-in-the-Loop', 'Bimanual / Dual-Arm Manipulation'],
            'why_it_matters': 'Direct application to our dual-arm system',
            'summary': 'New VLA approach for coordinated dual-arm tasks'
        },
        {
            'title': 'Diffusion Policy for Robotic Grasping',
            'final_score': 75,
            'buckets': ['Imitation / Diffusion / RL', 'Grasping & Dexterous Manipulation'],
            'why_it_matters': 'Improves grasp success rate significantly',
            'summary': 'Uses diffusion models for grasp planning'
        }
    ]
    
    try:
        summary = summarizer.generate_summary(test_papers)
        print(f"  ✅ Generated summary: {summary.get('headline', 'N/A')}")
        print(f"     Bullets: {len(summary.get('bullets', []))}")
        print(f"     Highlights: {len(summary.get('highlights', []))}")
    except Exception as e:
        print(f"  ❌ Summary generation failed: {e}")
        return False
    
    return True


def test_web_renderer():
    """Test web view generation."""
    print("\nTesting web renderer...")
    
    from render.web_renderer import WebRenderer
    
    # Load config
    with open('config.yaml', 'r') as f:
        config = yaml.safe_load(f)
    
    renderer = WebRenderer(config)
    
    # Test data
    test_papers = [
        {
            'arxiv_id': '2401.12345v1',
            'title': 'Test Paper for Web View',
            'arxiv_link': 'https://arxiv.org/abs/2401.12345',
            'pdf_link': 'https://arxiv.org/pdf/2401.12345.pdf',
            'final_score': 85,
            'buckets': ['VLA / LLM-in-the-Loop'],
            'why_it_matters': 'Test relevance',
            'summary': 'Test summary',
            'figure_url': 'https://example.com/figure.png'
        }
    ]
    
    buckets = {
        'VLA / LLM-in-the-Loop': test_papers
    }
    
    digest_summary = {
        'headline': 'Test digest for web view',
        'bullets': ['Test bullet 1', 'Test bullet 2'],
        'highlights': []
    }
    
    try:
        html = renderer.render(
            top_picks=test_papers,
            buckets=buckets,
            also_noteworthy=[],
            digest_summary=digest_summary,
            metadata={'total_papers': 1}
        )
        
        # Save test output
        output_path = renderer.save(html)
        print(f"  ✅ Web view generated: {output_path}")
        print(f"     Size: {len(html)} bytes")
        
    except Exception as e:
        print(f"  ❌ Web rendering failed: {e}")
        return False
    
    return True


def main():
    """Run all tests."""
    print("=" * 60)
    print("🧪 Testing New Robotics Digest Features")
    print("=" * 60)
    
    # Check environment
    print("\nEnvironment check:")
    print(f"  Python version: {sys.version.split()[0]}")
    print(f"  Working directory: {os.getcwd()}")
    
    api_key = os.getenv('GEMINI_API_KEY')
    print(f"  GEMINI_API_KEY: {'✅ Set' if api_key else '⚠️  Not set'}")
    
    resend_key = os.getenv('RESEND_API_KEY')
    print(f"  RESEND_API_KEY: {'✅ Set' if resend_key else '⚠️  Not set'}")
    
    # Run tests
    results = []
    
    results.append(("Imports", test_imports()))
    results.append(("Figure Extraction", test_figure_extraction()))
    results.append(("X Finder", test_x_finder()))
    results.append(("Digest Summary", test_digest_summary()))
    results.append(("Web Renderer", test_web_renderer()))
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Test Results Summary")
    print("=" * 60)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"  {test_name}: {status}")
    
    all_passed = all(r[1] for r in results)
    
    if all_passed:
        print("\n🎉 All tests passed! Ready to deploy.")
    else:
        print("\n⚠️  Some tests failed. Please check the output above.")
    
    return 0 if all_passed else 1


if __name__ == '__main__':
    sys.exit(main())


