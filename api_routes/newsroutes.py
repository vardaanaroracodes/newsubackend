from flask import Blueprint, request, jsonify, current_app
from .auth import require_api_key  # need this for server to server authentication
import logging
import os
from dotenv import load_dotenv
from services.session_service import (
    create_session, add_message, get_messages, list_sessions, 
    clear_messages, delete_session, update_session_title, get_session
)
from services.session_title_service import get_title_generator
from extensions import mongo  # Add this import to fix the undefined variable error

load_dotenv()
from services.newsagentservice import NewsAgentService

logger = logging.getLogger(__name__)

news_bp = Blueprint('news', __name__)

news_agent = None # Initialize news agent service
title_generator = None # Initialize title generator service

def get_news_agent():
    """
    Get or initialize the news agent service
    
    Returns:
        NewsAgentService: The news agent service
    """
    global news_agent, title_generator
    
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
        
        # Initialize title generator if not already done
        if title_generator is None:
            title_generator = get_title_generator(news_agent)
    
    return news_agent

def get_title_for_query(query):
    """
    Generate a title for a user query
    
    Args:
        query (str): The user query
        
    Returns:
        str: A generated title
    """
    global title_generator
    
    # Ensure the news agent and title generator are initialized
    agent = get_news_agent()
    if agent is None:
        logger.error("Could not initialize news agent service")
        return "New Conversation"
    
    if title_generator is None:
        logger.error("Could not initialize title generator")
        return "New Conversation"
    
    try:
        return title_generator.generate_title(query)
    except Exception as e:
        logger.error(f"Error generating title: {str(e)}")
        return "News Conversation"

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
    
    # Create session with default title (will be updated when first message is sent)
    session_id = create_session(data['user_id'])
    
    # If initial query is provided, use it to generate a title
    initial_title = "New Conversation"
    if 'initial_query' in data:
        initial_title = get_title_for_query(data['initial_query'])
        update_session_title(session_id, initial_title)
        
    return jsonify({
        'success': True, 
        'session_id': session_id,
        'title': initial_title
    })

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
    
    # If this is the first message in the session, generate a title
    is_first_message = len(history) == 0
    if is_first_message:
        title = get_title_for_query(user_query)
        update_session_title(session_id, title)
        logger.info(f"Generated title for new session: '{title}'")
    
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
    sources = result.get('sources')
    
    # Store AI response with sources as metadata
    add_message(session_id, 'ai', ai_resp, {"sources": sources} if sources else None)
    
    # Add session info to the result
    result['session_id'] = session_id
    
    # Get the current session title if this was the first message
    if is_first_message:
        result['title'] = title
    
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

@news_bp.route('/session/<session_id>', methods=['GET'])
@require_api_key
def get_session_route(session_id):
    """Get session details"""
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'error': 'Missing user_id parameter'}), 400
        
    session = get_session(session_id, user_id)
    if not session:
        return jsonify({'success': False, 'error': 'Session not found or unauthorized'}), 404
        
    return jsonify({'success': True, 'session': session})

@news_bp.route('/session/<session_id>/title', methods=['PUT'])
@require_api_key
def update_session_title_route(session_id):
    """Update a session's title"""
    data = request.get_json() or {}
    if 'user_id' not in data:
        return jsonify({'success': False, 'error': 'Missing user_id'}), 400
    if 'title' not in data:
        return jsonify({'success': False, 'error': 'Missing title'}), 400
    
    user_id = data['user_id']
    new_title = data['title']
    
    # Validate title length
    if len(new_title) > 30:
        new_title = new_title[:27] + "..."
    
    success = update_session_title(session_id, new_title, user_id)
    if not success:
        return jsonify({'success': False, 'error': 'Session not found or unauthorized'}), 404
        
    return jsonify({'success': True, 'title': new_title})

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



#---------------------------------
# Tracked Queries                 
#---------------------------------
# To be Reviewed
#---------------------------------

