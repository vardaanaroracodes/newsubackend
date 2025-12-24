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

class NewsVerificationTool:
    """Tool to verify news authenticity based on source priority lists."""

    # Priority 1: Government of India and official government portals
    PRIORITY_1_DOMAINS = [
        'gov.in',
        'nic.in',
        'indianarmy.nic.in',
        'indiannavy.nic.in',
        'indianairforce.nic.in',
        'pib.gov.in',
        'pmindia.gov.in',
        'mha.gov.in',
        'mea.gov.in',
        'mod.gov.in',
        'pib.nic.in'
    ]

    # Priority 2: Independent established news organizations
    PRIORITY_2_DOMAINS = [
        'thehindu.com',
        'timesofIndia.indiatimes.com',
        'indianexpress.com',
        'hindustantimes.com',
        'ndtv.com',
        'thequint.com',
        'scroll.in',
        'theprint.in',
        'news18.com',
        'indiatoday.in',
        'bbc.com/news',
        'reuters.com',
        'apnews.com',
        'firstpost.com',
        'outlookindia.com'
    ]

    # Keywords indicating national/government-related news
    NATIONAL_KEYWORDS = [
        'government', 'ministry', 'minister', 'parliament', 'lok sabha', 'rajya sabha',
        'prime minister', 'pm modi', 'president', 'cabinet', 'central government',
        'army', 'navy', 'air force', 'defence', 'defense', 'military', 'armed forces',
        'pib', 'ministry of', 'govt', 'national security', 'border', 'policy',
        'legislation', 'bill passed', 'amendment', 'supreme court', 'election commission',
        'rbi', 'reserve bank', 'finance ministry', 'budget', 'gst', 'tax policy',
        'foreign affairs', 'diplomacy', 'bilateral', 'treaty', 'mea',
        'home ministry', 'mha', 'law and order', 'national'
    ]

    def __init__(self):
        pass

    def _is_national_news(self, search_results: List[Dict[str, Any]], query: str = "") -> bool:
        """
        Determine if the news is related to national/government issues.

        Args:
            search_results: List of search results
            query: The original search query

        Returns:
            bool: True if news is national/government-related
        """
        # Combine all text from query, titles, and snippets
        text_to_check = query.lower()

        for result in search_results:
            title = result.get('title', '').lower()
            snippet = result.get('snippet', '').lower()
            text_to_check += f" {title} {snippet}"

        # Check if any national keyword is present
        for keyword in self.NATIONAL_KEYWORDS:
            if keyword in text_to_check:
                return True

        return False

    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        from urllib.parse import urlparse
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            # Remove www. prefix
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
        except Exception:
            return ""

    def _check_domain_priority(self, domain: str) -> int:
        """
        Check which priority list the domain belongs to.
        Returns: 1, 2, or 3 based on priority
        """
        # Check Priority 1
        for p1_domain in self.PRIORITY_1_DOMAINS:
            if domain.endswith(p1_domain) or domain == p1_domain:
                return 1

        # Check Priority 2
        for p2_domain in self.PRIORITY_2_DOMAINS:
            if domain.endswith(p2_domain) or domain == p2_domain:
                return 2

        # Priority 3: Everything else
        return 3

    def verify_news(self, search_results: List[Dict[str, Any]], query: str = "") -> Dict[str, Any]:
        """
        Verify news based on search results and source domains.

        Args:
            search_results: List of search results with 'link' field
            query: The original search query to determine news context

        Returns:
            Dict with verification status and details
        """
        if not search_results:
            return {
                'verified': False,
                'status': 'no_results',
                'message': 'No search results available for verification.',
                'priority_breakdown': {},
                'is_national_news': False
            }

        # Determine if this is national/government-related news
        is_national = self._is_national_news(search_results, query)

        priority_counts = {1: 0, 2: 0, 3: 0}
        priority_sources = {1: [], 2: [], 3: []}

        for result in search_results:
            link = result.get('link') or result.get('url', '')
            if not link:
                continue

            domain = self._extract_domain(link)
            priority = self._check_domain_priority(domain)

            priority_counts[priority] += 1
            priority_sources[priority].append({
                'title': result.get('title', 'No title'),
                'domain': domain,
                'link': link
            })

        # Determine verification status based on priority logic
        verification_result = self._determine_verification_status(
            priority_counts,
            priority_sources,
            len(search_results),
            is_national
        )

        verification_result['is_national_news'] = is_national

        return verification_result

    def _determine_verification_status(
        self,
        priority_counts: Dict[int, int],
        priority_sources: Dict[int, List[Dict]],
        total_results: int,
        is_national_news: bool
    ) -> Dict[str, Any]:
        """
        Determine the final verification status based on priority distribution.

        Args:
            priority_counts: Count of sources by priority level
            priority_sources: Actual sources grouped by priority
            total_results: Total number of results
            is_national_news: Whether the news is national/government-related

        Returns:
            Dict with verification details
        """

        # Priority 1: Government sources - ONLY for national/government news
        if is_national_news and priority_counts[1] > 0:
            return {
                'verified': True,
                'status': 'verified',
                'confidence': 'high',
                'message': f'✓ Verified by our algorithm. Found in {priority_counts[1]} official government source(s).',
                'priority_breakdown': {
                    'government_sources': priority_counts[1],
                    'independent_news': priority_counts[2],
                    'other_sources': priority_counts[3]
                },
                'sources_by_priority': priority_sources
            }

        # Priority 2: Independent news organizations
        if priority_counts[2] > 0:
            # If found in multiple independent sources (2+), mark as fully verified
            if priority_counts[2] >= 2:
                return {
                    'verified': True,
                    'status': 'fully_verified',
                    'confidence': 'medium-high',
                    'message': f'✓ Fully verified. Found in {priority_counts[2]} independent news source(s).',
                    'priority_breakdown': {
                        'government_sources': priority_counts[1] if is_national_news else 0,
                        'independent_news': priority_counts[2],
                        'other_sources': priority_counts[3]
                    },
                    'sources_by_priority': priority_sources
                }
            else:
                # Only 1 independent source
                return {
                    'verified': True,
                    'status': 'partially_verified',
                    'confidence': 'medium',
                    'message': f'⚠ Partially verified. Found in {priority_counts[2]} independent news source(s). Additional confirmation recommended.',
                    'priority_breakdown': {
                        'government_sources': priority_counts[1] if is_national_news else 0,
                        'independent_news': priority_counts[2],
                        'other_sources': priority_counts[3]
                    },
                    'sources_by_priority': priority_sources
                }

        # Priority 3: Only local/other sources
        return {
            'verified': False,
            'status': 'unverified',
            'confidence': 'low',
            'message': f'⚠ Cannot confirm authenticity. Found only in {priority_counts[3]} local/other source(s). Needs time to verify from credible sources.',
            'priority_breakdown': {
                'government_sources': 0,
                'independent_news': 0,
                'other_sources': priority_counts[3]
            },
            'sources_by_priority': priority_sources
        }

    def __call__(self, search_results_json: str) -> str:
        """
        LangChain-compatible callable interface.

        Args:
            search_results_json: JSON string of search results

        Returns:
            Formatted verification result as string
        """
        try:
            # Parse the input - it could be JSON or we need to access from the search tool
            search_results = json.loads(search_results_json) if isinstance(search_results_json, str) else search_results_json

            if not isinstance(search_results, list):
                return "Invalid input: Expected a list of search results."

            result = self.verify_news(search_results)

            # Format the output for the agent
            output = f"\n{'='*60}\n"
            output += f"VERIFICATION RESULT\n"
            output += f"{'='*60}\n\n"
            output += f"Status: {result['status'].upper()}\n"
            output += f"Confidence: {result['confidence']}\n\n"
            output += f"{result['message']}\n\n"

            breakdown = result['priority_breakdown']
            output += f"Source Breakdown:\n"
            output += f"  • Official Government Sources: {breakdown['government_sources']}\n"
            output += f"  • Independent News Organizations: {breakdown['independent_news']}\n"
            output += f"  • Other Local Sources: {breakdown['other_sources']}\n"

            return output

        except Exception as e:
            logger.error(f"Error in NewsVerificationTool: {e}")
            return f"Error during verification: {str(e)}"

