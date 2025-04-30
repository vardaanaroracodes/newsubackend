from flask import Blueprint, request, jsonify, current_app
from .auth import require_api_key  # need this for server to server authentication
import logging
import os
from dotenv import load_dotenv
from services.session_service import create_session, add_message, get_messages, list_sessions, clear_messages, delete_session
from extensions import mongo  # Add this import to fix the undefined variable error

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

# Session management endpoints
@news_bp.route('/session/start', methods=['POST'])
@require_api_key
def start_session():
    """Start a new chat session"""
    data = request.get_json() or {}
    if 'user_id' not in data:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
    
    session_id = create_session(data['user_id'])
    return jsonify({'success': True, 'session_id': session_id})

@news_bp.route('/session/<session_id>/ask', methods=['POST'])
@require_api_key
def ask_session(session_id):
    """Ask within an existing session"""
    data = request.get_json() or {}
    if 'query' not in data:
        return jsonify({'success': False, 'error': 'Missing query'}), 400
    if 'user_id' not in data:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
    
    user_id = data['user_id']
    user_query = data['query']
    
    # Retrieve and seed conversation memory from DB
    agent = get_news_agent()
    if agent is None:
        return jsonify({'success': False, 'error': 'Init error'}), 500
    
    # First check if the session exists and belongs to the user
    session = mongo.db.chat_sessions.find_one({"session_id": session_id})
    if session:
        # Session exists, check if it belongs to this user
        if session.get("user_id") != user_id:
            return jsonify({'success': False, 'error': 'Unauthorized access to session'}), 403
    else:
        # Session doesn't exist at all
        return jsonify({'success': False, 'error': 'Session not found'}), 404
    
    # Get message history (might be empty for new sessions)
    history = get_messages(session_id, user_id)
    logger.info(f"Loading {len(history)} messages from session {session_id}")
    
    # Clear current agent memory and load history
    agent.memory.clear()
    for msg in history:
        if msg['role'] == 'user':
            agent.memory.chat_memory.add_user_message(msg['content'])
            logger.debug(f"Added user message to memory: {msg['content'][:50]}...")
        elif msg['role'] == 'ai':
            agent.memory.chat_memory.add_ai_message(msg['content'])
            logger.debug(f"Added AI message to memory: {msg['content'][:50]}...")
    
    # Log memory state for debugging        
    memory_messages = agent.memory.chat_memory.messages
    logger.info(f"Agent memory now has {len(memory_messages)} messages")
    
    # Store user message and generate response
    add_message(session_id, 'user', user_query)
    
    # Generate response with history context
    result = agent.generate_response(user_query)
    ai_resp = result.get('response')
    add_message(session_id, 'ai', ai_resp)
    result['session_id'] = session_id
    return jsonify(result)

@news_bp.route('/sessions', methods=['GET'])
@require_api_key
def get_sessions_route():
    """List all chat sessions for a user"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Missing user_id parameter'}), 400
        
    sessions = list_sessions(user_id)
    return jsonify({'success': True, 'sessions': sessions})

@news_bp.route('/session/<session_id>/history', methods=['GET'])
@require_api_key
def session_history(session_id):
    """Get history for a session"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Missing user_id parameter'}), 400
        
    messages = get_messages(session_id, user_id)
    if not messages and mongo.db.chat_sessions.find_one({"session_id": session_id}):
        # Session exists but doesn't belong to this user
        return jsonify({'success': False, 'error': 'Session not found or unauthorized'}), 403
        
    return jsonify({'success': True, 'history': messages})

@news_bp.route('/session/<session_id>/clear', methods=['POST'])
@require_api_key
def clear_session_route(session_id):
    """Clear messages for a session"""
    data = request.get_json() or {}
    if 'user_id' not in data:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
    clear_messages(session_id, data['user_id'])
    return jsonify({'success': True, 'message': 'Session cleared'})

@news_bp.route('/session/<session_id>/delete', methods=['DELETE'])
@require_api_key
def delete_session_route(session_id):
    """Delete a session entirely"""
    data = request.get_json() or {}
    if 'user_id' not in data:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
        
    delete_session(session_id, data['user_id'])
    return jsonify({'success': True, 'message': 'Session deleted'})