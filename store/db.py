import sqlite3
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional
import os

logger = logging.getLogger(__name__)

class Database:
    """SQLite database for tracking processed papers and metrics."""
    
    def __init__(self, db_path: str = "./digest.db"):
        self.db_path = db_path
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            # Papers table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS papers (
                    arxiv_id TEXT PRIMARY KEY,
                    title TEXT,
                    processed_at TIMESTAMP,
                    relevance_score REAL,
                    kept BOOLEAN,
                    buckets TEXT,
                    in_top_picks BOOLEAN,
                    version INTEGER
                )
            """)
            
            # Digest runs table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS digest_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_at TIMESTAMP,
                    papers_fetched INTEGER,
                    papers_kept INTEGER,
                    top_picks_count INTEGER,
                    email_sent BOOLEAN,
                    recipients TEXT,
                    error TEXT
                )
            """)
            
            # Metrics table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS metrics (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP,
                    metric_name TEXT,
                    metric_value REAL,
                    metadata TEXT
                )
            """)
            
            conn.commit()
    
    def has_seen_paper(self, arxiv_id: str, version: int = None) -> bool:
        """Check if we've already processed this paper (and version)."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            if version:
                cursor.execute(
                    "SELECT 1 FROM papers WHERE arxiv_id = ? AND version >= ?",
                    (arxiv_id, version)
                )
            else:
                cursor.execute(
                    "SELECT 1 FROM papers WHERE arxiv_id = ?",
                    (arxiv_id,)
                )
            
            return cursor.fetchone() is not None
    
    def save_papers(self, papers: List[Dict]):
        """Save processed papers to database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            for paper in papers:
                cursor.execute("""
                    INSERT OR REPLACE INTO papers 
                    (arxiv_id, title, processed_at, relevance_score, kept, buckets, in_top_picks, version)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    paper['arxiv_id'],
                    paper['title'],
                    datetime.now(),
                    paper.get('relevance_score', 0),
                    paper.get('keep', False),
                    json.dumps(paper.get('buckets', [])),
                    paper.get('in_top_picks', False),
                    paper.get('version', 1)
                ))
            
            conn.commit()
            logger.info(f"Saved {len(papers)} papers to database")
    
    def log_run(self, 
                papers_fetched: int,
                papers_kept: int,
                top_picks_count: int,
                email_sent: bool,
                recipients: List[str],
                error: Optional[str] = None):
        """Log a digest run."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO digest_runs 
                (run_at, papers_fetched, papers_kept, top_picks_count, email_sent, recipients, error)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                datetime.now(),
                papers_fetched,
                papers_kept,
                top_picks_count,
                email_sent,
                json.dumps(recipients),
                error
            ))
            
            conn.commit()
    
    def log_metric(self, name: str, value: float, metadata: Dict = None):
        """Log a metric."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            cursor.execute("""
                INSERT INTO metrics (timestamp, metric_name, metric_value, metadata)
                VALUES (?, ?, ?, ?)
            """, (
                datetime.now(),
                name,
                value,
                json.dumps(metadata) if metadata else None
            ))
            
            conn.commit()
    
    def get_recent_papers(self, days: int = 7) -> List[Dict]:
        """Get recently processed papers."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute("""
                SELECT * FROM papers
                WHERE processed_at > datetime('now', '-' || ? || ' days')
                ORDER BY processed_at DESC
            """, (days,))
            
            return [dict(row) for row in cursor.fetchall()]