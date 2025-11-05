import re
import logging
from typing import List, Dict, Set, Tuple
import yaml

logger = logging.getLogger(__name__)

class HeuristicFilter:
    """Fast heuristic filtering and scoring for papers."""
    
    def __init__(self, config: dict):
        self.config = config
        self.boost_terms = config['digest']['boost_terms']
        self.drop_terms = config['digest']['drop_terms']
        self.greylist_terms = config['digest']['greylist_terms']
        self.greylist_keep_keywords = config['digest']['greylist_keep_if_keywords']
        self.buckets = config['buckets']
        
        # Compile regex patterns for efficiency
        self._compile_patterns()
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for all terms."""
        self.boost_patterns = {}
        for level, terms in self.boost_terms.items():
            self.boost_patterns[level] = [
                re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE) 
                for term in terms
            ]
        
        self.drop_patterns = [
            re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for term in self.drop_terms
        ]
        
        self.greylist_patterns = [
            re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for term in self.greylist_terms
        ]
        
        self.greylist_keep_patterns = [
            re.compile(r'\b' + re.escape(term) + r'\b', re.IGNORECASE)
            for term in self.greylist_keep_keywords
        ]
    
    def pre_filter(self, papers: List[Dict]) -> List[Dict]:
        """
        Apply fast pre-filtering to remove obvious non-targets.
        Returns filtered list of papers with initial scores.
        """
        filtered = []
        
        for paper in papers:
            text = f"{paper['title']} {paper['abstract']}"
            
            # Check for hard drop terms (unless boost terms present)
            if self._should_drop(text):
                logger.debug(f"Dropping paper {paper['arxiv_id']}: hard drop term")
                continue
            
            # Check greylist (keep if transferable methods present)
            if self._is_greylisted(text):
                if not self._has_transferable_methods(text):
                    logger.debug(f"Dropping paper {paper['arxiv_id']}: greylisted without transferable methods")
                    continue
                paper['greylisted'] = True
            
            # Calculate initial heuristic score
            paper['heuristic_score'] = self._calculate_score(text)
            paper['detected_buckets'] = self._detect_buckets(text)
            
            filtered.append(paper)
        
        logger.info(f"Pre-filtered {len(papers)} papers to {len(filtered)}")
        return filtered
    
    def _should_drop(self, text: str) -> bool:
        """Check if paper should be hard dropped."""
        has_drop = any(pattern.search(text) for pattern in self.drop_patterns)
        if not has_drop:
            return False
        
        # Check if any boost terms present (override drop)
        for patterns in self.boost_patterns.values():
            if any(p.search(text) for p in patterns):
                return False
        
        return True
    
    def _is_greylisted(self, text: str) -> bool:
        """Check if paper is in greylist category."""
        return any(pattern.search(text) for pattern in self.greylist_patterns)
    
    def _has_transferable_methods(self, text: str) -> bool:
        """Check if greylisted paper has transferable methods."""
        return any(pattern.search(text) for pattern in self.greylist_keep_patterns)
    
    def _calculate_score(self, text: str) -> float:
        """Calculate heuristic relevance score based on keywords."""
        score = 0.0
        
        # High priority terms (20 points each)
        for pattern in self.boost_patterns.get('high', []):
            matches = len(pattern.findall(text))
            score += matches * 20
        
        # Medium priority terms (10 points each)
        for pattern in self.boost_patterns.get('medium', []):
            matches = len(pattern.findall(text))
            score += matches * 10
        
        # Low priority terms (5 points each)
        for pattern in self.boost_patterns.get('low', []):
            matches = len(pattern.findall(text))
            score += matches * 5
        
        # Base score for biomedical AI papers
        text_lower = text.lower()
        if any(term in text_lower for term in ['machine learning', 'deep learning', 'neural network', 'ai']):
            if any(term in text_lower for term in ['medical', 'clinical', 'patient', 'drug', 'protein', 'diagnostic', 'healthcare']):
                score += 20
        
        return min(score, 100)  # Cap at 100
    
    def _detect_buckets(self, text: str) -> List[str]:
        """Detect which buckets this paper might belong to."""
        detected = []
        
        for bucket in self.buckets:
            bucket_name = bucket['name']
            keywords = bucket['keywords']
            
            for keyword in keywords:
                if re.search(r'\b' + re.escape(keyword) + r'\b', text, re.IGNORECASE):
                    detected.append(bucket_name)
                    break
        
        return detected
    
    def extract_links(self, paper: Dict) -> Tuple[List[str], List[str]]:
        """Extract code and dataset links from paper text and comments."""
        code_urls = []
        dataset_urls = []
        
        text = f"{paper.get('abstract', '')} {paper.get('comments', '')}"
        
        # GitHub patterns
        github_pattern = r'(https?://github\.com/[\w\-/]+)'
        code_urls.extend(re.findall(github_pattern, text))
        
        # GitLab patterns
        gitlab_pattern = r'(https?://gitlab\.com/[\w\-/]+)'
        code_urls.extend(re.findall(gitlab_pattern, text))
        
        # Project page patterns
        project_pattern = r'(https?://[\w\-\.]+\.github\.io/[\w\-/]+)'
        code_urls.extend(re.findall(project_pattern, text))
        
        # Dataset patterns (common dataset hosts)
        dataset_patterns = [
            r'(https?://[\w\-\.]*huggingface\.co/datasets/[\w\-/]+)',
            r'(https?://[\w\-\.]*kaggle\.com/[\w\-/]+)',
            r'(https?://[\w\-\.]*zenodo\.org/[\w\-/]+)',
        ]
        
        for pattern in dataset_patterns:
            dataset_urls.extend(re.findall(pattern, text))
        
        # Remove duplicates while preserving order
        code_urls = list(dict.fromkeys(code_urls))
        dataset_urls = list(dict.fromkeys(dataset_urls))
        
        return code_urls, dataset_urls