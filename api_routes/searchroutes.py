from flask import Blueprint, request, jsonify
from extensions import mongo
from .auth import require_api_key
import logging
import re

logger = logging.getLogger(__name__)

search_bp = Blueprint('search', __name__)

@search_bp.route('', methods=['GET'])
@require_api_key
def search_conversations():
    """
    Search through user conversations and titles.
    
    Query parameters:
        query: The search term
        user_id: ID of the user whose conversations to search
        
    Returns:
        JSON with matched sessions/conversations
    """
    query = request.args.get('query')
    user_id = request.args.get('user_id')
    
    if not query:
        return jsonify({
            'success': False,
            'error': 'Missing query parameter'
        }), 400
        
    if not user_id:
        return jsonify({
            'success': False,
            'error': 'Missing user_id parameter'
        }), 400
    
    try:
        logger.info(f"Searching for '{query}' in conversations for user_id: {user_id}")
        
        # Create regex pattern for case-insensitive search
        pattern = re.compile(f'.*{re.escape(query)}.*', re.IGNORECASE)
        
        # Search for the query in titles and message content
        results = mongo.db.chat_sessions.find({
            "user_id": user_id,
            "$or": [
                {"title": {"$regex": pattern}},
                {"messages.content": {"$regex": pattern}}
            ]
        }, {
            "session_id": 1,
            "title": 1, 
            "created_at": 1,
            "messages": 1
        })
        
        # Format the results
        formatted_results = []
        for session in results:
            # Format session data
            session_data = {
                "session_id": session["session_id"],
                "title": session.get("title", "Untitled Conversation"),
                "created_at": session.get("created_at"),
                "matched_messages": []
            }
            
            # Find matching messages
            for msg in session.get("messages", []):
                content = msg.get("content", "")
                if re.search(pattern, content):
                    # Add matched message with limited preview
                    preview = content[:100] + "..." if len(content) > 100 else content
                    session_data["matched_messages"].append({
                        "role": msg.get("role"),
                        "timestamp": msg.get("timestamp"),
                        "preview": preview
                    })
            
            # Add to results even if no messages matched (title match)
            formatted_results.append(session_data)
        
        return jsonify({
            'success': True,
            'results': formatted_results,
            'count': len(formatted_results)
        })
        
    except Exception as e:
        logger.error(f"Error searching conversations: {str(e)}")
        return jsonify({
            'success': False,
            'error': 'An error occurred while searching conversations',
            'details': str(e)
        }), 500