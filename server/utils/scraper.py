#!/usr/bin/env python3
"""
Web Scraper - A robust Python module for scraping content from any URL

This module provides a comprehensive set of tools to extract various types of content
from websites with robust error handling, rate limiting, and efficient parsing.

Features:
- Extract clean text content from any website
- Extract specific elements using CSS selectors
- Extract links from a webpage
- Extract tables from a webpage
- Extract metadata from a webpage
- Built-in rate limiting and retry logic
- Comprehensive error handling
"""

import os
import time
import logging
import random
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Union, List, Tuple
from bs4 import BeautifulSoup
import trafilatura
from requests.exceptions import RequestException

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("web_scraper")

class WebScraper:
    """
    A robust web scraper that extracts content from any URL with
    comprehensive error handling and content parsing capabilities.
    
    Features:
    - Robust error handling
    - Rate limiting
    - Retry mechanism with exponential backoff
    - User-agent customization
    - Content extraction (HTML, text, tables, specific elements)
    """
    
    def __init__(self, 
                 user_agent: Optional[str] = None,
                 timeout: int = 30,
                 max_retries: int = 3,
                 respect_robots: bool = True,
                 rate_limit: Optional[float] = 1.0):
        """
        Initialize the web scraper with configurable parameters.
        
        Args:
            user_agent (str, optional): Custom user agent string. Defaults to a common browser user agent.
            timeout (int): Request timeout in seconds. Defaults to 30.
            max_retries (int): Maximum number of retry attempts for failed requests. Defaults to 3.
            respect_robots (bool): Whether to respect robots.txt rules. Defaults to True.
            rate_limit (float, optional): Minimum delay between requests in seconds. Defaults to 1.0.
        """
        self.timeout = timeout
        self.max_retries = max_retries
        self.respect_robots = respect_robots
        self.rate_limit = rate_limit
        self.last_request_time = 0
        
        # Use provided user agent or default to a common browser user agent
        self.user_agent = user_agent or (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        self.headers = {
            "User-Agent": self.user_agent,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
            "Accept-Encoding": "gzip, deflate, br",
            "DNT": "1",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "Cache-Control": "max-age=0"
        }
        
        # Create a session for connection pooling
        self.session = requests.Session()
        self.session.headers.update(self.headers)
        
    def _apply_rate_limit(self) -> None:
        """
        Implement rate limiting to avoid overwhelming target sites.
        """
        if not self.rate_limit:
            return
            
        current_time = time.time()
        elapsed = current_time - self.last_request_time
        
        if elapsed < self.rate_limit:
            # Add a small random delay to avoid detection
            sleep_time = self.rate_limit - elapsed + random.uniform(0.1, 0.5)
            logger.debug(f"Rate limiting: sleeping for {sleep_time:.2f} seconds")
            time.sleep(sleep_time)
            
        self.last_request_time = time.time()
    
    def fetch(self, url: str, params: Optional[Dict[str, Any]] = None) -> requests.Response:
        """
        Fetch a URL with retry logic and error handling.
        
        Args:
            url (str): The URL to fetch
            params (dict, optional): Query parameters for the request
            
        Returns:
            requests.Response: The response object
            
        Raises:
            RequestException: If the request fails after all retries
        """
        self._apply_rate_limit()
        
        # Validate URL
        parsed_url = urlparse(url)
        if not all([parsed_url.scheme, parsed_url.netloc]):
            raise ValueError(f"Invalid URL format: {url}")
        
        attempt = 0
        last_exception = None
        
        while attempt < self.max_retries:
            try:
                logger.info(f"Fetching URL: {url} (attempt {attempt+1}/{self.max_retries})")
                response = self.session.get(
                    url,
                    params=params,
                    timeout=self.timeout,
                    allow_redirects=True
                )
                
                # Check if the request was successful
                response.raise_for_status()
                return response
                
            except RequestException as e:
                attempt += 1
                wait_time = 2 ** attempt  # Exponential backoff
                last_exception = e
                
                logger.warning(f"Request failed: {str(e)}")
                
                if attempt < self.max_retries:
                    logger.info(f"Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
        
        # If we've exhausted our retries, raise the last exception
        logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
        raise last_exception or RequestException(f"Failed to fetch {url}")
    
    def get_html(self, url: str) -> str:
        """
        Get the HTML content of a URL.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            str: The HTML content
        """
        try:
            response = self.fetch(url)
            return response.text
        except Exception as e:
            logger.error(f"Failed to get HTML from {url}: {str(e)}")
            return ""
    
    def extract_text(self, url: str) -> str:
        """
        Extract clean text content from a URL using Trafilatura.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            str: The extracted text content
        """
        try:
            html = self.get_html(url)
            if not html:
                return ""
            return trafilatura.extract(html)
        except Exception as e:
            logger.error(f"Failed to extract text from {url}: {str(e)}")
            return ""
    
    def extract_elements(self, url: str, css_selector: str) -> List[str]:
        """
        Extract specific elements from a webpage using a CSS selector.
        
        Args:
            url (str): The URL to scrape
            css_selector (str): CSS selector to target specific elements
            
        Returns:
            list: List of extracted elements as strings
        """
        try:
            html = self.get_html(url)
            if not html:
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            elements = soup.select(css_selector)
            
            return [element.get_text(strip=True) for element in elements]
            
        except Exception as e:
            logger.error(f"Failed to extract elements from {url}: {str(e)}")
            return []
    
    def extract_links(self, url: str) -> List[str]:
        """
        Extract all links from a webpage.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            list: List of extracted links
        """
        try:
            html = self.get_html(url)
            if not html:
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            links = soup.find_all('a', href=True)
            
            return [link.get('href') for link in links]
            
        except Exception as e:
            logger.error(f"Failed to extract links from {url}: {str(e)}")
            return []
    
    def extract_metadata(self, url: str) -> Dict[str, str]:
        """
        Extract metadata from a webpage (meta tags).
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            dict: Dictionary of metadata key-value pairs
        """
        try:
            html = self.get_html(url)
            if not html:
                return {}
                
            soup = BeautifulSoup(html, 'html.parser')
            meta_tags = soup.find_all('meta')
            
            metadata = {}
            for tag in meta_tags:
                name = tag.get('name', tag.get('property', ''))
                content = tag.get('content', '')
                if name and content:
                    metadata[name] = content
                    
            return metadata
            
        except Exception as e:
            logger.error(f"Failed to extract metadata from {url}: {str(e)}")
            return {}
    
    def extract_table(self, url: str, table_index: int = 0) -> List[List[str]]:
        """
        Extract a table from a webpage.
        
        Args:
            url (str): The URL to scrape
            table_index (int): Index of the table to extract if multiple tables exist
            
        Returns:
            list: 2D list representing the table data
        """
        try:
            html = self.get_html(url)
            if not html:
                return []
                
            soup = BeautifulSoup(html, 'html.parser')
            tables = soup.find_all('table')
            
            if not tables or table_index >= len(tables):
                return []
                
            table = tables[table_index]
            rows = []
            
            for tr in table.find_all('tr'):
                row = []
                for cell in tr.find_all(['td', 'th']):
                    row.append(cell.get_text(strip=True))
                if row:  # Only append non-empty rows
                    rows.append(row)
                    
            return rows
            
        except Exception as e:
            logger.error(f"Failed to extract table from {url}: {str(e)}")
            return []
    
    def scrape(self, url: str, params: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Perform a comprehensive scrape of a URL, extracting all available content.
        
        Args:
            url (str): The URL to scrape
            params (dict, optional): Query parameters for the request
            
        Returns:
            dict: Dictionary containing all extracted content
        """
        try:
            html = self.get_html(url)
            if not html:
                return {}
                
            soup = BeautifulSoup(html, 'html.parser')
            
            # Extract all types of content
            result = {
                'html': html,
                'text_content': self.extract_text(url),
                'metadata': self.extract_metadata(url),
                'links': self.extract_links(url),
                'tables': [self.extract_table(url, i) for i in range(len(soup.find_all('table')))],
                'title': soup.title.string if soup.title else '',
                'status': 'success'
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to scrape {url}: {str(e)}")
            return {
                'status': 'error',
                'error': str(e)
            } 