import feedparser
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import pytz
from dateutil import parser as date_parser

logger = logging.getLogger(__name__)

class RSSFetcher:
    """Fetches papers from arXiv RSS/Atom feeds."""
    
    BASE_URL = "https://rss.arxiv.org/atom"
    
    def __init__(self, categories: List[str], hours_lookback: int = 48, config: dict = None):
        self.categories = categories
        self.hours_lookback = hours_lookback
        self.et_tz = pytz.timezone('America/New_York')
        self.config = config or {}
    
    def fetch(self) -> List[Dict]:
        """Fetch papers from RSS feeds for all configured categories."""
        all_entries = []
        seen_ids = set()
        
        # Fetch each category separately to avoid URL length issues
        for category in self.categories:
            url = f"{self.BASE_URL}/{category}"
            logger.info(f"Fetching RSS feed for {category} from {url}")
            
            try:
                feed = feedparser.parse(url)
                
                if feed.bozo:
                    logger.warning(f"Feed parsing warning for {category}: {feed.bozo_exception}")
                
                logger.info(f"Found {len(feed.entries)} entries in {category} feed")
                
                for entry in feed.entries:
                    paper = self._parse_entry(entry, category)
                    
                    # Deduplicate by arXiv ID
                    if paper['arxiv_id'] not in seen_ids:
                        seen_ids.add(paper['arxiv_id'])
                        all_entries.append(paper)
                        logger.debug(f"Added paper: {paper['arxiv_id']} - {paper['title'][:50]}...")
                
                logger.info(f"Processed {len(feed.entries)} entries from {category}")
                
            except Exception as e:
                logger.error(f"Error fetching {category}: {e}")
                continue
        
        # Filter by date
        filtered = self._filter_by_date(all_entries)
        logger.info(f"Total unique papers after date filter: {len(filtered)}")
        
        # Log some sample titles for debugging
        if filtered:
            logger.info("Sample papers fetched:")
            for paper in filtered[:5]:
                logger.info(f"  - {paper['arxiv_id']}: {paper['title'][:60]}...")
        
        return filtered
    
    def _parse_entry(self, entry: Dict, category: str) -> Dict:
        """Parse a feed entry into our standard format."""
        # Extract arXiv ID from the entry ID
        # Handle both formats: "oai:arXiv.org:2508.10269v1" and "http://arxiv.org/abs/2508.10269v1"
        entry_id = entry.id if 'id' in entry else ''
        if 'oai:arXiv.org:' in entry_id:
            arxiv_id = entry_id.replace('oai:arXiv.org:', '')
        elif 'arxiv.org/abs/' in entry_id:
            arxiv_id = entry_id.split('/')[-1]
        else:
            arxiv_id = entry_id.split('/')[-1] if entry_id else ''
        
        # Parse dates
        published = self._parse_date(entry.get('published', ''))
        updated = self._parse_date(entry.get('updated', ''))
        
        # Extract authors
        authors = []
        if 'authors' in entry:
            authors = [author.get('name', '') for author in entry.authors]
        elif 'author_detail' in entry:
            authors = [entry.author_detail.get('name', '')]
        elif 'author' in entry:
            authors = [entry.author]
        
        # Extract categories from tags
        categories = []
        if 'tags' in entry:
            categories = [tag.get('term', '') for tag in entry.tags]
        
        # Get PDF link
        pdf_link = f"https://arxiv.org/pdf/{arxiv_id}.pdf" if arxiv_id else ''
        
        # Get arXiv page link
        if 'link' in entry:
            arxiv_link = entry.link
        else:
            arxiv_link = f"https://arxiv.org/abs/{arxiv_id}" if arxiv_id else ''
        
        # Extract comments (may contain code/data links)
        comments = entry.get('arxiv_comment', '')
        
        return {
            'arxiv_id': arxiv_id,
            'title': entry.get('title', '').replace('\n', ' ').strip(),
            'abstract': entry.get('summary', '').replace('\n', ' ').strip(),
            'authors': authors,
            'categories': categories,
            'primary_category': category,
            'published': published,
            'updated': updated,
            'pdf_link': pdf_link,
            'arxiv_link': arxiv_link,
            'comments': comments,
            'version': self._extract_version(arxiv_id)
        }
    
    def _parse_date(self, date_str: str) -> Optional[datetime]:
        """Parse date string to datetime object."""
        if not date_str:
            return None
        try:
            return date_parser.parse(date_str)
        except:
            return None
    
    def _extract_version(self, arxiv_id: str) -> int:
        """Extract version number from arXiv ID."""
        if 'v' in arxiv_id:
            try:
                return int(arxiv_id.split('v')[-1])
            except:
                pass
        return 1
    
    def _filter_by_date(self, entries: List[Dict]) -> List[Dict]:
        """Filter entries to only include recent papers."""
        cutoff = datetime.now(timezone.utc) - timedelta(hours=self.hours_lookback)
        
        logger.info(f"Filtering papers published after {cutoff}")
        
        filtered = []
        only_new = self.config.get('digest', {}).get('fetch', {}).get('only_new_submissions', False)
        
        for entry in entries:
            # For new submissions only, use published date
            # For all papers, use updated date
            if only_new:
                entry_date = entry.get('published')
                # Skip updates (v2, v3, etc.)
                if entry.get('version', 1) > 1:
                    logger.debug(f"Skipping update v{entry.get('version')}: {entry['title'][:50]}...")
                    continue
            else:
                entry_date = entry.get('updated') or entry.get('published')
            
            if entry_date and entry_date > cutoff:
                filtered.append(entry)
                logger.debug(f"Keeping paper from {entry_date}: {entry['title'][:50]}...")
            elif entry_date:
                logger.debug(f"Filtering out old paper from {entry_date}: {entry['title'][:50]}...")
        
        logger.info(f"Kept {len(filtered)} papers (new submissions only: {only_new})")
        return filtered