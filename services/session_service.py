from extensions import mongo
from datetime import datetime
import uuid
import logging

logger = logging.getLogger(__name__)

# Service for managing chat sessions in MongoDB.

def create_session(user_id, title=None):
    """Create a new chat session and return its session_id.
    
    Args:
        user_id (str): The user ID to associate with this session
        title (str, optional): Optional title for the session. If None, a default title will be used.
    
    Returns:
        str: The generated session ID
    """
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "title": title or "New Conversation",
        "messages": [],
        "created_at": datetime.utcnow()
    }
    mongo.db.chat_sessions.insert_one(session)
    return session_id


def add_message(session_id: str, role: str, content: str, metadata=None):
    """Add a message to the session's history.
    
    Args:
        session_id (str): The session ID
        role (str): The role of the message sender ('user' or 'ai')
        content (str): The message content
        metadata (dict, optional): Additional metadata to store with the message
    """
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
    
    # Add any additional metadata if provided
    if metadata:
        message.update(metadata)
        
    mongo.db.chat_sessions.update_one(
        {"session_id": session_id},
        {"$push": {"messages": message}}
    )


def get_messages(session_id: str, user_id=None):
    """Retrieve all messages for a given session.
    
    If user_id is provided, ensures the session belongs to that user."""
    query = {"session_id": session_id}
    if user_id:
        query["user_id"] = user_id
        
    session = mongo.db.chat_sessions.find_one(query)
    if not session:
        return []
    return session.get("messages", [])


def list_sessions(user_id):
    """List all chat sessions for a user with their creation time and title."""
    sessions = mongo.db.chat_sessions.find(
        {"user_id": user_id}, 
        {"_id": 0, "session_id": 1, "created_at": 1, "title": 1}
    )
    return [
        {
            "session_id": s["session_id"], 
            "created_at": s["created_at"],
            "title": s.get("title", "Untitled Conversation")
        } 
        for s in sessions
    ]


def clear_messages(session_id: str, user_id=None):
    """Clear messages for a given session.
    
    If user_id is provided, ensures the session belongs to that user."""
    query = {"session_id": session_id}
    if user_id:
        query["user_id"] = user_id
        
    mongo.db.chat_sessions.update_one(
        query,
        {"$set": {"messages": []}}
    )


def delete_session(session_id: str, user_id=None):
    """Delete a session entirely.
    
    If user_id is provided, ensures the session belongs to that user."""
    query = {"session_id": session_id}
    if user_id:
        query["user_id"] = user_id
        
    mongo.db.chat_sessions.delete_one(query)


def update_session_title(session_id: str, title: str, user_id=None):
    """Update the title of a session.
    
    Args:
        session_id (str): The session ID
        title (str): The new title for the session
        user_id (str, optional): If provided, ensures the session belongs to this user
        
    Returns:
        bool: True if the update was successful, False otherwise
    """
    query = {"session_id": session_id}
    if user_id:
        query["user_id"] = user_id
        
    result = mongo.db.chat_sessions.update_one(
        query,
        {"$set": {"title": title}}
    )
    
    return result.modified_count > 0


def get_session(session_id: str, user_id=None):
    """Get a session by ID.
    
    Args:
        session_id (str): The session ID
        user_id (str, optional): If provided, ensures the session belongs to this user
        
    Returns:
        dict: The session document, or None if not found
    """
    query = {"session_id": session_id}
    if user_id:
        query["user_id"] = user_id
        
    return mongo.db.chat_sessions.find_one(query, {"_id": 0})
