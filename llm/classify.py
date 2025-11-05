import google.generativeai as genai
import json
import logging
from typing import List, Dict, Optional
from tenacity import retry, stop_after_attempt, wait_exponential
import os

logger = logging.getLogger(__name__)

class GeminiClassifier:
    """Classify papers using Gemini 2.5 Pro with structured output."""
    
    def __init__(self, api_key: str, config: dict):
        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel('gemini-2.5-pro')
        self.config = config
        self.buckets = config['buckets']
        
        # Build the system prompt
        self.system_prompt = self._build_system_prompt()
        
        # Define the response schema (WITHOUT minimum/maximum constraints)
        self.response_schema = {
            "type": "object",
            "properties": {
                "keep": {"type": "boolean"},
                "relevance_score": {"type": "number"},  # Removed minimum/maximum
                "buckets": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "why_it_matters": {"type": "string"},
                "summary": {"type": "string"},
                "code_urls": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "dataset_urls": {
                    "type": "array",
                    "items": {"type": "string"}
                },
                "risk_flags": {
                    "type": "array",
                    "items": {"type": "string"}
                }
            },
            "required": ["keep", "relevance_score", "buckets", "why_it_matters", "summary"]
        }
    
    def _build_system_prompt(self) -> str:
        """Build the system prompt for Gemini."""
        bucket_descriptions = "\n".join([
            f"- {b['name']}: {', '.join(b['keywords'])}"
            for b in self.buckets
        ])
        
        return f"""You are a biomedical AI research analyst focused on innovations in AI for medicine, healthcare, biotechnology, and drug discovery.

Your job is to evaluate research papers for relevance to neurotech, biotech startups, and clinical AI applications, and classify them into appropriate categories.

BUCKETS FOR CLASSIFICATION:
{bucket_descriptions}

EVALUATION CRITERIA - BE VERY SELECTIVE:
1. High relevance (80-100): Direct clinical impact or major breakthrough
   - FDA-approved or in clinical trials
   - Validated on real patient data with strong results
   - Major breakthrough in drug discovery or protein modeling
   - Novel AI methods with clear clinical applications
   
2. Good relevance (60-79): Strong potential for clinical translation
   - Validated methods ready for clinical testing
   - Significant improvements in biomarker discovery
   - Novel ML/AI approaches for healthcare problems
   - Strong results on established medical benchmarks
   
3. Medium relevance (40-59): Interesting AI methods for biomedical problems
   - Computational methods with medical applications
   - Early-stage research with potential
   - Datasets or benchmarks for medical AI
   
4. Low relevance (20-39): Tangentially related
   - Basic ML without clear medical application
   - Incremental improvements only
   
5. Not relevant (0-19): Outside scope
   - No AI/ML component
   - Pure chemistry without computational methods
   - Veterinary-only without human translation

BE SELECTIVE - WE ONLY WANT THE BEST PAPERS:
- Set keep=true ONLY for papers with relevance_score >= 40
- We are specifically interested in:
  * AI diagnostics and medical imaging analysis
  * Drug discovery and compound screening using ML/AI
  * Protein folding and molecular modeling (AlphaFold-style)
  * Clinical decision support and predictive analytics
  * Brain-computer interfaces and neuroscience AI
  * EEG/fNIRS and biosignal analysis
  * Healthcare LLMs and clinical NLP
  * Validated on real patient/clinical data

DROP PAPER IF:
- Pure statistics without modern ML/AI methods
- Pure chemistry/biology without computational component
- Animal studies only without clear human translation path
- Theoretical work without validation
- No clear clinical or biotech application
- Incremental improvements on narrow problems
- Pure software engineering without medical innovation

For greylisted topics (animal models, in vitro only), keep ONLY if they include:
- Novel AI/ML methods applicable to human medicine
- Clear path to clinical translation
- Breakthrough results that change the field

RISK FLAGS to identify:
- "in-vitro-only": No validation beyond lab experiments
- "no-validation": Purely theoretical or simulated
- "small-sample": Very limited dataset (n < 50)
- "no-code": No code repository mentioned
- "animal-only": No clear human translation path
- "narrow-domain": Very specific niche application

For the TOP PICKS (relevance_score >= 80), provide a detailed 3-4 sentence summary explaining:
- The clinical problem being solved
- The AI/ML methodology used
- Key results and potential impact on patient outcomes or biotech innovation

For others, keep the summary to 1-2 sentences.

Extract any GitHub, GitLab, project page, or dataset URLs from the abstract and comments.

IMPORTANT: Return relevance_score as a number between 0 and 100. Be selective - most papers should score below 60. Focus on papers that could actually impact patient care, drug discovery, or neurotech applications."""
    
    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def classify_single(self, paper: Dict) -> Dict:
        """Classify a single paper."""
        prompt = self._build_paper_prompt(paper)
        
        try:
            response = self.model.generate_content(
                prompt,
                generation_config={
                    "response_mime_type": "application/json",
                    "response_schema": self.response_schema,
                    "temperature": 0.3,
                    "top_p": 0.95,
                }
            )
            
            result = json.loads(response.text)
            
            # Validate relevance_score is within bounds
            if 'relevance_score' in result:
                result['relevance_score'] = max(0, min(100, result['relevance_score']))
            
            # Detailed logging for debugging
            title = paper.get('title', '')[:60] + "..."
            arxiv_id = paper.get('arxiv_id', '')
            
            logger.info(f"\n{'='*80}")
            logger.info(f"📄 PAPER: {arxiv_id}")
            logger.info(f"📝 TITLE: {paper.get('title', '')}")
            logger.info(f"🏷️  CATEGORIES: {', '.join(paper.get('categories', []))}")
            logger.info(f"📋 ABSTRACT: {paper.get('abstract', '')[:200]}...")
            
            if result.get('keep', False):
                logger.info(f"✅ DECISION: KEEP")
                logger.info(f"📊 SCORE: {result.get('relevance_score')}/100")
                logger.info(f"🎯 BUCKETS: {', '.join(result.get('buckets', []))}")
                logger.info(f"💡 WHY IT MATTERS: {result.get('why_it_matters', '')}")
                logger.info(f"📝 SUMMARY: {result.get('summary', '')}")
            else:
                logger.info(f"❌ DECISION: DROP")
                logger.info(f"📊 SCORE: {result.get('relevance_score')}/100")
                logger.info(f"💡 WHY IT MATTERS: {result.get('why_it_matters', '')}")
                logger.info(f"📝 SUMMARY: {result.get('summary', '')}")
            
            # Log any risk flags
            risk_flags = result.get('risk_flags', [])
            if risk_flags:
                logger.info(f"⚠️  RISK FLAGS: {', '.join(risk_flags)}")
            
            # Log any detected URLs
            code_urls = result.get('code_urls', [])
            dataset_urls = result.get('dataset_urls', [])
            if code_urls:
                logger.info(f"🔗 CODE URLs: {', '.join(code_urls)}")
            if dataset_urls:
                logger.info(f"📊 DATASET URLs: {', '.join(dataset_urls)}")
            
            logger.info(f"{'='*80}")
            
            # Merge with paper data
            paper.update(result)
            
            # Add any heuristically detected links
            from rules.heuristics import HeuristicFilter
            heuristic = HeuristicFilter(self.config)
            code_urls, dataset_urls = heuristic.extract_links(paper)
            
            # Merge URLs (avoiding duplicates)
            paper['code_urls'] = list(set(paper.get('code_urls', []) + code_urls))
            paper['dataset_urls'] = list(set(paper.get('dataset_urls', []) + dataset_urls))
            
            return paper
            
        except Exception as e:
            logger.error(f"  ⚠️ ERROR classifying {paper.get('arxiv_id')}: {e}")
            logger.error(f"     Title: {paper.get('title')[:60]}...")
            # Return with default values but mark as robotics-related for debugging
            paper.update({
                'keep': True,  # Keep by default for debugging
                'relevance_score': 30,  # Low score
                'buckets': [],
                'why_it_matters': f'Classification failed: {str(e)}',
                'summary': 'Classification error - marked for review',
                'error': str(e)
            })
            return paper
    
    def classify_batch(self, papers: List[Dict], batch_size: int = 5) -> List[Dict]:
        """Classify papers in batches for efficiency."""
        classified = []
        
        logger.info(f"Starting classification of {len(papers)} papers...")
        
        for i in range(0, len(papers), batch_size):
            batch = papers[i:i+batch_size]
            
            # For simplicity, process one by one
            # (Gemini structured output works best with single items)
            for paper in batch:
                result = self.classify_single(paper)
                classified.append(result)
                
                logger.info(f"Classified {paper['arxiv_id']}: "
                          f"keep={result.get('keep')}, "
                          f"score={result.get('relevance_score')}")
        
        # Log summary
        kept = [p for p in classified if p.get('keep', False)]
        logger.info(f"Classification complete: {len(kept)}/{len(classified)} papers kept")
        
        return classified
    
    def _build_paper_prompt(self, paper: Dict) -> str:
        """Build prompt for a single paper."""
        # Include detected buckets from heuristics as hints
        bucket_hints = paper.get('detected_buckets', [])
        bucket_hint_str = f"\nHeuristic bucket hints: {', '.join(bucket_hints)}" if bucket_hints else ""
        
        return f"""{self.system_prompt}

PAPER TO EVALUATE:
Title: {paper['title']}
Categories: {', '.join(paper.get('categories', []))}
Abstract: {paper['abstract']}
Comments: {paper.get('comments', 'None')}
{bucket_hint_str}

Provide your evaluation as JSON matching the schema."""