import logging
from typing import Optional

logger = logging.getLogger(__name__)

class SessionTitleGenerator:
    """Service for generating session titles based on user queries."""
    
    def __init__(self, llm):
        """
        Initialize the session title generator.
        
        Args:
            llm: The language model instance to use for title generation
        """
        self.llm = llm
    
    def generate_title(self, user_query: str) -> str:
        """
        Generate a concise, descriptive title based on the user's query.
        
        Args:
            user_query (str): The user's query to base the title on
            
        Returns:
            str: A generated title (or a fallback title if generation fails)
        """
        try:
            # Create a prompt for title generation
            prompt = f"""Given the following user query in a news chat application, generate a concise, descriptive title (5 words or less) that captures the main topic. The title should be informative but brief (30 characters max).

Query: '{user_query}'

Title:"""
            
            # Generate the title using the LLM
            response = self.llm.invoke(prompt)
            
            # Extract and clean the title
            title = response.content.strip()
            
            # Limit title length and remove any quotes
            title = title.replace('"', '').replace("'", "")
            if len(title) > 30:
                title = title[:27] + "..."
                
            logger.info(f"Generated title: '{title}' for query: '{user_query}'")
            return title
            
        except Exception as e:
            logger.error(f"Error generating title: {str(e)}")
            
            # Fallback title generation - extract first few words
            if len(user_query) > 30:
                fallback_title = user_query[:27] + "..."
            else:
                fallback_title = user_query
                
            logger.info(f"Using fallback title: '{fallback_title}'")
            return fallback_title


def get_title_generator(news_agent_service) -> Optional[SessionTitleGenerator]:
    """
    Create a session title generator using the LLM from the news agent service.
    
    Args:
        news_agent_service: The initialized news agent service with LLM
        
    Returns:
        SessionTitleGenerator: The title generator, or None if creation fails
    """
    try:
        if news_agent_service and hasattr(news_agent_service, 'llm'):
            return SessionTitleGenerator(news_agent_service.llm)
        else:
            logger.error("News agent service is not properly initialized")
            return None
    except Exception as e:
        logger.error(f"Error creating title generator: {str(e)}")
        return None 