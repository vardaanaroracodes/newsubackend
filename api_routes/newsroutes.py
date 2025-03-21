from flask import Blueprint, request, jsonify, current_app
from .auth import require_api_key  # need this for server to server authentication
import logging
import os
from dotenv import load_dotenv

load_dotenv()
from services.newsagentservice import NewsAgentService

logger = logging.getLogger(__name__)

news_bp = Blueprint('news', __name__)

news_agent = None # Initialize news agent service

def get_news_agent():
    """
    Get or initialize the news agent service
    
    Returns:
        NewsAgentService: The news agent service
    """
    global news_agent
    
    if news_agent is None:
        GOOGLE_API_KEY = current_app.config.get('GOOGLE_API_KEY') or os.getenv('GOOGLE_API_KEY')
        serper_api_key = current_app.config.get('SERPER_API_KEY') or os.getenv('SERPER_API_KEY')
        
        if not GOOGLE_API_KEY or not serper_api_key:
            logger.error("Missing API keys")
            return None
       
        news_agent = NewsAgentService(
            GOOGLE_API_KEY=GOOGLE_API_KEY,
            serper_api_key=serper_api_key
        )
    
    return news_agent

@news_bp.route('/ask', methods=['POST'])
@require_api_key #decorator
def ask_news_agent():
    """
    API endpoint to ask questions to the news agent
    
    Expects JSON with 'query' field
    
    Returns:
        JSON response with the agent's answer
    """
    agent = get_news_agent()
    if agent is None:
        return jsonify({
            'success': False,
            'error': 'Could not initialize news agent service. Check API keys.'
        }), 500
    
    data = request.get_json()
    if not data or 'query' not in data:
        return jsonify({
            'success': False,
            'error': 'Missing query parameter in request body'
        }), 400
    
    user_query = data['query']
    
    try:
       
        result = agent.generate_response(user_query)
        return jsonify(result)
        
    except Exception as e:
        logger.error(f"Error processing news query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while processing your request',
            'details': str(e)
        }), 500

@news_bp.route('/clear', methods=['POST'])
@require_api_key 
# not in use, for future use.
def clear_conversation():
    """
    API endpoint to clear the conversation history
    
    Returns:
        JSON response indicating success or failure
    """
    agent = get_news_agent()
    if agent is None:
        return jsonify({
            'success': False,
            'error': 'Could not initialize news agent service. Check API keys.'
        }), 500
    
    try:
        
        result = agent.clear_conversation()
        return jsonify({
            'success': True,
            'message': 'Conversation history cleared'
        })
        
    except Exception as e:
        logger.error(f"Error clearing conversation: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while clearing the conversation',
            'details': str(e)
        }), 500

@news_bp.route('/history', methods=['GET'])
@require_api_key  # Add decorator
def get_conversation_history():
    """
    API endpoint to get the conversation history
    
    Returns:
        JSON response with the conversation history
    """
    agent = get_news_agent()
    if agent is None:
        return jsonify({
            'success': False,
            'error': 'Could not initialize news agent service. Check API keys.'
        }), 500
    
    try:
        history = agent.memory.chat_memory.messages
        return jsonify({
            'success': True,
            'history': [{'role': msg.type, 'content': msg.content} for msg in history]
        })
        
    except Exception as e:
        logger.error(f"Error getting conversation history: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while getting conversation history',
            'details': str(e)
        }), 500