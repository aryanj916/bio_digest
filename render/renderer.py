from jinja2 import Template
import logging
from datetime import datetime
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class EmailRenderer:
    """Render email HTML from classified papers."""
    
    def __init__(self, config: dict):
        self.config = config
        self.template = self._load_template()
        # Design tokens for Droyd branding (email-safe)
        self.tokens = {
            "brandName": "Droyd",
            "logoUrl": "https://dummyimage.com/200x40/8B5CF6/FFFFFF&text=Droyd",
            "color": {
                "bg": "#FAFAFA",
                "panel": "#FFFFFF",
                "muted": "#6B7280",
                "text": "#1F2937",
                "subtle": "#374151",
                "primary": "#6366F1",
                "primaryHi": "#4F46E5",
                "accent1": "#10B981",
                "accent2": "#F59E0B",
                "accent3": "#EF4444",
                "accent4": "#3B82F6",
                "accent5": "#8B5CF6",
            },
            "radius": {"sm": 8, "md": 14, "lg": 20, "xl": 28},
            "shadow": "0 4px 6px -1px rgba(0, 0, 0, 0.1), 0 2px 4px -1px rgba(0, 0, 0, 0.06)",
            "fontStack": "'Segoe UI', Roboto, Arial, sans-serif",
        }

    def _hex_to_rgba(self, hex_color: str, alpha: float) -> str:
        """Convert hex like #RRGGBB to rgba(r,g,b,alpha)."""
        hex_color = hex_color.lstrip('#')
        r = int(hex_color[0:2], 16)
        g = int(hex_color[2:4], 16)
        b = int(hex_color[4:6], 16)
        return f"rgba({r},{g},{b},{alpha})"

    def _build_badge_style_map(self) -> Dict[str, str]:
        """Map bucket names to inline badge styles using tokens."""
        c = self.tokens["color"]
        bucket_to_hex = {
            "VLA / LLM-in-the-Loop": c["accent1"],
            "Imitation / Diffusion / RL": c["accent2"],
            "Perception for Manipulation": c["accent3"],
            "Task & Motion Planning": c["accent4"],
            "Datasets & Benchmarks": c["accent5"],
            "Bimanual / Dual-Arm Manipulation": c["primary"],
            "Mobile Manipulation": c["primaryHi"],
            "Hardware & Mechatronics": "#EC4899",
            "HRI & Teleop": "#06B6D4",
            "Safety & Reliability": "#F97316",
            "Navigation & Mapping": c["accent4"],
            "Systems & Infrastructure": c["muted"],
            "Grasping & Dexterous Manipulation": "#10B981",
            "Humanoids & Legged": "#8B5CF6",
        }
        style_map: Dict[str, str] = {}
        for bucket, hex_color in bucket_to_hex.items():
            bg = self._hex_to_rgba(hex_color, 0.15)
            border = self._hex_to_rgba(hex_color, 0.45)
            style_map[bucket] = (
                f"background:{bg};border:1px solid {border};"
                f"border-radius:999px;color:{c['text']};"
                f"font:700 11px {self.tokens['fontStack']};"
                f"letter-spacing:.4px;text-transform:uppercase;padding:6px 8px;display:inline-block;"
            )
        return style_map
    
    def _load_template(self) -> Template:
        """Load the email template."""
        template_path = os.path.join(
            os.path.dirname(__file__), 
            'email_template.html'
        )
        
        with open(template_path, 'r') as f:
            template_str = f.read()
        
        return Template(template_str)
    
    def render(self, 
               top_picks: List[Dict],
               buckets: Dict[str, List[Dict]],
               also_noteworthy: List[Dict],
               filtered_out: List[Dict],
               metadata: Optional[Dict] = None) -> str:
        """Render the email HTML with new features."""
        
        metadata = metadata or {}
        
        # Format the date
        date_formatted = datetime.now().strftime("%A, %B %d, %Y")
        
        # Extract new metadata fields
        digest_summary = metadata.get('digest_summary')
        web_view_url = metadata.get('web_view_url')
        
        # Prepare template variables
        context = {
            'date': datetime.now().strftime("%Y-%m-%d"),
            'date_formatted': date_formatted,
            'top_picks': top_picks,
            'buckets': buckets,
            'also_noteworthy': also_noteworthy,
            'filtered_out': filtered_out,
            'hours_lookback': self.config['digest']['fetch']['hours_lookback'],
            'categories_str': ', '.join(self.config['digest']['fetch']['categories']),
            'tokens': self.tokens,
            'badge_style_by_bucket': self._build_badge_style_map(),
            'from_email': self.config['digest'].get('from_email', ''),
            'digest_summary': digest_summary,  # NEW
            'web_view_url': web_view_url,      # NEW
            'total_papers': metadata.get('total_papers', 0)
        }
        
        html = self.template.render(**context)
        
        # Log statistics
        total_papers = len(top_picks) + sum(len(p) for p in buckets.values()) + len(also_noteworthy)
        papers_with_figures = sum(1 for p in top_picks if p.get('figure_url'))
        papers_with_x = sum(1 for p in top_picks if p.get('x_url'))
        
        logger.info(f"Rendered email with {len(top_picks)} top picks, "
                   f"{sum(len(p) for p in buckets.values())} bucketed papers")
        logger.info(f"Papers with figures: {papers_with_figures}")
        logger.info(f"Papers with X posts: {papers_with_x}")
        
        if digest_summary:
            logger.info(f"Digest headline: {digest_summary.get('headline', 'N/A')}")
        
        if web_view_url:
            logger.info(f"Web view URL: {web_view_url}")
        
        return html