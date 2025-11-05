import os
import logging
from jinja2 import Template
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

logger = logging.getLogger(__name__)

class WebRenderer:
    """Render interactive web view with collapsible categories."""
    
    def __init__(self, config: dict):
        self.config = config
        self.template = self._load_template()
        
        # Setup output directories
        self.web_dir = Path('web')
        self.assets_dir = self.web_dir / 'assets'
        self.web_dir.mkdir(exist_ok=True)
        self.assets_dir.mkdir(exist_ok=True)
    
    def _load_template(self) -> Template:
        """Load the web template."""
        template_path = os.path.join(
            os.path.dirname(__file__), 
            'web_template.html'
        )
        
        with open(template_path, 'r') as f:
            template_str = f.read()
        
        return Template(template_str)
    
    def _generate_pdf_preview(self, paper: Dict) -> Dict:
        """Generate PDF preview for papers without figures."""
        
        if not paper.get('needs_pdf_preview'):
            return paper
        
        try:
            from pdf2image import convert_from_path
            
            arxiv_id = paper['arxiv_id'].split('v')[0]
            preview_path = self.assets_dir / f"{arxiv_id}.png"
            
            # Check if preview already exists
            if not preview_path.exists():
                pdf_url = paper.get('pdf_link')
                if pdf_url:
                    # Download PDF first
                    import requests
                    pdf_path = self.assets_dir / f"{arxiv_id}.pdf"
                    
                    if not pdf_path.exists():
                        response = requests.get(pdf_url, timeout=30)
                        with open(pdf_path, 'wb') as f:
                            f.write(response.content)
                    
                    # Convert first page to image
                    images = convert_from_path(
                        pdf_path, 
                        first_page=1, 
                        last_page=1,
                        dpi=150
                    )
                    
                    if images:
                        images[0].save(preview_path, 'PNG')
                        logger.info(f"Generated PDF preview for {arxiv_id}")
                        
                        # Clean up PDF to save space
                        pdf_path.unlink()
            
            if preview_path.exists():
                paper['pdf_preview_url'] = f"assets/{arxiv_id}.png"
                paper['needs_pdf_preview'] = False
        
        except Exception as e:
            logger.error(f"Failed to generate PDF preview for {paper.get('arxiv_id')}: {e}")
        
        return paper
    
    def render(self, 
               top_picks: List[Dict],
               buckets: Dict[str, List[Dict]],
               also_noteworthy: List[Dict],
               digest_summary: Optional[Dict] = None,
               metadata: Optional[Dict] = None) -> str:
        """Render the interactive web view."""
        
        # Generate PDF previews for papers that need them
        if self.config.get('media', {}).get('generate_pdf_previews', True):
            logger.info("Generating PDF previews for papers without figures...")
            
            for paper in top_picks:
                self._generate_pdf_preview(paper)
            
            for bucket_papers in buckets.values():
                for paper in bucket_papers:
                    self._generate_pdf_preview(paper)
            
            for paper in also_noteworthy:
                self._generate_pdf_preview(paper)
        
        # Format the date
        date_formatted = datetime.now().strftime("%A, %B %d, %Y")
        
        # Prepare template variables
        # Build categories string based on fetch configuration
        fetch_config = self.config['digest']['fetch']
        categories_parts = []
        if fetch_config.get('use_pubmed'):
            categories_parts.append('PubMed')
        if fetch_config.get('use_biorxiv'):
            categories_parts.append('bioRxiv/medRxiv')
        if fetch_config.get('use_rss') and fetch_config.get('categories'):
            categories_parts.extend(fetch_config['categories'])
        categories_str = ', '.join(categories_parts) if categories_parts else 'Multiple sources'
        
        context = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'date_formatted': date_formatted,
            'top_picks': top_picks,
            'buckets': buckets,
            'also_noteworthy': also_noteworthy,
            'digest_summary': digest_summary,
            'hours_lookback': self.config['digest']['fetch'].get('hours_lookback', 24),
            'categories_str': categories_str,
            'total_papers': metadata.get('total_papers', 0) if metadata else 0
        }
        
        html = self.template.render(**context)
        
        logger.info(f"Rendered web view with {len(top_picks)} top picks, "
                   f"{sum(len(p) for p in buckets.values())} bucketed papers")
        
        return html
    
    def save(self, html: str) -> str:
        """Save the web view and return the path."""
        output_path = self.web_dir / 'index.html'
        
        with open(output_path, 'w') as f:
            f.write(html)
        
        logger.info(f"Saved web view to {output_path}")
        
        return str(output_path)


