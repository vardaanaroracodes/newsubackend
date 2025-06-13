import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
from flask_cors import CORS
from api_routes.newsroutes import news_bp
from api_routes.searchroutes import search_bp
from config import Config
from extensions import mongo, jwt

app = Flask(__name__)
app.config.from_object(Config)

# Initialize MongoDB
mongo.init_app(app)

# Initialize JWT
jwt.init_app(app)

CORS(app, supports_credentials=True, allow_headers=["Content-Type", "Auth-Session-Id"])
from api_routes import auth

app.register_blueprint(auth.auth_bp, url_prefix='/api/auth')
app.register_blueprint(news_bp, url_prefix='/api/news')
app.register_blueprint(search_bp, url_prefix='/api/search')

if __name__ == '__main__':
    app.run(debug=True,port=5001)