@news_bp.route('/tracked-queries', methods=['GET'])
@require_api_key
def get_tracked_queries():
    """
    Get all tracked queries for a specific user
    
    Query parameters:
        user_id: ID of the user to get tracked queries for
        
    Returns:
        JSON with tracked queries information
    """
    user_id = request.args.get('user_id')
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Missing user_id parameter'
        }), 400
    
    try:
        # Log the query attempt for debugging
        logger.info(f"Attempting to retrieve tracked queries for user_id: {user_id}")
        
        # Get the news_tracker database from the same MongoDB cluster
        db_name = "news_tracker"  # Specify the correct database name
        collection_name = "tracked_queries"  # Specify the correct collection name
        
        # Use the PyMongo client to access a different database in the same cluster
        mongo_client = mongo.cx  # Get the underlying PyMongo client
        news_tracker_db = mongo_client[db_name]  # Access the news_tracker database
        tracked_queries_collection = news_tracker_db[collection_name]  # Access the tracked_queries collection
        
        # Check if collection exists
        if collection_name not in news_tracker_db.list_collection_names():
            logger.warning(f"{collection_name} collection does not exist in the {db_name} database")
            # Create the collection if it doesn't exist
            news_tracker_db.create_collection(collection_name)
            logger.info(f"Created {collection_name} collection in {db_name} database")
            return jsonify({
                'success': True,
                'tracked_queries': [],
                'message': f'No queries found - collection was just created in {db_name} database'
            })
        
        # Count documents in collection for this user (for debugging)
        count = tracked_queries_collection.count_documents({"user_id": user_id})
        logger.info(f"Found {count} tracked queries for user_id: {user_id} in {db_name}.{collection_name}")
        
        # Find all tracked queries for this user
        tracked_queries = list(tracked_queries_collection.find(
            {"user_id": user_id},
            {"_id": 1, "query": 1, "is_active": 1, "created_at": 1, "updated_at": 1}
        ))
        
        # Convert ObjectId to string for JSON serialization
        for query in tracked_queries:
            query['_id'] = str(query['_id'])
        
        return jsonify({
            'success': True,
            'tracked_queries': tracked_queries,
            'count': len(tracked_queries),
            'database': db_name,
            'collection': collection_name
        })
        
    except Exception as e:
        logger.error(f"Error retrieving tracked queries: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while retrieving tracked queries',
            'details': str(e)
        }), 500

@news_bp.route('/tracked-queries/<query_id>', methods=['GET'])
@require_api_key
def get_tracked_query_details(query_id):
    """
    Get details of a specific tracked query by its ID
    
    Path parameters:
        query_id: ID of the tracked query to get details for
        
    Query parameters:
        user_id: ID of the user (for validation)
        include_history: Whether to include tracking history (default: true)
        
    Returns:
        JSON with tracked query details
    """
    user_id = request.args.get('user_id')
    include_history = request.args.get('include_history', 'true').lower() == 'true'
    
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Missing user_id parameter'
        }), 400
    
    try:
        from bson import ObjectId
        
        # Get the news_tracker database from the same MongoDB cluster
        db_name = "news_tracker"
        collection_name = "tracked_queries"
        
        # Use the PyMongo client to access a different database in the same cluster
        mongo_client = mongo.cx
        news_tracker_db = mongo_client[db_name]
        tracked_queries_collection = news_tracker_db[collection_name]
        
        # Check if the query_id is a valid ObjectId
        try:
            query_obj_id = ObjectId(query_id)
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid query ID format'
            }), 400
        
        # Set the projection based on whether to include history
        projection = None if include_history else {
            "_id": 1, 
            "user_id": 1, 
            "query": 1, 
            "is_active": 1, 
            "created_at": 1, 
            "updated_at": 1
        }
        
        # Find the tracked query document
        tracked_query = tracked_queries_collection.find_one({
            "_id": query_obj_id,
            "user_id": user_id
        }, projection)
        
        if not tracked_query:
            return jsonify({
                'success': False,
                'error': 'Tracked query not found or unauthorized access'
            }), 404
        
        # Convert ObjectId to string for JSON serialization
        tracked_query['_id'] = str(tracked_query['_id'])
        
        # Restructure the tracking_history if it exists
        if include_history and 'tracking_history' in tracked_query and tracked_query['tracking_history']:
            # Sort history by date (newest first) if not already sorted
            tracking_history = sorted(
                tracked_query['tracking_history'], 
                key=lambda x: x.get('date', ''), 
                reverse=True
            )
            
            # Extract the latest update and add it as a separate field for easy access in UI
            # This helps separate current tracking information from historical data
            latest_update = tracking_history[0]
            
            # Add latest update info directly to the tracked_query root level
            # This flattens the structure to make the latest data easier to access
            tracked_query['summary'] = latest_update.get('summary')
            tracked_query['update_date'] = latest_update.get('date')
            tracked_query['sources'] = latest_update.get('sources', {})
            tracked_query['changes'] = latest_update.get('changes')
            
            # Collect all sources from previous updates into a single archived_sources object
            # This simplifies history management by focusing only on source archives
            # rather than keeping full historical entries
            archived_sources = {}
            for history_item in tracking_history[1:]:
                sources = history_item.get('sources', {})
                for source_name, source_data in sources.items():
                    # Add timestamp to help identify when this source was relevant
                    if source_data and isinstance(source_data, dict):
                        source_data['archived_date'] = history_item.get('date')
                    archived_sources[source_name] = source_data
            
            # Add archived sources to the tracked query
            if archived_sources:
                tracked_query['archived_sources'] = archived_sources
            
            # Remove the original tracking_history from the response
            # This prevents duplication of data and simplifies the response structure
            tracked_query.pop('tracking_history', None)
            # Remove the latest_update field if it was added by previous version
            tracked_query.pop('latest_update', None)
        
        return jsonify({
            'success': True,
            'tracked_query': tracked_query
        })
        
    except Exception as e:
        logger.error(f"Error retrieving tracked query details: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while retrieving tracked query details',
            'details': str(e)
        }), 500
        
