import google.generativeai as genai
import json
import logging
from typing import List, Dict
from tenacity import retry, stop_after_attempt, wait_exponential

logger = logging.getLogger(__name__)

class DigestSummarizer:
    """Generate a digestible summary of today's papers."""
    
    def __init__(self, api_key: str):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def generate_summary(self, papers: List[Dict]) -> Dict:
        """Generate a digest summary of today's papers."""
        
        if not papers:
            return {
                'headline': 'No relevant papers today',
                'bullets': [],
                'highlights': []
            }
        
        # Prepare paper summaries for the prompt
        paper_summaries = []
        for p in papers:
            paper_summaries.append({
                'title': p.get('title', ''),
                'score': p.get('final_score', p.get('relevance_score', 0)),
                'buckets': p.get('buckets', []),
                'why_matters': p.get('why_it_matters', ''),
                'summary': p.get('summary', ''),
                'has_code': bool(p.get('code_urls')),
                'has_dataset': bool(p.get('dataset_urls'))
            })
        
        prompt = f"""You are a biomedical AI research analyst focused on neurotech, biotech startups, and clinical AI innovation.
        
Create a concise digest summary of today's research papers for researchers and clinicians.

Focus on:
- Clinical breakthroughs and patient impact
- Novel AI/ML methods for healthcare
- Drug discovery and biotech innovations
- Neuroscience and brain-computer interface advances
- Any datasets or code releases that advance the field

Papers to summarize:
{json.dumps(paper_summaries, indent=2)[:15000]}

Output JSON with this structure:
{{
    "headline": "One-line summary of today's key theme (max 100 chars)",
    "bullets": [
        "3-6 actionable bullet points about clinical impact, methods, or breakthroughs",
        "Focus on what matters for biotech innovation and patient outcomes",
        "Mention specific papers when relevant"
    ],
    "highlights": [
        "0-3 specific callouts about notable results, datasets, or clinical applications"
    ]
}}

Be specific and clinically relevant. Highlight real-world impact on healthcare and biotech."""
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    'response_mime_type': 'application/json',
                    'temperature': 0.3,
                    'top_p': 0.95
                }
            )
            
            result = json.loads(response.text)
            
            # Validate structure
            if 'headline' not in result:
                result['headline'] = f"{len(papers)} papers on robotics and manipulation"
            if 'bullets' not in result or not result['bullets']:
                result['bullets'] = [f"Found {len(papers)} relevant papers today"]
            if 'highlights' not in result:
                result['highlights'] = []
            
            # Truncate headline if too long
            if len(result['headline']) > 100:
                result['headline'] = result['headline'][:97] + '...'
            
            logger.info(f"Generated digest summary: {result['headline']}")
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate summary: {e}")
            return {
                'headline': f"Today's digest: {len(papers)} papers on biomedical AI & healthcare",
                'bullets': [
                    f"Found {len(papers)} relevant papers across {len(set(b for p in papers for b in p.get('buckets', [])))} categories",
                    f"Top paper scored {max(p.get('final_score', 0) for p in papers):.0f}/100"
                ],
                'highlights': []
            }


