import arxiv
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import re

logger = logging.getLogger(__name__)

class SearchAPIFetcher:
    """Supplementary fetcher using arXiv search API for more complex queries."""
    
    def __init__(self, max_results: int = 200):
        self.max_results = max_results
        self.client = arxiv.Client()
    
    def fetch_by_query(self, query: str, days_back: int = 2) -> List[Dict]:
        """
        Fetch papers using search API with custom query.
        Example query: 'cat:cs.RO AND (ti:manipulation OR abs:grasp)'
        """
        papers = []
        
        try:
            search = arxiv.Search(
                query=query,
                max_results=self.max_results,
                sort_by=arxiv.SortCriterion.SubmittedDate,
                sort_order=arxiv.SortOrder.Descending
            )
            
            cutoff = datetime.now() - timedelta(days=days_back)
            
            for result in self.client.results(search):
                # Filter by date
                if result.published < cutoff:
                    break
                
                papers.append(self._parse_result(result))
            
            logger.info(f"Fetched {len(papers)} papers from search API")
            
        except Exception as e:
            logger.error(f"Error fetching from search API: {e}")
        
        return papers
    
    def _parse_result(self, result) -> Dict:
        """Parse arXiv Result object to our standard format."""
        # Extract arXiv ID
        arxiv_id = result.entry_id.split('/')[-1]
        
        # Extract code/data links from comments
        comments = result.comment or ''
        
        return {
            'arxiv_id': arxiv_id,
            'title': result.title.replace('\n', ' ').strip(),
            'abstract': result.summary.replace('\n', ' ').strip(),
            'authors': [author.name for author in result.authors],
            'categories': result.categories,
            'primary_category': result.primary_category,
            'published': result.published,
            'updated': result.updated,
            'pdf_link': result.pdf_url,
            'arxiv_link': result.entry_id,
            'comments': comments,
            'version': self._extract_version(arxiv_id)
        }
    
    def _extract_version(self, arxiv_id: str) -> int:
        """Extract version number from arXiv ID."""
        match = re.search(r'v(\d+)$', arxiv_id)
        return int(match.group(1)) if match else 1