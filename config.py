import os
from dotenv import load_dotenv

load_dotenv() 

#config will get the values from the env file or will use the default values, so don't get confused hehe.
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'hi_stalkers')
    MONGO_URI = os.getenv('MONGO_URI')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY')
    NEWS_API_KEY = os.getenv('NEWS_API_KEY')
    GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID')
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET')
    BRAVE_API_KEY = os.environ.get('BRAVE_API_KEY'),
    GOOGLE_API_KEY = os.environ.get('GOOGLE_API_KEY'),
    SERPER_API_KEY = os.environ.get('SERPER_API_KEY'),
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO'),
    API_KEY = os.environ.get('API_KEY'),
    DEBUG = os.environ.get('FLASK_DEBUG', 'False').lower() in ('true', '1', 't')