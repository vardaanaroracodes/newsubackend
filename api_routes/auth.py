from flask import Blueprint, request, jsonify, current_app
from functools import wraps
from dotenv import load_dotenv
import os
from bson.objectid import ObjectId
import datetime
from clerk_backend_api import Clerk
import json

load_dotenv()
auth_bp = Blueprint('auth_bp', __name__)

# Initialize Clerk client
clerk = Clerk(bearer_auth=os.getenv('CLERK_SECRET_KEY'))

def require_session(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        session_token = request.headers.get('Auth-Session-Id')
        if not session_token:
            return jsonify({'message': 'No session token provided'}), 401
        
        try:
            # Verify the session token using Clerk
            response = clerk.sessions.get(session_id=session_token)
            session_data = json.loads(response.model_dump_json())
            
            # Check session status
            if session_data.get('status') != 'active':
                return jsonify({'message': 'Session is not active'}), 401
            
            # Add user_id to request context for use in routes
            request.user_id = session_data.get('user_id')
            # Add the full session data to request context if needed
            request.session_data = session_data
            
            return f(*args, **kwargs)
        except Exception as e:
            current_app.logger.error(f"Session verification failed: {str(e)}")
            return jsonify({'message': 'Invalid session token'}), 401
    return decorated_function

def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        API_KEY=os.getenv('API_KEY')
        api_key = request.headers.get('API-AUTH-KEY')
        if api_key and api_key == API_KEY:
            return f(*args, **kwargs)
        else:
            return jsonify({'message': 'Invalid or missing API key'}), 401
    return decorated_function

#Test route to verify API key authentication
@auth_bp.route('/test', methods=['GET'])
@require_api_key
def test_auth():
    return jsonify({'message': 'Authentication successful'}), 200

def save_session_response(response_data):
    """
    Save the session response to the database
    """
    from extensions import mongo
    
    session_id = response_data.get('session_id')
    if not session_id:
        current_app.logger.error("No session_id in response data")
        return False
    
    # Create a document to store in MongoDB
    session_document = {
        'session_id': session_id,
        'response': response_data.get('response'),
        'sources': response_data.get('sources', []),
        'success': response_data.get('success', False),
        'timestamp': datetime.datetime.utcnow()
    }
    
    try:
        # Insert the document into a sessions collection
        result = mongo.db.sessions.insert_one(session_document)
        current_app.logger.info(f"Saved session response with ID: {result.inserted_id}")
        return True
    except Exception as e:
        current_app.logger.error(f"Error saving session response: {str(e)}")
        return False