#!/usr/bin/env python3
"""
Main orchestrator for the arXiv Robotics Research Digest.
Updated to include figures, digest summary, X posts, and web view.
"""

import os
import sys
import logging
import yaml
from datetime import datetime
from typing import List, Dict, Tuple
from dotenv import load_dotenv
import pytz
from pathlib import Path

# Import our modules
from fetch import RSSFetcher, SearchAPIFetcher, PubMedFetcher, BioRxivFetcher
from rules import HeuristicFilter
from llm import GeminiClassifier
from render import EmailRenderer
from llm.summarize import DigestSummarizer  # NEW
from media.figure_extractor import FigureExtractor  # NEW
from social.x_finder import XFinder  # NEW
from render.web_renderer import WebRenderer  # NEW
from send import ResendClient
from store import Database

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(
    level=os.getenv('LOG_LEVEL', 'INFO'),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DigestOrchestrator:
    """Main orchestrator for the digest pipeline."""
    
    def __init__(self, config_path: str = 'config.yaml'):
        # Load configuration
        with open(config_path, 'r') as f:
            self.config = yaml.safe_load(f)
        
        # Initialize components
        self.db = Database(os.getenv('DATABASE_PATH', './digest.db'))
        
        # Initialize fetchers based on config
        fetch_config = self.config['digest']['fetch']
        self.fetchers = []
        
        # PubMed fetcher
        if fetch_config.get('use_pubmed', False):
            self.fetchers.append(PubMedFetcher(
                api_key=os.getenv('NCBI_API_KEY'),
                search_queries=fetch_config.get('pubmed_queries', []),
                days_lookback=fetch_config.get('days_lookback', 1)
            ))
        
        # bioRxiv/medRxiv fetcher
        if fetch_config.get('use_biorxiv', False):
            self.fetchers.append(BioRxivFetcher(
                categories=fetch_config.get('biorxiv_categories', ['biorxiv', 'medrxiv']),
                days_lookback=fetch_config.get('days_lookback', 1)
            ))
        
        # Keep RSS fetcher as fallback (for arXiv if needed)
        if fetch_config.get('use_rss', False):
            self.fetchers.append(RSSFetcher(
                categories=fetch_config.get('categories', []),
                hours_lookback=fetch_config.get('hours_lookback', 36),
                config=self.config
            ))
        
        self.heuristic_filter = HeuristicFilter(self.config)
        self.classifier = GeminiClassifier(
            api_key=os.getenv('GEMINI_API_KEY'),
            config=self.config
        )
        # NEW: Initialize new components
        self.summarizer = DigestSummarizer(
            api_key=os.getenv('GEMINI_API_KEY')
        )
        self.figure_extractor = FigureExtractor(self.config)
        self.x_finder = XFinder(self.config)
        
        self.renderer = EmailRenderer(self.config)
        self.web_renderer = WebRenderer(self.config)  # NEW
        self.email_client = ResendClient(
            api_key=os.getenv('RESEND_API_KEY'),
            config=self.config
        )
    
    def run(self, test_mode: bool = False, skip_classification: bool = False, force: bool = False):
        """Run the complete digest pipeline."""
        logger.info("Starting digest pipeline run")
        logger.info(f"Test mode: {test_mode}, Skip classification: {skip_classification}, Force: {force}")
        
        # Check if we should send emails based on schedule
        # Note: GitHub Actions handles the scheduling, so we always send when triggered
        # The config schedule is for local testing only
        if not test_mode and not force:
            # Only check schedule if we're running locally (not in GitHub Actions)
            if not os.getenv('GITHUB_ACTIONS'):
                if not self._should_send_email():
                    logger.info("Not a scheduled email day/time - skipping email send")
                    # Still process papers but don't send email
                    test_mode = True
        
        try:
            # Step 1: Fetch papers
            papers = self._fetch_papers()
            logger.info(f"Fetched {len(papers)} papers from all sources")
            
            if not papers:
                logger.warning("No papers fetched, skipping run")
                return
            
            # Step 2: Pre-filter with heuristics (add scores without aggressive filtering)
            logger.info("Adding heuristic scores to papers")
            for paper in papers:
                text = f"{paper['title']} {paper['abstract']}"
                paper['heuristic_score'] = self.heuristic_filter._calculate_score(text)
                paper['detected_buckets'] = self.heuristic_filter._detect_buckets(text)
            
            # Step 3: Filter papers to only include today's papers
            papers = self._filter_todays_papers(papers)
            logger.info(f"After filtering to today's papers: {len(papers)} papers from today")
            
            # Step 4: Filter out already seen papers (unless force mode)
            if not force:
                papers = self._filter_seen_papers(papers)
                logger.info(f"After deduplication: {len(papers)} new papers")
            else:
                logger.info("Force mode: Processing all papers regardless of history")
            
            if not papers:
                logger.info("No new papers to process")
                return
            
            # NEW Step 5: Enrich papers with figures and X posts
            logger.info("Enriching papers with figures and social media posts...")
            enriched_papers = []
            
            for i, paper in enumerate(papers):
                # Extract figures
                if self.config.get('features', {}).get('include_figures', True):
                    paper = self.figure_extractor.extract_figure(paper)
                
                # Find X posts (if enabled)
                if self.config.get('features', {}).get('include_x_posts', False):
                    paper = self.x_finder.find_x_post(paper)
                
                enriched_papers.append(paper)
                
                # Progress logging
                if (i + 1) % 10 == 0:
                    logger.info(f"Enriched {i + 1}/{len(papers)} papers")
            
            papers = enriched_papers
            
            # Step 6: Classify with Gemini (or skip for debugging)
            if skip_classification:
                logger.info("Skipping classification - marking all papers as relevant for debugging")
                for paper in papers:
                    paper['keep'] = True
                    paper['relevance_score'] = 50
                    paper['buckets'] = paper.get('detected_buckets', [])
                    paper['why_it_matters'] = 'Debug mode - all papers included'
                    paper['summary'] = paper['abstract'][:200] + '...'
            else:
                logger.info(f"\n{'='*80}")
                logger.info("🤖 STARTING CLASSIFICATION PROCESS")
                logger.info(f"📊 Processing {len(papers)} papers with Gemini AI")
                logger.info(f"{'='*80}")
                papers = self.classifier.classify_batch(papers)
                logger.info(f"\n{'='*80}")
                logger.info("✅ CLASSIFICATION PROCESS COMPLETE")
                logger.info(f"{'='*80}")
            
            # Step 5: Filter kept papers (must meet minimum relevance)
            min_relevance = self.config['digest'].get('min_relevance', 50)
            kept_papers = [
                p for p in papers 
                if p.get('keep', False) and p.get('relevance_score', 0) >= min_relevance
            ]
            logger.info(f"Kept {len(kept_papers)} papers after classification (min relevance: {min_relevance})")
            
            # Log classification summary
            if papers:
                logger.info(f"\n{'='*80}")
                logger.info("📊 CLASSIFICATION SUMMARY")
                logger.info(f"{'='*80}")
                dropped_papers = [p for p in papers if not p.get('keep', False)]
                low_score_papers = [p for p in papers if p.get('keep', False) and p.get('relevance_score', 0) < min_relevance]
                
                logger.info(f"📈 Total papers processed: {len(papers)}")
                logger.info(f"❌ Papers dropped by classifier: {len(dropped_papers)}")
                logger.info(f"⚠️  Papers kept but below min relevance ({min_relevance}): {len(low_score_papers)}")
                logger.info(f"✅ Final papers in digest: {len(kept_papers)}")
                
                if dropped_papers:
                    logger.info(f"\n📋 PAPERS DROPPED BY CLASSIFIER:")
                    for p in dropped_papers[:5]:  # Show first 5
                        logger.info(f"  ❌ {p['arxiv_id']}: {p['title'][:60]}...")
                        logger.info(f"     Score: {p.get('relevance_score', 0)} | Reason: {p.get('why_it_matters', 'No reason given')[:100]}...")
                
                if low_score_papers:
                    logger.info(f"\n⚠️  PAPERS BELOW MIN RELEVANCE ({min_relevance}):")
                    for p in low_score_papers[:5]:  # Show first 5
                        logger.info(f"  ⚠️  {p['arxiv_id']}: {p['title'][:60]}...")
                        logger.info(f"     Score: {p.get('relevance_score', 0)} | Reason: {p.get('why_it_matters', 'No reason given')[:100]}...")
                
                if kept_papers:
                    logger.info(f"\n✅ PAPERS KEPT FOR DIGEST:")
                    for p in kept_papers[:5]:  # Show first 5
                        logger.info(f"  ✅ {p['arxiv_id']}: {p['title'][:60]}...")
                        logger.info(f"     Score: {p.get('relevance_score', 0)} | Buckets: {', '.join(p.get('buckets', []))}")
                
                logger.info(f"{'='*80}")
            
            # If no papers kept and we're in debug mode, keep top 10 by heuristic score
            if not kept_papers and test_mode:
                logger.warning("No papers kept! Debug mode: keeping top 10 by heuristic score")
                papers.sort(key=lambda p: p.get('heuristic_score', 0), reverse=True)
                kept_papers = papers[:10]
                for paper in kept_papers:
                    paper['keep'] = True
                    paper['relevance_score'] = paper.get('heuristic_score', 30)
                    paper['why_it_matters'] = 'Debug: kept based on heuristic score'
            
            if not kept_papers:
                logger.warning("No relevant papers found after classification")
                if test_mode:
                    logger.info("Papers that were rejected:")
                    for paper in papers[:10]:
                        logger.info(f"  - {paper['arxiv_id']}: {paper['title'][:60]}... (score: {paper.get('relevance_score', 0)})")
                return
            
            # Step 6: Rank and organize
            top_picks, buckets, also_noteworthy = self._organize_papers(kept_papers)
            
            # NEW Step 9: Generate digest summary
            digest_summary = None
            if self.config.get('features', {}).get('include_digest_summary', True):
                logger.info("Generating digest summary...")
                digest_summary = self.summarizer.generate_summary(kept_papers)
                logger.info(f"Digest headline: {digest_summary.get('headline', 'N/A')}")
            
            # Step 10: Get filtered out papers for transparency
            filtered_out = [p for p in papers if not p.get('keep', False)]
            
            # NEW Step 11: Generate web view
            web_view_url = None
            if self.config.get('features', {}).get('build_web_view', True):
                logger.info("Generating interactive web view...")
                web_html = self.web_renderer.render(
                    top_picks=top_picks,
                    buckets=buckets,
                    also_noteworthy=also_noteworthy,
                    digest_summary=digest_summary,
                    metadata={'total_papers': len(papers)}
                )
                
                # Save web view
                web_path = self.web_renderer.save(web_html)
                
                # Generate GitHub Pages URL if in GitHub Actions
                if os.getenv('GITHUB_ACTIONS'):
                    repo = os.getenv('GITHUB_REPOSITORY', 'mindcompany/robotics_digest')
                    org, repo_name = repo.split('/')
                    web_view_url = f"https://{org}.github.io/{repo_name}/"
                else:
                    # Prefer configured public URL if provided (for clickable email links)
                    public_url = self.config.get('web', {}).get('public_url')
                    if public_url:
                        web_view_url = public_url
                    else:
                        web_view_url = f"file://{os.path.abspath(web_path)}"
                
                logger.info(f"Web view generated: {web_view_url}")
            
            # Step 12: Render email
            html = self.renderer.render(
                top_picks=top_picks,
                buckets=buckets,
                also_noteworthy=also_noteworthy,
                filtered_out=filtered_out,
                metadata={
                    'total_papers': len(papers),
                    'digest_summary': digest_summary,
                    'web_view_url': web_view_url
                }
            )
            
            # Step 13: Send email (or save in test mode)
            if test_mode:
                self._save_test_output(html)
                logger.info("Test mode: Email saved to test_output.html")
                if web_view_url and 'file://' in web_view_url:
                    logger.info(f"Web view saved to: {web_view_url}")
            else:
                subject = f"Bio Daily Research Digest - {datetime.now().strftime('%a, %b %d')}"
                recipients = self.config['digest']['recipients']
                
                success = self.email_client.send_digest(
                    recipients=recipients,
                    subject=subject,
                    html_content=html
                )
                
                if success:
                    logger.info(f"Email sent successfully to {recipients}")
                else:
                    logger.error("Failed to send email")
            
            # Step 14: Save to database
            if not test_mode:
                self.db.save_papers(papers)
                self.db.log_run(
                    papers_fetched=len(papers),
                    papers_kept=len(kept_papers),
                    top_picks_count=len(top_picks),
                    email_sent=not test_mode,
                    recipients=self.config['digest']['recipients']
                )
            
            # Log metrics
            self._log_metrics(papers, kept_papers, top_picks)
            
            logger.info("Digest pipeline completed successfully")
            
        except Exception as e:
            logger.error(f"Pipeline failed: {e}", exc_info=True)
            if not test_mode:
                self.db.log_run(
                    papers_fetched=0,
                    papers_kept=0,
                    top_picks_count=0,
                    email_sent=False,
                    recipients=[],
                    error=str(e)
                )
            raise
    
    def _fetch_papers(self) -> List[Dict]:
        """Fetch papers from all configured sources."""
        all_papers = []
        seen_ids = set()
        
        for fetcher in self.fetchers:
            fetcher_name = fetcher.__class__.__name__
            logger.info(f"Fetching from {fetcher_name}...")
            
            try:
                papers = fetcher.fetch()
                logger.info(f"{fetcher_name} returned {len(papers)} papers")
                
                # Deduplicate across sources using DOI or ID
                for paper in papers:
                    # Create unique ID from available identifiers
                    paper_id = (
                        paper.get('doi') or 
                        paper.get('arxiv_id') or 
                        paper.get('pubmed_id') or 
                        paper.get('biorxiv_id') or
                        paper.get('title', '')
                    )
                    
                    if paper_id and paper_id not in seen_ids:
                        seen_ids.add(paper_id)
                        # Standardize the ID field for database storage
                        if not paper.get('arxiv_id'):
                            paper['arxiv_id'] = paper_id
                        all_papers.append(paper)
                    else:
                        logger.debug(f"Skipping duplicate: {paper.get('title', '')[:50]}")
                
            except Exception as e:
                logger.error(f"Error fetching from {fetcher_name}: {e}")
                continue
        
        logger.info(f"Total unique papers from all sources: {len(all_papers)}")
        return all_papers
    
    def _filter_todays_papers(self, papers: List[Dict]) -> List[Dict]:
        """Filter papers to only include those from today."""
        from datetime import datetime, timezone
        
        # Get today's date in UTC
        today = datetime.now(timezone.utc).date()
        
        todays_papers = []
        logger.info("=== Filtering to today's papers ===")
        
        for paper in papers:
            # Parse the published date
            try:
                published_date = datetime.fromisoformat(paper['published'].replace('Z', '+00:00'))
                paper_date = published_date.date()
                
                title = paper['title'][:60] + "..." if len(paper['title']) > 60 else paper['title']
                
                if paper_date == today:
                    logger.info(f"  ✅ TODAY: {paper['arxiv_id']} - {title}")
                    todays_papers.append(paper)
                else:
                    logger.info(f"  ❌ OLD: {paper['arxiv_id']} ({paper_date}) - {title}")
            except Exception as e:
                logger.warning(f"Could not parse date for {paper['arxiv_id']}: {e}")
                # Include papers with unparseable dates to be safe
                todays_papers.append(paper)
        
        logger.info(f"=== Today's papers: {len(todays_papers)}/{len(papers)} papers from today ===")
        return todays_papers
    
    def _filter_seen_papers(self, papers: List[Dict]) -> List[Dict]:
        """Filter out papers we've already processed."""
        new_papers = []
        
        logger.info("=== Checking for duplicate papers ===")
        
        for paper in papers:
            arxiv_id = paper['arxiv_id']
            version = paper.get('version', 1)
            title = paper['title'][:60] + "..." if len(paper['title']) > 60 else paper['title']
            
            if self.db.has_seen_paper(arxiv_id, version):
                logger.info(f"  ❌ EXCLUDED (already processed): {arxiv_id} v{version} - {title}")
            else:
                logger.info(f"  ✅ INCLUDED (new paper): {arxiv_id} v{version} - {title}")
                new_papers.append(paper)
        
        logger.info(f"=== Deduplication complete: {len(new_papers)}/{len(papers)} papers are new ===")
        
        return new_papers
    
    def _organize_papers(self, papers: List[Dict]) -> Tuple[List[Dict], Dict[str, List[Dict]], List[Dict]]:
        """Organize papers into top picks, buckets, and also noteworthy."""
        
        # Calculate final scores
        for paper in papers:
            paper['final_score'] = self._calculate_final_score(paper)
        
        # Sort by final score
        papers.sort(key=lambda p: p['final_score'], reverse=True)
        
        # Select top picks
        top_picks_count = self.config['digest']['top_picks']
        top_picks = papers[:top_picks_count]
        
        # Mark top picks
        for paper in top_picks:
            paper['in_top_picks'] = True
        
        # Organize remaining papers by bucket (avoid duplicates)
        remaining = papers[top_picks_count:]
        buckets = {}
        used_papers = set()  # Track papers already assigned to buckets
        
        for bucket_config in self.config['buckets']:
            bucket_name = bucket_config['name']
            bucket_papers = [
                p for p in remaining 
                if bucket_name in p.get('buckets', []) and p['arxiv_id'] not in used_papers
            ]
            
            if bucket_papers:
                # Sort within bucket by score
                bucket_papers.sort(key=lambda p: p['final_score'], reverse=True)
                buckets[bucket_name] = bucket_papers
                # Mark these papers as used
                used_papers.update(p['arxiv_id'] for p in bucket_papers)
        
        # Find also noteworthy (high score but not in top picks or main buckets)
        also_noteworthy = [
            p for p in remaining
            if p['final_score'] >= 60 and p['arxiv_id'] not in used_papers
        ]
        
        return top_picks, buckets, also_noteworthy
    
    def _calculate_final_score(self, paper: Dict) -> float:
        """Calculate final relevance score combining all factors."""
        score = paper.get('relevance_score', 0)
        
        # Add heuristic score (weighted 30%)
        heuristic = paper.get('heuristic_score', 0)
        score = score * 0.7 + heuristic * 0.3
        
        # Boost for code/data
        if paper.get('code_urls'):
            score += 5
        if paper.get('dataset_urls'):
            score += 3
        
        # NEW: Small boost for having figure or X post
        if paper.get('figure_url'):
            score += 2
        if paper.get('x_url'):
            score += 2
        
        # Penalty for risk flags
        risk_flags = paper.get('risk_flags', [])
        if 'sim-only' in risk_flags:
            score -= 10
        if 'no-code' in risk_flags:
            score -= 5
        
        # Penalty for greylisted papers
        if paper.get('greylisted'):
            score -= 15
        
        return max(0, min(100, score))
    
    def _should_send_email(self) -> bool:
        """Check if we should send an email based on schedule configuration."""
        try:
            # Get timezone from config
            tz_name = self.config['digest']['schedule'].get('timezone', 'America/New_York')
            tz = pytz.timezone(tz_name)
            
            # Get current time in configured timezone
            now = datetime.now(tz)
            
            # Check if today is a scheduled day
            days_of_week = self.config['digest']['schedule'].get('days_of_week', [])
            if days_of_week:
                current_day = now.strftime('%A')
                if current_day not in days_of_week:
                    logger.info(f"Today ({current_day}) is not in scheduled days: {days_of_week}")
                    return False
            
            # Check if current time matches scheduled time (within 1 hour window)
            scheduled_time_str = self.config['digest']['schedule'].get('run_at_local', '17:00')
            scheduled_hour = int(scheduled_time_str.split(':')[0])
            scheduled_minute = int(scheduled_time_str.split(':')[1])
            
            current_hour = now.hour
            current_minute = now.minute
            
            # Allow 1-hour window around scheduled time
            time_diff = abs((current_hour * 60 + current_minute) - (scheduled_hour * 60 + scheduled_minute))
            if time_diff > 60:  # More than 1 hour difference
                logger.info(f"Current time ({current_hour:02d}:{current_minute:02d}) is not within 1 hour of scheduled time ({scheduled_hour:02d}:{scheduled_minute:02d})")
                return False
            
            logger.info(f"Email send conditions met: {current_day} at {current_hour:02d}:{current_minute:02d}")
            return True
            
        except Exception as e:
            logger.error(f"Error checking email schedule: {e}")
            # Default to sending if there's an error
            return True
    
    def _save_test_output(self, html: str):
        """Save test output to file."""
        with open('test_output.html', 'w') as f:
            f.write(html)
    
    def _log_metrics(self, papers: List[Dict], kept_papers: List[Dict], top_picks: List[Dict]):
        """Log metrics for monitoring."""
        logger.info("=== Pipeline Metrics ===")
        logger.info(f"Total papers fetched: {len(papers)}")
        logger.info(f"Papers kept: {len(kept_papers)} ({len(kept_papers)/len(papers)*100:.1f}%)")
        logger.info(f"Top picks: {len(top_picks)}")
        
        # Log bucket distribution
        bucket_counts = {}
        for paper in kept_papers:
            for bucket in paper.get('buckets', []):
                bucket_counts[bucket] = bucket_counts.get(bucket, 0) + 1
        
        if bucket_counts:
            logger.info("Bucket distribution:")
            for bucket, count in sorted(bucket_counts.items(), key=lambda x: x[1], reverse=True):
                logger.info(f"  - {bucket}: {count}")
        
        if not self.db:
            return
            
        self.db.log_metric('papers_fetched', len(papers))
        self.db.log_metric('papers_kept', len(kept_papers))
        self.db.log_metric('keep_ratio', len(kept_papers) / len(papers) if papers else 0)
        self.db.log_metric('top_picks', len(top_picks))
        
        for bucket, count in bucket_counts.items():
            self.db.log_metric(f'bucket_{bucket}', count)


if __name__ == '__main__':
    # Parse command line arguments
    test_mode = '--test' in sys.argv
    skip_classification = '--skip-classify' in sys.argv
    reset_db = '--reset-db' in sys.argv

    force_process = '--force' in sys.argv
    verbose = '--verbose' in sys.argv
    
    # Set logging level based on verbose flag
    if verbose:
        logging.getLogger().setLevel(logging.INFO)
        logger.info("Verbose logging enabled - showing detailed classification reasoning")
    
    if skip_classification:
        logger.info("Running in skip-classification mode - all papers will be included")
    
    if force_process:
        logger.info("Force mode: Will process all papers even if seen before")
    
    # Run the orchestrator
    orchestrator = DigestOrchestrator()
    
    # Reset database if requested
    if reset_db:
        if os.path.exists('./digest.db'):
            os.remove('./digest.db')
            logger.info("Database reset - removed digest.db")
            orchestrator.db = Database(os.getenv('DATABASE_PATH', './digest.db'))
    
    orchestrator.run(test_mode=test_mode, skip_classification=skip_classification, force=force_process)