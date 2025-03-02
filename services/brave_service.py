import requests
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class BraveSearchService:
    def __init__(self, api_key=None):
        self.api_key = api_key or current_app.config.get('BRAVE_API_KEY')
        self.base_url = current_app.config.get('BRAVE_SEARCH_URL', "https://api.search.brave.com/news")
        self.limit = current_app.config.get('NEWS_RESULTS_LIMIT', 10)
    
    def search_news(self, query):
        """
        Search for news using the Brave Search API
        
        Args:
            query (str): The search query
            
        Returns:
            dict: The API response
        """
        headers = {
            "Accept": "application/json",
            "X-Subscription-Token": self.api_key
        }
        
        params = {
            "q": query,
            "count": self.limit,
            "search_lang": "en"
        }
        
        try:
            response = requests.get(
                self.base_url,
                headers=headers,
                params=params
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Brave Search API error: {str(e)}")
            return {"error": str(e)}
    
    def extract_relevant_news(self, response):
        """
        Extract relevant information from the Brave Search API response
        
        Args:
            response (dict): The API response
            
        Returns:
            list: List of news articles with extracted information
        """
        if "error" in response:
            return []
        
        news_articles = []
        try:
            for article in response.get("news", []):
                news_articles.append({
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", ""),
                    "published_time": article.get("published_time", ""),
                    "source": article.get("source", ""),
                    "image_url": article.get("image", {}).get("url", "")
                })
            return news_articles
        except (KeyError, TypeError) as e:
            logger.error(f"Error extracting news data: {str(e)}")
            return []