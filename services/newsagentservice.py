import os
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_react_agent
from langchain.prompts import PromptTemplate
from langchain.tools import Tool
from langchain.chains import LLMChain
from langchain_core.prompts import MessagesPlaceholder
from langchain_core.messages import AIMessage, HumanMessage
from langchain.agents.format_scratchpad import format_to_openai_function_messages
from langchain.agents.output_parsers import ReActSingleInputOutputParser
import json

logger = logging.getLogger(__name__)

class SerperNewsSearchTool:
    """Tool for searching news using Serper API."""
    
    def __init__(self, api_key):
        # Convert tuple to string if necessary
        if isinstance(api_key, tuple):
            self.api_key = api_key[0]
        else:
            self.api_key = api_key
        print(self.api_key)
        self.headers = {
            'X-API-KEY': str(self.api_key),  # Ensure string type
            'Content-Type': 'application/json'
        }
        self.url = "https://google.serper.dev/search"
    
    def search(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search for news using Serper API
        
        Args:
            query (str): The search query
            limit (int): Maximum number of results to return
            
        Returns:
            List[Dict[str, Any]]: List of news articles
        """
        import requests
        
        try:
            payload = json.dumps({
                "q": query,
                "search_type": "news"  # Specify news search type
            })
            
            response = requests.request("POST", self.url, headers=self.headers, data=payload)
            response.raise_for_status()
            
            data = response.json()
            
            # The response structure is different, adjust accordingly
            results = data.get("organic", [])  # Use 'organic' instead of 'news'
            return results[:limit]
            
        except Exception as e:
            logger.error(f"Error searching news with Serper: {e}")
            return []
    
    def __call__(self, query: str) -> str:
        """
        Call the tool and return formatted results
        
        Args:
            query (str): The search query
            
        Returns:
            str: Formatted news results
        """
        results = self.search(query)
        
        if not results:
            return "No news articles found for the query."
        
        formatted_results = "Here are the latest news articles I found:\n\n"
        
        for i, article in enumerate(results, 1):
            title = article.get("title", "No title")
            link = article.get("link", "")
            source = article.get("source", "Unknown source")
            date = article.get("date", "")
            snippet = article.get("snippet", "No description available")
            
            formatted_results += f"{i}. **{title}**\n"
            formatted_results += f"   Source: {source}"
            if date:
                formatted_results += f" | {date}"
            formatted_results += f"\n   {snippet}\n"
            formatted_results += f"   Link: {link}\n\n"
        
        return formatted_results


from langchain.memory import ConversationBufferMemory
from langchain.chains import ConversationChain

class NewsAgentService:
    """Service that provides a conversational news agent using LangChain, Gemini, and Serper."""
    
    def __init__(self, GOOGLE_API_KEY: str, serper_api_key: str):
        """
        Initialize the news agent service
        
        Args:
            GOOGLE_API_KEY (str): API key for Google Gemini
            serper_api_key (str): API key for Serper
        """
        self.GOOGLE_API_KEY = GOOGLE_API_KEY
        self.serper_api_key = serper_api_key
        
        # Initialize the LLM
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-1.5-flash",
            GOOGLE_API_KEY=self.GOOGLE_API_KEY,
            temperature=0.7,
            convert_system_message_to_human=True
        )
        
        # Initialize the search tool
        self.search_tool = SerperNewsSearchTool(api_key=self.serper_api_key)
        
        # Create LangChain tools
        self.tools = [
            Tool(
                name="NewsSearch",
                func=self.search_tool,
                description="Useful for searching and finding recent news articles on specific topics. Input should be a search query."
            )
        ]
        
        # Initialize conversation memory first
        self.memory = ConversationBufferMemory()
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=True
        )
        
        # Create the agent after memory is initialized
        self._create_agent()
    
    def _create_agent(self):
        """Create the LangChain agent with the appropriate prompt."""
        
        # Create a prompt template with the correct ReAct format
        prompt = PromptTemplate.from_template(
            """You are a helpful news assistant that can search for and summarize recent news.
            Always be conversational and friendly in your responses.
            
            When finding news:
            1. Search for the most relevant news articles
            2. Summarize the key points
            3. Add your own insights about the news
            4. Be concise yet informative
            
            Available tools: {tools}
            
            Use the following format:
            
            Question: the input question you must answer
            Thought: you should always think about what to do
            Action: the action to take, should be one of [{tool_names}]
            Action Input: the input to the action
            Observation: the result of the action
            ... (this Thought/Action/Action Input/Observation can repeat N times)
            Thought: I now know the final answer
            Final Answer: the final answer to the original input question
            
            Begin!
            
            Question: {input}
            {agent_scratchpad}"""
        )
        
        # Create the agent with explicit input variables
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create the agent executor without memory parameter
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )

    def prepare_context(self, search_results: List[Dict[str, Any]]) -> str:
        """
        Prepare context from search results
        
        Args:
            search_results (List[Dict[str, Any]]): List of news articles
            
        Returns:
            str: Formatted context string
        """
        if not search_results:
            return "No relevant news articles found."
            
        context = "Here are the relevant news articles:\n\n"
        
        for i, article in enumerate(search_results, 1):
            title = article.get("title", "No title")
            snippet = article.get("snippet", "No description available")
            source = article.get("source", "Unknown source")
            date = article.get("date", "")
            
            context += f"{i}. {title}\n"
            context += f"   {snippet}\n"
            context += f"   Source: {source}"
            if date:
                context += f" | {date}"
            context += "\n\n"
            
        return context

    def generate_response(self, query: str) -> Dict[str, Any]:
        """Generate a response to the user's query"""
        try:
            # Use the agent executor with just the query
            response = self.agent_executor.invoke({"input": query})
            
            # Add the interaction to memory
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(response['output'])
            
            # Get the latest search results from the tool
            search_results = self.search_tool.search(query)
            
            return {
                'success': True,
                'response': response['output'],
                'sources': search_results
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "success": False,
                "response": "I'm sorry, I encountered an error while processing your request.",
                "error": str(e)
            }

    def clear_conversation(self):
        """Clear the conversation history."""
        self.memory.clear()
        return {"status": "Conversation history cleared"}