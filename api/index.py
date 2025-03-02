import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'
from flask import Flask
from flask_cors import CORS
from config import Config
from extensions import mongo, jwt
from flask_dance.contrib.google import make_google_blueprint
app = Flask(__name__)
app.config.from_object(Config)

google_bp = make_google_blueprint(
    scope=[
        'openid',
        "https://www.googleapis.com/auth/userinfo.profile",
        "https://www.googleapis.com/auth/userinfo.email",
    ],
    redirect_url='/login/google/authorized'
)
app.register_blueprint(google_bp, url_prefix="/login")

mongo.init_app(app)
jwt.init_app(app)

# Enable CORS
CORS(app)

# Register Blueprints
from api_routes import auth, news

app.register_blueprint(auth.auth_bp, url_prefix='/api/auth')
app.register_blueprint(news.news_bp, url_prefix='/api/news')

if __name__ == '__main__':
    app.run(debug=True)
