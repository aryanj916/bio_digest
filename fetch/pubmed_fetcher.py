import requests
import logging
from datetime import datetime, timedelta, timezone
from typing import List, Dict, Optional
import xml.etree.ElementTree as ET
from urllib.parse import urlencode

logger = logging.getLogger(__name__)

class PubMedFetcher:
    """Fetches papers from PubMed using NCBI E-utilities API."""
    
    BASE_URL = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils"
    
    def __init__(self, api_key: str, search_queries: List[str], days_lookback: int = 1):
        self.api_key = api_key
        self.search_queries = search_queries
        self.days_lookback = days_lookback
    
    def fetch(self) -> List[Dict]:
        """Fetch papers from PubMed for all configured search queries."""
        all_papers = []
        seen_ids = set()
        
        for query in self.search_queries:
            logger.info(f"Searching PubMed with query: {query}")
            try:
                # Step 1: Search for PMIDs
                pmids = self._search_pmids(query)
                logger.info(f"Found {len(pmids)} PMIDs for query: {query}")
                
                if not pmids:
                    continue
                
                # Step 2: Fetch details for PMIDs
                papers = self._fetch_details(pmids)
                
                # Deduplicate
                for paper in papers:
                    if paper['pubmed_id'] not in seen_ids:
                        seen_ids.add(paper['pubmed_id'])
                        all_papers.append(paper)
                
            except Exception as e:
                logger.error(f"Error fetching PubMed papers for query '{query}': {e}")
                continue
        
        logger.info(f"Total unique papers from PubMed: {len(all_papers)}")
        return all_papers
    
    def _search_pmids(self, query: str) -> List[str]:
        """Search PubMed and return list of PMIDs."""
        # Build date filter
        end_date = datetime.now(timezone.utc)
        start_date = end_date - timedelta(days=self.days_lookback)
        
        date_query = f"({start_date.strftime('%Y/%m/%d')}:{end_date.strftime('%Y/%m/%d')}[PDAT])"
        full_query = f"{query} AND {date_query}"
        
        params = {
            'db': 'pubmed',
            'term': full_query,
            'retmax': 500,  # Max results
            'retmode': 'json',
            'api_key': self.api_key,
            'sort': 'pub_date',
            'usehistory': 'n'
        }
        
        try:
            url = f"{self.BASE_URL}/esearch.fcgi"
            response = requests.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            pmids = data.get('esearchresult', {}).get('idlist', [])
            
            return pmids
            
        except Exception as e:
            logger.error(f"Error searching PubMed: {e}")
            return []
    
    def _fetch_details(self, pmids: List[str]) -> List[Dict]:
        """Fetch paper details for a list of PMIDs."""
        if not pmids:
            return []
        
        # PubMed API recommends batches of 200
        batch_size = 200
        papers = []
        
        for i in range(0, len(pmids), batch_size):
            batch = pmids[i:i+batch_size]
            
            params = {
                'db': 'pubmed',
                'id': ','.join(batch),
                'retmode': 'xml',
                'api_key': self.api_key
            }
            
            try:
                url = f"{self.BASE_URL}/efetch.fcgi"
                response = requests.get(url, params=params, timeout=60)
                response.raise_for_status()
                
                batch_papers = self._parse_xml_response(response.text)
                papers.extend(batch_papers)
                
                logger.info(f"Fetched details for {len(batch_papers)} papers (batch {i//batch_size + 1})")
                
            except Exception as e:
                logger.error(f"Error fetching PubMed details for batch: {e}")
                continue
        
        return papers
    
    def _parse_xml_response(self, xml_text: str) -> List[Dict]:
        """Parse PubMed XML response into our standard format."""
        papers = []
        
        try:
            root = ET.fromstring(xml_text)
            
            for article in root.findall('.//PubmedArticle'):
                try:
                    paper = self._parse_article(article)
                    if paper:
                        papers.append(paper)
                except Exception as e:
                    logger.warning(f"Error parsing article: {e}")
                    continue
            
        except Exception as e:
            logger.error(f"Error parsing XML: {e}")
        
        return papers
    
    def _parse_article(self, article) -> Optional[Dict]:
        """Parse a single PubMed article."""
        try:
            # Get PMID
            pmid_elem = article.find('.//PMID')
            if pmid_elem is None:
                return None
            pmid = pmid_elem.text
            
            # Get article metadata
            article_elem = article.find('.//Article')
            if article_elem is None:
                return None
            
            # Title
            title_elem = article_elem.find('.//ArticleTitle')
            title = title_elem.text if title_elem is not None and title_elem.text else "No title"
            
            # Abstract
            abstract_parts = []
            abstract_elem = article_elem.find('.//Abstract')
            if abstract_elem is not None:
                for text_elem in abstract_elem.findall('.//AbstractText'):
                    if text_elem.text:
                        # Handle labeled abstracts
                        label = text_elem.get('Label', '')
                        if label:
                            abstract_parts.append(f"{label}: {text_elem.text}")
                        else:
                            abstract_parts.append(text_elem.text)
            abstract = ' '.join(abstract_parts) if abstract_parts else "No abstract available"
            
            # Authors
            authors = []
            author_list = article_elem.find('.//AuthorList')
            if author_list is not None:
                for author in author_list.findall('.//Author'):
                    last_name = author.find('.//LastName')
                    fore_name = author.find('.//ForeName')
                    if last_name is not None and last_name.text:
                        author_name = last_name.text
                        if fore_name is not None and fore_name.text:
                            author_name = f"{fore_name.text} {author_name}"
                        authors.append(author_name)
            
            # Journal
            journal_elem = article_elem.find('.//Journal/Title')
            journal = journal_elem.text if journal_elem is not None and journal_elem.text else "Unknown Journal"
            
            # Publication date
            pub_date_elem = article.find('.//PubmedData/History/PubMedPubDate[@PubStatus="pubmed"]')
            if pub_date_elem is None:
                pub_date_elem = article.find('.//PubmedData/History/PubMedPubDate[@PubStatus="entrez"]')
            if pub_date_elem is None:
                pub_date_elem = article_elem.find('.//Journal/JournalIssue/PubDate')
            
            published = self._parse_pubmed_date(pub_date_elem)
            
            # DOI
            doi = None
            article_id_list = article.find('.//PubmedData/ArticleIdList')
            if article_id_list is not None:
                for article_id in article_id_list.findall('.//ArticleId'):
                    if article_id.get('IdType') == 'doi':
                        doi = article_id.text
                        break
            
            # MeSH terms (keywords)
            mesh_terms = []
            mesh_list = article.find('.//MeshHeadingList')
            if mesh_list is not None:
                for mesh in mesh_list.findall('.//MeshHeading/DescriptorName'):
                    if mesh.text:
                        mesh_terms.append(mesh.text)
            
            # Build URLs
            pubmed_link = f"https://pubmed.ncbi.nlm.nih.gov/{pmid}/"
            pdf_link = f"https://www.ncbi.nlm.nih.gov/pmc/articles/PMC{pmid}/pdf/" if doi else None
            
            return {
                'pubmed_id': pmid,
                'doi': doi,
                'title': title.strip(),
                'abstract': abstract.strip(),
                'authors': authors,
                'journal': journal,
                'categories': mesh_terms[:5],  # Limit to top 5 MeSH terms
                'primary_category': 'PubMed',
                'published': published.isoformat() if published else None,
                'updated': published.isoformat() if published else None,
                'pdf_link': pdf_link,
                'pubmed_link': pubmed_link,
                'arxiv_link': pubmed_link,  # Use pubmed_link as standard link
                'comments': '',
                'version': 1,
                'source': 'pubmed'
            }
            
        except Exception as e:
            logger.error(f"Error parsing article: {e}")
            return None
    
    def _parse_pubmed_date(self, date_elem) -> Optional[datetime]:
        """Parse PubMed date element to datetime."""
        if date_elem is None:
            return None
        
        try:
            year_elem = date_elem.find('.//Year')
            month_elem = date_elem.find('.//Month')
            day_elem = date_elem.find('.//Day')
            
            year = int(year_elem.text) if year_elem is not None and year_elem.text else None
            month = int(month_elem.text) if month_elem is not None and month_elem.text and month_elem.text.isdigit() else 1
            day = int(day_elem.text) if day_elem is not None and day_elem.text else 1
            
            if year:
                return datetime(year, month, day, tzinfo=timezone.utc)
        except Exception as e:
            logger.warning(f"Error parsing date: {e}")
        
        return None

