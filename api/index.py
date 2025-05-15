import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from flask import Flask
from flask_cors import CORS
from api_routes.newsroutes import news_bp
from config import Config
app = Flask(__name__)
app.config.from_object(Config)

CORS(app)

from api_routes import auth

app.register_blueprint(auth.auth_bp, url_prefix='/api/auth')
app.register_blueprint(news_bp, url_prefix='/api/news')

if __name__ == '__main__':
    app.run(debug=True,port=5001)
