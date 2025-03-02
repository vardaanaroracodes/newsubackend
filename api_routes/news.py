# api_routes/news.py
from flask import Blueprint, request, jsonify
import requests
from flask_jwt_extended import jwt_required
from config import Config

news_bp = Blueprint('news_bp', __name__)
NEWS_API_KEY = Config.NEWS_API_KEY

@news_bp.route('', methods=['GET'])
@jwt_required(optional=True)
def get_news():
    country = request.args.get('country', 'us')
    category = request.args.get('category', None)
    url = 'https://newsapi.org/v2/top-headlines'
    params = {
        'apiKey': NEWS_API_KEY,
        'country': country,
        'pageSize': 20
    }
    if category:
        params['category'] = category

    response = requests.get(url, params=params)
    if response.status_code == 200:
        return jsonify(response.json())
    else:
        return jsonify({'msg': 'Error fetching news'}), response.status_code