class SerperNewsSearchTool:
    def __init__(self, api_key):
        if isinstance(api_key, tuple):
            self.api_key = api_key[0]
        else:
            self.api_key = api_key
        print(self.api_key)
        self.headers = {
            'X-API-KEY': str(self.api_key),
            'Content-Type': 'application/json'
        }
        self.url = "https://google.serper.dev/search" # goes and searches here(whatever query you perform)
    
    def search(self, query: str, limit: int = 30) -> List[Dict[str, Any]]:
        """
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
                "search_type": "news" 
            })
            response = requests.request("POST", self.url, headers=self.headers, data=payload)
            response.raise_for_status()
            data = response.json()
            results = data.get("organic", []) #use 'organic' instead of 'news'
            # store the raw results and the query on the instance so the agent can access them
            self._last_results = results[:limit]
            self._last_query = query
            return self._last_results
            
        except Exception as e:
            logger.error(f"Error searching news with Serper: {e}")
            return []
    
    """
    Call here acts as the bridge between langchain 
    react agent and raw news search
    Also we are using call because LangChain works on standardized
    interface which means it gives a string input and demands a string output
    so call is the best way to do that.
    """
    def __call__(self, query: str) -> str:
        results = self.search(query)
        # Debug: show raw search results returned by the search tool when invoked by the agent
        try:
            print("[SearchTool] raw results:", results)
        except Exception:
            # ensure printing never raises
            pass
        
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

"""
Integrates langchain,google gemini and serper api 
"""
class NewsAgentService:
    """Service that provides a conversational news agent using LangChain, Gemini, and Serper."""
    
    def __init__(self, GOOGLE_API_KEY: str, serper_api_key: str):
        self.GOOGLE_API_KEY = GOOGLE_API_KEY
        self.serper_api_key = serper_api_key
        
        self.llm = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash",
            GOOGLE_API_KEY=self.GOOGLE_API_KEY,
            temperature=0.7,
            convert_system_message_to_human=True
        )

        self.search_tool = SerperNewsSearchTool(api_key=self.serper_api_key)
        self.verification_tool = NewsVerificationTool()

        # Create a wrapper function for verification that accesses the search tool's results
        def verify_latest_news(input_text: str) -> str:
            """Verify the latest search results from the NewsSearch tool."""
            last_results = getattr(self.search_tool, "_last_results", None)
            last_query = getattr(self.search_tool, "_last_query", "")

            if not last_results:
                return "No search results available to verify. Please use NewsSearch first."

            # Pass both results and query to determine if it's national news
            verification_result = self.verification_tool.verify_news(last_results, last_query)

            # Format the output for the agent
            output = f"\n{'='*60}\n"
            output += f"VERIFICATION RESULT\n"
            output += f"{'='*60}\n\n"

            # Add context about national news detection
            if verification_result.get('is_national_news'):
                output += f"News Type: National/Government-related\n"
            else:
                output += f"News Type: General/Non-governmental\n"

            output += f"Status: {verification_result['status'].upper()}\n"
            output += f"Confidence: {verification_result['confidence']}\n\n"
            output += f"{verification_result['message']}\n\n"

            breakdown = verification_result['priority_breakdown']
            output += f"Source Breakdown:\n"

            # Only show government sources if it's national news
            if verification_result.get('is_national_news'):
                output += f"  • Official Government Sources: {breakdown['government_sources']}\n"

            output += f"  • Independent News Organizations: {breakdown['independent_news']}\n"
            output += f"  • Other Local Sources: {breakdown['other_sources']}\n"

            # Store verification result for later use in response
            self._last_verification = verification_result

            return output

        self.tools = [
            Tool(
                name="NewsSearch",
                func=self.search_tool,
                description="Use this tool to search for news articles and information from the web. Use this only for news-related queries, not for greetings or general conversation."
            ),
            Tool(
                name="VerifyNews",
                func=verify_latest_news,
                description="Use this tool AFTER using NewsSearch to verify the authenticity of the news based on source credibility. This tool analyzes whether the news comes from official government sources, established independent news organizations, or local sources."
            )
        ]

        self.memory = ConversationBufferMemory()
        self.conversation = ConversationChain(
            llm=self.llm,
            memory=self.memory,
            verbose=True
        )

        self._create_agent()
    
    def _create_agent(self):
        """Create the LangChain agent with the appropriate prompt."""
        
        # prompt template with the correct ReAct format and chat history
        prompt = PromptTemplate.from_template(
            """You are a helpful news assistant that can search for and verify recent news.
            Always be conversational and friendly in your responses.

            When finding news, follow this workflow:
            1. Use NewsSearch to find the most relevant news articles
            2. ALWAYS use VerifyNews immediately after NewsSearch to check the authenticity of the news
            3. In your final answer, include:
               - A summary of the key points from the news
               - The verification status (verified/partially verified/unverified)
               - Which types of sources reported the news
               - Your insights about the news
            4. Be concise yet informative

            IMPORTANT: For every news query, you MUST use both NewsSearch AND VerifyNews tools in sequence.

            Previous conversation history:
            {chat_history}

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

        self.agent = create_react_agent(
            llm=self.llm,
            tools=self.tools,
            prompt=prompt
        )

        self.agent_executor = AgentExecutor.from_agent_and_tools(
            agent=self.agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
            max_iterations=100
        )

    def generate_response(self, query: str) -> Dict[str, Any]:
        """Generate a response to the user's query"""
        try:
            # Format the conversation history in a structured way the model can understand
            chat_history = ""
            if self.memory.chat_memory.messages:
                for message in self.memory.chat_memory.messages:
                    if message.type == 'human':
                        chat_history += f"User: {message.content}\n"
                    else:
                        chat_history += f"Assistant: {message.content}\n"
            
            # Execute the agent with properly formatted chat history
            response = self.agent_executor.invoke({
                "input": query,
                "chat_history": chat_history
            })
            
            # Add the interaction to memory
            self.memory.chat_memory.add_user_message(query)
            self.memory.chat_memory.add_ai_message(response['output'])
            
            # Decide whether to fetch/ reuse search results.
            # For simple greetings we don't want any sources.
            def _is_greeting(q: str) -> bool:
                if not q:
                    return False
                qn = q.lower().strip()
                qn = qn.strip(".!?,")
                greetings = {"hi", "hello", "hey", "hey there", "good morning", "good afternoon", "good evening", "yo"}
                # exact match or first token is a greeting
                tokens = qn.split()
                return qn in greetings or (tokens and tokens[0] in greetings)

            sources: List[Dict[str, Any]] = []

            if _is_greeting(query):
                # Do not call search for greetings — return empty sources
                search_results = []
            else:
                # Prefer the results the tool stored while the agent was running.
                last_results = getattr(self.search_tool, "_last_results", None)
                last_query = getattr(self.search_tool, "_last_query", None)

                if last_results and last_query == query:
                    search_results = last_results
                else:
                    # Fallback: perform a direct search for this query
                    search_results = self.search_tool.search(query)

            # Transform Serper raw results into the expected 'sources' shape
            for idx, item in enumerate(search_results or [], start=1):
                src = {
                    "title": item.get("title", ""),
                    "link": item.get("link") or item.get("url") or "",
                    "snippet": item.get("snippet", ""),
                    "position": item.get("position") if item.get("position") is not None else idx
                }
                if item.get("date"):
                    src["date"] = item.get("date")
                sources.append(src)

            # Debug: log what the search tool returned to be used as sources
            try:
                print("[NewsAgentService] sources formed from Serper response:", sources)
            except Exception:
                pass

            # Include verification status in response if available
            verification_status = getattr(self, "_last_verification", None)

            response_data = {
                'success': True,
                'response': response['output'],
                'sources': sources
            }

            # Add verification data if available
            if verification_status:
                response_data['verification'] = {
                    'verified': verification_status.get('verified', False),
                    'status': verification_status.get('status', 'unknown'),
                    'confidence': verification_status.get('confidence', 'unknown'),
                    'message': verification_status.get('message', ''),
                    'is_national_news': verification_status.get('is_national_news', False),
                    'priority_breakdown': verification_status.get('priority_breakdown', {})
                }
                # Clear the verification after using it
                self._last_verification = None

            return response_data
            
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