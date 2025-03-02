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
        self.api_key = api_key
        self.headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }
        self.url = "https://google.serper.dev/news"
    
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
            payload = json.dumps({"q": query})
            response = requests.post(self.url, headers=self.headers, data=payload)
            response.raise_for_status()
            
            results = response.json().get("news", [])
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
        
        # Create the agent
        self._create_agent()
        
        # Initialize conversation history
        self.conversation_history = []
    
    def _create_agent(self):
        """Create the LangChain agent with the appropriate prompt."""
        
        # Get the ReAct format instructions
        output_parser = ReActSingleInputOutputParser()
        format_instructions = output_parser.get_format_instructions()
        
        # Create a prompt template
        prompt = PromptTemplate.from_template(
            """You are a helpful news assistant that can search for and summarize recent news.
            Always be conversational and friendly in your responses.
            
            When finding news:
            1. Search for the most relevant news articles
            2. Summarize the key points
            3. Add your own insights about the news
            4. Be concise yet informative
            
            Available tools: {tools}
            Tool names: {tool_names}
            
            {format_instructions}
            
            Previous conversation:
            {chat_history}
            
            Human: {input}
            
            {agent_scratchpad}
            
            Assistant: """
        )
        
        # Create the agent
        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )
        
        # Create the agent executor
        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=3
        )
    
    def generate_response(self, query: str) -> Dict[str, Any]:
        """
        Generate a response to the user's query
        
        Args:
            query (str): The user's question or request
            
        Returns:
            Dict[str, Any]: Response containing the agent's answer and context
        """
        try:
            # Add query to conversation history
            self.conversation_history.append(HumanMessage(content=query))
            
            # Convert conversation history to format expected by agent
            chat_history = "\n".join([
                f"Human: {msg.content}" if isinstance(msg, HumanMessage) else f"Assistant: {msg.content}"
                for msg in self.conversation_history[:-1]  # Exclude the latest query
            ])
            
            # Get the ReAct format instructions for this invocation
            output_parser = ReActSingleInputOutputParser()
            format_instructions = output_parser.get_format_instructions()
            
            # Run the agent
            result = self.agent_executor.invoke({
                "input": query,
                "chat_history": chat_history,
                "format_instructions": format_instructions
            })
            
            # Get the output
            response = result.get("output", "I'm sorry, I couldn't process that request.")
            
            # Add response to conversation history
            self.conversation_history.append(AIMessage(content=response))
            
            # Limit conversation history
            if len(self.conversation_history) > 10:
                self.conversation_history = self.conversation_history[-10:]
            
            return {
                "response": response,
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "success": True
            }
            
        except Exception as e:
            logger.error(f"Error generating response: {e}")
            return {
                "response": "I'm sorry, I encountered an error while processing your request.",
                "timestamp": datetime.now().isoformat(),
                "query": query,
                "success": False,
                "error": str(e)
            }
    
    def clear_conversation(self):
        """Clear the conversation history."""
        self.conversation_history = []
        return {"status": "Conversation history cleared"}