import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class BioRxivFetcher:
    """Fetches papers from bioRxiv and medRxiv using their public API."""
    
    BASE_URL = "https://api.biorxiv.org/details"
    
    def __init__(self, categories: List[str], days_lookback: int = 1):
        """
        Initialize bioRxiv/medRxiv fetcher.
        
        Args:
            categories: List of repositories to fetch from (e.g., ['biorxiv', 'medrxiv'])
            days_lookback: Number of days to look back for papers
        """
        self.categories = categories  # 'biorxiv', 'medrxiv', or both
        self.days_lookback = days_lookback
    
    def fetch(self) -> List[Dict]:
        """Fetch papers from bioRxiv and/or medRxiv."""
        all_papers = []
        seen_ids = set()
        
        # Get date range
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.days_lookback)
        
        for category in self.categories:
            logger.info(f"Fetching papers from {category}")
            
            try:
                papers = self._fetch_category(category, start_date, end_date)
                
                # Deduplicate
                for paper in papers:
                    paper_id = paper.get('biorxiv_id') or paper.get('doi', '')
                    if paper_id and paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        all_papers.append(paper)
                
                logger.info(f"Fetched {len(papers)} papers from {category}")
                
            except Exception as e:
                logger.error(f"Error fetching from {category}: {e}")
                continue
        
        logger.info(f"Total unique papers from bioRxiv/medRxiv: {len(all_papers)}")
        return all_papers
    
    def _fetch_category(self, category: str, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Fetch papers from a specific category (biorxiv or medrxiv)."""
        papers = []
        
        # Format dates as YYYY-MM-DD
        start_str = start_date.strftime('%Y-%m-%d')
        end_str = end_date.strftime('%Y-%m-%d')
        
        # Build URL: https://api.biorxiv.org/details/[server]/[start_date]/[end_date]/[cursor]
        cursor = 0
        
        while True:
            url = f"{self.BASE_URL}/{category}/{start_str}/{end_str}/{cursor}"
            
            try:
                logger.debug(f"Fetching from: {url}")
                response = requests.get(url, timeout=30)
                response.raise_for_status()
                
                data = response.json()
                
                # Check if we got results
                if 'collection' not in data or not data['collection']:
                    logger.debug(f"No more results for {category} at cursor {cursor}")
                    break
                
                # Parse papers
                for item in data['collection']:
                    paper = self._parse_paper(item, category)
                    if paper:
                        papers.append(paper)
                
                # Check if there are more results
                # bioRxiv API returns up to 100 results per request
                # If we got less than 100, we're done
                if len(data['collection']) < 100:
                    break
                
                cursor += len(data['collection'])
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Request error for {category}: {e}")
                break
            except Exception as e:
                logger.error(f"Error parsing {category} response: {e}")
                break
        
        return papers
    
    def _parse_paper(self, item: Dict, source: str) -> Optional[Dict]:
        """Parse a bioRxiv/medRxiv paper into our standard format."""
        try:
            # Extract DOI (unique identifier)
            doi = item.get('doi', '')
            if not doi:
                return None
            
            # Create bioRxiv ID (remove version from DOI)
            biorxiv_id = doi.split('v')[0] if 'v' in doi else doi
            
            # Parse dates
            published_str = item.get('date', '')
            published = self._parse_date(published_str)
            
            # Get version
            version = item.get('version', '1')
            try:
                version = int(version.replace('v', ''))
            except:
                version = 1
            
            # Authors (semicolon separated)
            authors_str = item.get('authors', '')
            authors = [a.strip() for a in authors_str.split(';') if a.strip()]
            
            # Category
            category = item.get('category', 'Unknown')
            
            # Build URLs
            arxiv_link = f"https://www.biorxiv.org/content/{doi}"
            if source == 'medrxiv':
                arxiv_link = f"https://www.medrxiv.org/content/{doi}"
            
            pdf_link = f"{arxiv_link}.full.pdf"
            
            return {
                'biorxiv_id': biorxiv_id,
                'doi': doi,
                'title': item.get('title', '').strip(),
                'abstract': item.get('abstract', '').strip(),
                'authors': authors,
                'categories': [category],
                'primary_category': f"{source}/{category}",
                'published': published.isoformat() if published else None,
                'updated': published.isoformat() if published else None,
                'pdf_link': pdf_link,
                'arxiv_link': arxiv_link,
                'biorxiv_link': arxiv_link,
                'comments': '',
                'version': version,
                'source': source
            }
            
        except Exception as e:
            logger.error(f"Error parsing paper: {e}")
            return None
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        
        try:
            # bioRxiv dates are in format YYYY-MM-DD
            return datetime.strptime(date_str, '%Y-%m-%d').replace(tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Error parsing date '{date_str}': {e}")
            return None

