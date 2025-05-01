import json
from typing import Dict, Any
import sys
import os
from pathlib import Path

# Add the server directory to Python path
server_dir = str(Path(__file__).resolve().parent.parent.parent)
if server_dir not in sys.path:
    sys.path.insert(0, server_dir)

from utils.scraper import WebScraper

class ScraperService:
    def __init__(self):
        self.scraper = WebScraper()

    def scrape_and_save(self, url: str) -> Dict[str, Any]:
        """
        Scrapes the given URL and saves results to a temporary file.
        
        Args:
            url (str): The URL to scrape
            
        Returns:
            Dict[str, Any]: Dictionary containing success status, scraped data, and file location
            
        Raises:
            ValueError: If URL is invalid or missing
            Exception: For other scraping-related errors
        """
        if not url:
            raise ValueError("URL is required")

        # Scrape the URL
        result = self.scraper.scrape(url)
        
        # Save to temp file
        temp_file_path = 'temp_scrape_results.json'
        with open(temp_file_path, 'w', encoding='utf-8') as f:
            json.dump(result, f, ensure_ascii=False, indent=2)
        
        return {
            "success": True,
            "data": result,
            "file_location": temp_file_path
        } 