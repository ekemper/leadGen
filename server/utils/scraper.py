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
import random
import requests
from urllib.parse import urlparse
from typing import Dict, Any, Optional, Union, List, Tuple
from bs4 import BeautifulSoup
import trafilatura
from requests.exceptions import RequestException
from server.utils.logging_config import setup_logger, ContextLogger

# Configure logging
logger = setup_logger('web_scraper')

class WebScraper:
    """A robust web scraper with built-in rate limiting and error handling."""
    
    def __init__(self, rate_limit: float = 1.0, max_retries: int = 3):
        """
        Initialize the web scraper.
        
        Args:
            rate_limit: Minimum time between requests in seconds
            max_retries: Maximum number of retry attempts for failed requests
        """
        self.rate_limit = rate_limit
        self.max_retries = max_retries
        self.last_request_time = 0
        
    def _wait_for_rate_limit(self):
        """Enforce rate limiting between requests."""
        current_time = time.time()
        time_since_last = current_time - self.last_request_time
        if time_since_last < self.rate_limit:
            time.sleep(self.rate_limit - time_since_last)
        self.last_request_time = time.time()
    
    def _make_request(self, url: str, method: str = 'GET', **kwargs) -> requests.Response:
        """
        Make an HTTP request with retry logic and rate limiting.
        
        Args:
            url: The URL to request
            method: HTTP method to use
            **kwargs: Additional arguments to pass to requests
            
        Returns:
            Response object from successful request
            
        Raises:
            RequestException: If all retry attempts fail
        """
        with ContextLogger(logger, url=url, method=method):
            for attempt in range(self.max_retries):
                try:
                    self._wait_for_rate_limit()
                    response = requests.request(method, url, **kwargs)
                    response.raise_for_status()
                    return response
                except RequestException as e:
                    logger.warning("Request failed", extra={
                        'metadata': {
                            'attempt': attempt + 1,
                            'error': str(e)
                        }
                    })
                    if attempt == self.max_retries - 1:
                        logger.error("Max retries exceeded", extra={
                            'metadata': {
                                'max_retries': self.max_retries,
                                'error': str(e)
                            }
                        })
                        raise
                    time.sleep(2 ** attempt)  # Exponential backoff
    
    def scrape_content(self, url: str) -> Dict[str, Any]:
        """
        Scrape content from a URL.
        
        Args:
            url: The URL to scrape
            
        Returns:
            Dictionary containing scraped content
        """
        with ContextLogger(logger, url=url):
            try:
                response = self._make_request(url)
                downloaded = trafilatura.fetch_url(url)
                
                if not downloaded:
                    logger.warning("Failed to download content", extra={
                        'metadata': {'url': url}
                    })
                    return {}
                
                # Extract main content
                content = trafilatura.extract(downloaded)
                
                # Parse with BeautifulSoup for additional extraction
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Extract metadata
                metadata = {
                    'title': soup.title.string if soup.title else None,
                    'meta_description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else None,
                    'canonical_url': soup.find('link', {'rel': 'canonical'})['href'] if soup.find('link', {'rel': 'canonical'}) else None
                }
                
                logger.info("Content scraped successfully", extra={
                    'metadata': {
                        'url': url,
                        'content_length': len(content) if content else 0
                    }
                })
                
                return {
                    'content': content,
                    'metadata': metadata,
                    'status': 'success'
                }
                
            except Exception as e:
                logger.error("Failed to scrape content", extra={
                    'metadata': {
                        'url': url,
                        'error': str(e)
                    }
                }, exc_info=True)
                return {
                    'content': None,
                    'metadata': {},
                    'status': 'error',
                    'error': str(e)
                } 