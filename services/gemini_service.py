import google.generativeai as genai
from flask import current_app
import logging

logger = logging.getLogger(__name__)

class GeminiService:
    def __init__(self, api_key=None):
        self.api_key = api_key or current_app.config.get('GOOGLE_API_KEY')
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel('gemini-1.5-flash')
    
    def process_query(self, user_query):
        """
        Process the user query to create an optimized search query
        
        Args:
            user_query (str): The original user query
            
        Returns:
            str: An optimized search query for news
        """
        prompt = f"""
        I need to search for relevant news articles about: "{user_query}"
        
        Please convert this into an optimized search query for a news search engine. 
        The query should:
        - Include relevant keywords
        - Be concise and focused
        - Remove unnecessary words
        - NOT include any explanations, just return the optimized query
        
        Optimized query:
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text.strip()
        except Exception as e:
            logger.error(f"Gemini API error: {str(e)}")
            return user_query  # Fall back to original query
    
    def filter_relevant_news(self, user_query, news_articles):
        """
        Filter and rank news articles by relevance to the user query
        
        Args:
            user_query (str): The original user query
            news_articles (list): List of news articles
            
        Returns:
            list: Filtered and ranked news articles
        """
        if not news_articles:
            return []
        
        # If we have fewer than 3 articles, just return them all
        if len(news_articles) <= 3:
            return news_articles
        
        # Create a concise representation of the articles for the prompt
        articles_text = ""
        for i, article in enumerate(news_articles):
            articles_text += f"Article {i+1}: {article['title']} - {article['description'][:100]}...\n"
        
        prompt = f"""
        Original user query: "{user_query}"
        
        I have the following news articles:
        {articles_text}
        
        Please analyze these articles and return ONLY the numbers of the articles 
        that are most relevant to the user's query, in order of relevance.
        Just give me a comma-separated list of article numbers, nothing else.
        For example: "3,1,5,2"
        """
        
        try:
            response = self.model.generate_content(prompt)
            article_indices = response.text.strip().split(',')
            
            # Convert to integers and subtract 1 for zero-indexing, filter out invalid indices
            filtered_indices = []
            for idx in article_indices:
                try:
                    index = int(idx.strip()) - 1
                    if 0 <= index < len(news_articles):
                        filtered_indices.append(index)
                except ValueError:
                    continue
            
            # Return the filtered and ranked articles
            return [news_articles[i] for i in filtered_indices]
        except Exception as e:
            logger.error(f"Gemini API error in filtering: {str(e)}")
            return news_articles  # Fall back to all articles