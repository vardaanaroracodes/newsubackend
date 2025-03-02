# api_routes/auth.py
from flask import Blueprint, request, jsonify, redirect, url_for, make_response
from flask_jwt_extended import create_access_token
from werkzeug.security import generate_password_hash, check_password_hash
from flask_dance.contrib.google import make_google_blueprint, google
from extensions import mongo  # Import mongo from extensions
from config import Config

auth_bp = Blueprint('auth_bp', __name__)

# Traditional Email/Password Registration
@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'msg': 'Missing email or password'}), 400

    existing_user = mongo.db.users.find_one({"email": data['email']})
    if existing_user:
        return jsonify({'msg': 'User already exists'}), 400

    hashed_password = generate_password_hash(data['password'])
    user_data = {"email": data['email'], "password_hash": hashed_password}
    result = mongo.db.users.insert_one(user_data)

    token = create_access_token(identity=str(result.inserted_id))
    response = make_response(jsonify({'msg': 'User registered successfully'}), 201)
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite='Lax', max_age=60*60*24)
    return response

# Traditional Email/Password Login
@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({'msg': 'Missing email or password'}), 400

    user = mongo.db.users.find_one({"email": data['email']})
    if user and check_password_hash(user['password_hash'], data['password']):
        token = create_access_token(identity=str(user['_id']))
        response = make_response(jsonify({'msg': 'Login successful!'}), 200)
        response.set_cookie("access_token", token, httponly=True, secure=True, samesite='Lax', max_age=60*60*24)

        return response
    else:
        return jsonify({'msg': 'Invalid credentials'}), 401



@auth_bp.route('/google')
def google_login():
    
    if not google.authorized:
        return redirect(url_for("google.login"))
    resp = google.get("/oauth2/v2/userinfo")
    if not resp.ok:
        return jsonify({"msg": "Failed to fetch user info from Google"}), 400

    user_info = resp.json()
    email = user_info.get("email")
    if not email:  # Check if email is present
        return jsonify({"msg": "Email not found in user info"}), 400
    print(email)
    user = mongo.db.users.find_one({"email": email})
    if not user:
        user_data = {"email": email, "password_hash": generate_password_hash("oauth-no-password")}
        result = mongo.db.users.insert_one(user_data)
        user_id = str(result.inserted_id)
    else:
        user_id = str(user['_id'])
    
    token = create_access_token(identity=user_id)
    print(token)
    # Redirect to your production frontend URL (update accordingly)
    response = make_response(redirect("https://your-production-frontend-url.com/dashboard"))
    response.set_cookie("access_token", token, httponly=True, secure=True, samesite='Lax', max_age=60*60*24)
    return response

@auth_bp.route('/google/authorized')
def google_authorized():
    if not google.authorized:
        return jsonify({"msg": "Authentication failed"}), 401
    return redirect(url_for('auth_bp.google_login'))