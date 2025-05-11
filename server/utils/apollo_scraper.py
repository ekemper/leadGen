import asyncio
import logging
from playwright.async_api import async_playwright
from typing import List, Dict, Optional

logger = logging.getLogger("apollo_lead_scraper")

class ApolloLeadScraper:
    """
    Scraper for extracting leads from Apollo using Playwright for browser automation.
    """
    def __init__(self, email: str, password: str, headless: bool = True):
        self.email = email
        self.password = password
        self.headless = headless

    async def _login(self, page) -> None:
        """
        Log in to Apollo using provided credentials.
        """
        logger.info("Navigating to Apollo login page...")
        await page.goto("https://app.apollo.io/#/login", timeout=60000)
        await page.fill('input[name="email"]', self.email)
        await page.fill('input[name="password"]', self.password)
        await page.click('button[type="submit"]')
        # Wait for navigation or dashboard element
        await page.wait_for_selector('div[data-testid="dashboard-root"], div[role="main"]', timeout=60000)
        logger.info("Login successful.")

    async def _extract_leads(self, page) -> List[Dict]:
        """
        Extract leads from the loaded Apollo people search page.
        """
        logger.info("Extracting leads from Apollo search results...")
        # Wait for results to load
        await page.wait_for_selector('div[data-testid="PeopleSearchResults"]', timeout=60000)
        # Example: extract visible lead cards (customize as needed)
        leads = []
        cards = await page.query_selector_all('div[data-testid^="PeopleSearchResultCard"]')
        for card in cards:
            name = await card.query_selector_eval('a[data-testid="PersonName"]', 'el => el.textContent')
            title = await card.query_selector_eval('span[data-testid="PersonTitle"]', 'el => el.textContent')
            company = await card.query_selector_eval('a[data-testid="CompanyName"]', 'el => el.textContent')
            email = await card.query_selector_eval('span[data-testid="PersonEmail"]', 'el => el.textContent')
            leads.append({
                'name': name.strip() if name else None,
                'title': title.strip() if title else None,
                'company': company.strip() if company else None,
                'email': email.strip() if email else None,
            })
        logger.info(f"Extracted {len(leads)} leads.")
        return leads

    async def scrape_leads(self, search_url: str) -> List[Dict]:
        """
        Main method to log in, navigate to the search URL, and extract leads.
        """
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=self.headless)
            context = await browser.new_context()
            page = await context.new_page()
            try:
                await self._login(page)
                logger.info(f"Navigating to search URL: {search_url}")
                await page.goto(search_url, timeout=60000)
                leads = await self._extract_leads(page)
                return leads
            except Exception as e:
                logger.error(f"Apollo scraping failed: {e}")
                return []
            finally:
                await browser.close()

    def scrape_leads_sync(self, search_url: str) -> List[Dict]:
        """
        Synchronous wrapper for scrape_leads (for use in non-async code).
        """
        return asyncio.run(self.scrape_leads(search_url)) 