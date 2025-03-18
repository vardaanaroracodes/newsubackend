from flask import Blueprint, request, jsonify,current_app
from functools import wraps
from dotenv import load_dotenv
import os

load_dotenv()
auth_bp = Blueprint('auth_bp', __name__)


def require_api_key(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        API_KEY=os.getenv('API_KEY')
        print(API_KEY)
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