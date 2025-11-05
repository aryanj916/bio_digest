import re
import logging
import requests
from urllib.parse import quote_plus
from typing import Dict, Optional, List
from bs4 import BeautifulSoup
import time

logger = logging.getLogger(__name__)

class XFinder:
    """Find X/Twitter posts about papers using best-effort web search."""
    
    def __init__(self, config: dict):
        self.enabled = config.get('features', {}).get('include_x_posts', False)
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        }
    
    def find_x_post(self, paper: Dict) -> Dict:
        """Find X/Twitter post for a paper using best-effort search."""
        
        if not self.enabled:
            return paper
        
        arxiv_id = paper.get('arxiv_id', '').split('v')[0]
        if not arxiv_id:
            return paper
        
        # Try multiple search strategies
        x_url = None
        
        # Strategy 1: Search for arXiv ID
        x_url = self._search_for_arxiv_id(arxiv_id)
        
        # Strategy 2: Search for paper title (if first strategy fails)
        if not x_url and paper.get('title'):
            x_url = self._search_for_title(paper['title'], arxiv_id)
        
        if x_url:
            paper['x_url'] = x_url
            logger.info(f"Found X post for {arxiv_id}: {x_url}")
        else:
            logger.debug(f"No X post found for {arxiv_id}")
        
        return paper
    
    def _search_for_arxiv_id(self, arxiv_id: str) -> Optional[str]:
        """Search for X posts mentioning the arXiv ID."""
        
        # Try different search engines for better coverage
        
        # Method 1: DuckDuckGo HTML search
        url = self._search_duckduckgo(f'site:x.com "{arxiv_id}"')
        if url:
            return url
        
        # Method 2: Try with different query format
        url = self._search_duckduckgo(f'site:twitter.com OR site:x.com arxiv {arxiv_id}')
        if url:
            return url
        
        # Method 3: Google search (as fallback)
        url = self._search_google(f'site:x.com "{arxiv_id}"')
        if url:
            return url
        
        # Method 4: Try direct X search URL (simple fallback)
        url = self._search_direct_x(arxiv_id)
        if url:
            return url
        
        return None
    
    def _search_for_title(self, title: str, arxiv_id: str) -> Optional[str]:
        """Search for X posts mentioning the paper title."""
        
        # Clean and shorten title for search
        title_clean = re.sub(r'[^\w\s]', '', title)
        title_words = title_clean.split()[:8]  # Use first 8 words
        title_short = ' '.join(title_words)
        
        # Try searching for title
        query = f'site:x.com "{title_short}" arxiv'
        url = self._search_duckduckgo(query)
        
        if url:
            # Verify it's related to this paper (basic check)
            if self._verify_relevance(url, arxiv_id, title_words):
                return url
        
        return None
    
    def _search_duckduckgo(self, query: str) -> Optional[str]:
        """Search using DuckDuckGo HTML interface."""
        
        try:
            search_url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
            
            response = requests.get(
                search_url, 
                headers=self.headers, 
                timeout=10
            )
            
            # Handle redirects and blocking
            if response.status_code not in [200, 202]:
                logger.debug(f"DuckDuckGo returned status {response.status_code}")
                return None
            
            # If we get a 202, it might be a redirect - try to follow it
            if response.status_code == 202:
                # Try alternative DuckDuckGo endpoint
                alt_url = f"https://duckduckgo.com/html/?q={quote_plus(query)}"
                response = requests.get(alt_url, headers=self.headers, timeout=10)
                if response.status_code != 200:
                    logger.debug(f"DuckDuckGo alt endpoint returned status {response.status_code}")
                    return None
            
            # Parse HTML to find X.com links
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for result links
            for result in soup.find_all('a', class_='result__a'):
                href = result.get('href', '')
                
                # Extract actual URL from DuckDuckGo redirect
                if 'x.com' in href or 'twitter.com' in href:
                    # DuckDuckGo wraps URLs, extract the actual URL
                    match = re.search(r'uddg=(https?://(?:x\.com|twitter\.com)/[^&]+)', href)
                    if match:
                        actual_url = match.group(1)
                        # Clean up URL
                        actual_url = re.sub(r'%3F.*$', '', actual_url)  # Remove encoded params
                        actual_url = actual_url.replace('%2F', '/')
                        
                        # Validate it's a status URL
                        if '/status/' in actual_url:
                            return actual_url
            
            # Alternative parsing for direct links
            for link in soup.find_all('a'):
                href = link.get('href', '')
                if 'x.com' in href and '/status/' in href:
                    # Extract clean URL
                    match = re.search(r'(https?://x\.com/\w+/status/\d+)', href)
                    if match:
                        return match.group(1)
            
        except Exception as e:
            logger.debug(f"DuckDuckGo search failed: {e}")
        
        return None
    
    def _search_google(self, query: str) -> Optional[str]:
        """Search using Google (as fallback, may be rate-limited)."""
        
        try:
            # Note: This is fragile and may be blocked
            search_url = f"https://www.google.com/search?q={quote_plus(query)}"
            
            response = requests.get(
                search_url,
                headers=self.headers,
                timeout=10
            )
            
            if response.status_code != 200:
                return None
            
            # Look for X.com URLs in the response
            matches = re.findall(
                r'https?://(?:x\.com|twitter\.com)/\w+/status/\d+',
                response.text
            )
            
            if matches:
                # Return first valid match
                return matches[0]
            
        except Exception as e:
            logger.debug(f"Google search failed: {e}")
        
        return None
    
    def _search_direct_x(self, arxiv_id: str) -> Optional[str]:
        """Try direct X search URL as a simple fallback."""
        
        # For now, return None as X search is unreliable
        # The search engines are blocking automated requests
        # and X's search API is not publicly accessible
        
        logger.debug(f"X search disabled - search engines blocking automated requests")
        return None
    
    def _validate_x_post(self, url: str, arxiv_id: str) -> bool:
        """Validate that an X post actually mentions the arXiv ID."""
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code == 200:
                # Check if the arXiv ID appears in the post content
                return arxiv_id in response.text
        except Exception as e:
            logger.debug(f"Failed to validate X post {url}: {e}")
        
        return False
    
    def _verify_relevance(self, url: str, arxiv_id: str, title_words: list) -> bool:
        """Basic verification that the X post is about this paper."""
        
        # For now, just accept any result
        # Could enhance by fetching the page and checking content
        # But that would be slower and more fragile
        
        return True
    
    def batch_find(self, papers: List[Dict]) -> List[Dict]:
        """Find X posts for multiple papers with rate limiting."""
        
        if not self.enabled:
            return papers
        
        logger.info(f"Searching for X posts for {len(papers)} papers...")
        
        for i, paper in enumerate(papers):
            paper = self.find_x_post(paper)
            
            # Rate limiting to be respectful
            if i < len(papers) - 1:
                time.sleep(0.5)  # 500ms between searches
        
        x_found = sum(1 for p in papers if 'x_url' in p)
        logger.info(f"Found X posts for {x_found}/{len(papers)} papers")
        
        return papers