@news_bp.route('/tracked-queries', methods=['POST'])
@require_api_key
def create_tracked_query():
    """
    Create a new tracked query for a user
    
    Expects JSON with:
        user_id: ID of the user
        query: The news topic/query to track
        
    Returns:
        JSON with the created tracked query ID
    """
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Missing request body'
        }), 400
    
    user_id = data.get('user_id')
    query = data.get('query')
    
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Missing user_id parameter'
        }), 400
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Missing query parameter'
        }), 400
    
    try:
        from datetime import datetime
        
        # Get the news_tracker database from the same MongoDB cluster
        db_name = "news_tracker"
        collection_name = "tracked_queries"
        
        # Use the PyMongo client to access a different database in the same cluster
        mongo_client = mongo.cx
        news_tracker_db = mongo_client[db_name]
        tracked_queries_collection = news_tracker_db[collection_name]
        
        # Create the tracked query document
        new_tracked_query = {
            "user_id": user_id,
            "query": query,
            "is_active": True,
            "created_at": datetime.utcnow(),
            "updated_at": datetime.utcnow(),
            "tracking_history": []  # Initialize with empty history
        }
        
        # Insert the document
        result = tracked_queries_collection.insert_one(new_tracked_query)
        
        logger.info(f"Created tracked query with ID: {result.inserted_id} for user_id: {user_id}")
        
        return jsonify({
            'success': True,
            'message': 'Tracked query created successfully',
            'tracked_query_id': str(result.inserted_id)
        })
        
    except Exception as e:
        logger.error(f"Error creating tracked query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while creating the tracked query',
            'details': str(e)
        }), 500
        
@news_bp.route('/tracked-queries/<query_id>', methods=['DELETE'])
@require_api_key
def delete_tracked_query(query_id):
    """
    Delete a specific tracked query by its ID
    
    Path parameters:
        query_id: ID of the tracked query to delete
        
    Expects JSON with:
        user_id: ID of the user (for validation)
        
    Returns:
        JSON with success status
    """
    data = request.get_json()
    if not data:
        return jsonify({
            'success': False,
            'error': 'Missing request body'
        }), 400
    
    user_id = data.get('user_id')
    
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Missing user_id parameter'
        }), 400
    
    try:
        from bson import ObjectId
        
        # Get the news_tracker database from the same MongoDB cluster
        db_name = "news_tracker"
        collection_name = "tracked_queries"
        
        # Use the PyMongo client to access a different database in the same cluster
        mongo_client = mongo.cx
        news_tracker_db = mongo_client[db_name]
        tracked_queries_collection = news_tracker_db[collection_name]
        
        # Check if the query_id is a valid ObjectId
        try:
            query_obj_id = ObjectId(query_id)
        except Exception:
            return jsonify({
                'success': False,
                'error': 'Invalid query ID format'
            }), 400
        
        # Delete the document
        result = tracked_queries_collection.delete_one({
            "_id": query_obj_id,
            "user_id": user_id
        })
        
        if result.deleted_count == 0:
            return jsonify({
                'success': False,
                'error': 'Tracked query not found or unauthorized access'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Tracked query deleted successfully'
        })
        
    except Exception as e:
        logger.error(f"Error deleting tracked query: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while deleting the tracked query',
            'details': str(e)
        }), 500

