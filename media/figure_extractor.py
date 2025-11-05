import re
import os
import logging
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from typing import Dict, Optional

logger = logging.getLogger(__name__)

class FigureExtractor:
    """Extract key figures from arXiv papers using HTML versions."""
    
    def __init__(self, config: dict):
        self.config = config
        self.prefer_ar5iv = config.get('media', {}).get('prefer_ar5iv', True)
        self.headers = {
            'User-Agent': 'MindCoDigestBot/1.0 (+https://github.com/aryanj916/bio_digest)'
        }
    
    def extract_figure(self, paper: Dict) -> Dict:
        """Try to extract a key figure for the paper."""
        arxiv_id = paper.get('arxiv_id', '').split('v')[0]
        
        if not arxiv_id:
            return paper
        
        figure_url = None
        
        # Try different sources in order of preference
        if self.prefer_ar5iv:
            # Try ar5iv first (better HTML rendering)
            figure_url = self._extract_from_ar5iv(arxiv_id)
            if not figure_url:
                # Fall back to arXiv HTML
                figure_url = self._extract_from_arxiv_html(arxiv_id)
        else:
            # Try arXiv HTML first
            figure_url = self._extract_from_arxiv_html(arxiv_id)
            if not figure_url:
                # Fall back to ar5iv
                figure_url = self._extract_from_ar5iv(arxiv_id)
        
        # If still no figure, try to get from abstract page
        if not figure_url:
            figure_url = self._extract_from_abstract_page(arxiv_id)
        
        if figure_url:
            paper['figure_url'] = figure_url
            logger.info(f"Found figure for {arxiv_id}: {figure_url}")
        else:
            # Mark for PDF preview generation
            paper['needs_pdf_preview'] = True
            logger.debug(f"No figure found for {arxiv_id}, will generate PDF preview")
        
        return paper
    
    def _extract_from_ar5iv(self, arxiv_id: str) -> Optional[str]:
        """Extract figure from ar5iv HTML version."""
        url = f"https://ar5iv.org/html/{arxiv_id}"
        base_url = url if url.endswith('/') else url + '/'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for first meaningful figure
            figure = soup.find('figure', class_='ltx_figure')
            if figure:
                img = figure.find('img')
                if img and img.get('src'):
                    return urljoin(base_url, img['src'])
            
            # Alternative: look for first large image
            for img in soup.find_all('img'):
                src = img.get('src', '')
                # Filter out small icons and math symbols
                if 'ltx_graphics' in img.get('class', []) or \
                   (img.get('width') and int(img.get('width', 0)) > 200):
                    return urljoin(base_url, src)
            
        except Exception as e:
            logger.debug(f"Failed to extract from ar5iv for {arxiv_id}: {e}")
        
        return None
    
    def _extract_from_arxiv_html(self, arxiv_id: str) -> Optional[str]:
        """Extract figure from arXiv's native HTML version."""
        url = f"https://arxiv.org/html/{arxiv_id}"
        base_url = url if url.endswith('/') else url + '/'
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for figures
            figure = soup.find('figure')
            if figure:
                img = figure.find('img')
                if img and img.get('src'):
                    return urljoin(base_url, img['src'])
            
            # Look for any reasonably sized image
            for img in soup.find_all('img'):
                # Check if it's a meaningful image
                width = img.get('width')
                height = img.get('height')
                if width and height:
                    try:
                        w = int(width)
                        h = int(height)
                        if max(w, h) >= 300:
                            return urljoin(base_url, img.get('src'))
                    except:
                        pass
            
        except Exception as e:
            logger.debug(f"Failed to extract from arXiv HTML for {arxiv_id}: {e}")
        
        return None
    
    def _extract_from_abstract_page(self, arxiv_id: str) -> Optional[str]:
        """Try to find ancillary files or linked images from abstract page."""
        url = f"https://arxiv.org/abs/{arxiv_id}"
        
        try:
            response = requests.get(url, headers=self.headers, timeout=10)
            if response.status_code != 200:
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Look for ancillary files section
            ancillary = soup.find('div', class_='ancillary')
            if ancillary:
                for link in ancillary.find_all('a'):
                    href = link.get('href', '')
                    if re.search(r'\.(png|jpg|jpeg|gif)$', href, re.IGNORECASE):
                        return urljoin(url, href)
            
        except Exception as e:
            logger.debug(f"Failed to extract from abstract page for {arxiv_id}: {e}")
        
        return None


