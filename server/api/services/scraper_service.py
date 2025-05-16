import json
from typing import Dict, Any
import sys
import os
from pathlib import Path
import requests
from bs4 import BeautifulSoup
import trafilatura
import re
from urllib.parse import urlparse
from server.utils.logging_config import app_logger
from werkzeug.exceptions import BadRequest, InternalServerError
from server.utils.scraper import WebScraper

# Add the server directory to Python path
server_dir = str(Path(__file__).resolve().parent.parent.parent)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

class ScraperService:
    """Service for web scraping functionality."""

    def __init__(self):
        """Initialize the scraper service."""
        self.scraper = WebScraper()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })

    def validate_url(self, url: str) -> None:
        """
        Validate the URL format and scheme.
        
        Args:
            url: The URL to validate
            
        Raises:
            BadRequest: If the URL is invalid or uses an unsupported scheme
        """
        if not url:
            raise BadRequest("URL is required")
            
        try:
            parsed = urlparse(url)
            if not all([parsed.scheme, parsed.netloc]):
                raise BadRequest("Invalid URL format")
                
            if parsed.scheme not in ['http', 'https']:
                raise BadRequest("Unsupported URL protocol. Only HTTP and HTTPS are supported.")
        except Exception as e:
            raise BadRequest(f"Invalid URL format: {str(e)}")

    def scrape_and_save(self, url: str) -> dict:
        """
        Scrape content from a URL and save relevant information.
        
        Args:
            url: The URL to scrape
            
        Returns:
            dict: The scraped and processed data
            
        Raises:
            BadRequest: For invalid URLs or client errors
            InternalServerError: For server errors or scraping failures
        """
        # Validate URL
        self.validate_url(url)
        
        try:
            # Get the HTML content
            downloaded = trafilatura.fetch_url(url)
            if downloaded is None:
                raise InternalServerError(f"Failed to fetch content from {url}")
                
            # Extract the main content
            result = trafilatura.extract(downloaded)
            if result is None:
                raise InternalServerError(f"Failed to extract content from {url}")
                
            # Process and return the result
            return {
                'url': url,
                'content': result
            }
            
        except requests.exceptions.RequestException as e:
            if hasattr(e.response, 'status_code'):
                if 400 <= e.response.status_code < 500:
                    raise BadRequest(f"Failed to fetch URL: {str(e)}")
                else:
                    raise InternalServerError(f"Server error while fetching URL: {str(e)}")
            raise InternalServerError(f"Failed to fetch URL: {str(e)}")
            
        except Exception as e:
            raise InternalServerError(f"Error processing URL: {str(e)}")

    