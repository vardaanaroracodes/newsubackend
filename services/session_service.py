from extensions import mongo
from datetime import datetime
import uuid

# Service for managing chat sessions in MongoDB.

def create_session(user_id):
    """Create a new chat session and return its session_id."""
    session_id = str(uuid.uuid4())
    session = {
        "session_id": session_id,
        "user_id": user_id,
        "messages": [],
        "created_at": datetime.utcnow()
    }
    mongo.db.chat_sessions.insert_one(session)
    return session_id


def add_message(session_id: str, role: str, content: str):
    """Add a message to the session's history."""
    message = {
        "role": role,
        "content": content,
        "timestamp": datetime.utcnow()
    }
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
    """List all chat sessions for a user with their creation time."""
    sessions = mongo.db.chat_sessions.find(
        {"user_id": user_id}, 
        {"_id": 0, "session_id": 1, "created_at": 1}
    )
    return [ {"session_id": s["session_id"], "created_at": s["created_at"]} for s in sessions ]


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
