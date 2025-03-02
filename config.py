import os
from dotenv import load_dotenv

load_dotenv() 

#config will get the values from the env file or will use the default values, so don't get confused hehe.
class Config:
    SECRET_KEY = os.getenv('SECRET_KEY', 'hi_stalkers')
    MONGO_URI = os.getenv('MONGO_URI', 'nothing')
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'hi_stalkers')
    NEWS_API_KEY = os.getenv('NEWS_API_KEY', 'hi_stalkers')
    GOOGLE_OAUTH_CLIENT_ID = os.getenv('GOOGLE_OAUTH_CLIENT_ID', 'hi_stalkers')
    GOOGLE_OAUTH_CLIENT_SECRET = os.getenv('GOOGLE_OAUTH_CLIENT_SECRET', 'hi_stalkers')
