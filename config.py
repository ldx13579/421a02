import os
from datetime import timedelta

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'voting-system-secret-key-2024'
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///' + os.path.join(os.path.abspath(os.path.dirname(__file__)), 'voting.db')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    PERMANENT_SESSION_LIFETIME = timedelta(hours=24)
    SESSION_TYPE = 'filesystem'
    
    ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME') or 'admin'
    ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD') or 'admin123'
    
    VOTE_IP_LIMIT_HOURS = int(os.environ.get('VOTE_IP_LIMIT_HOURS') or 24)
    
    CAPTCHA_LENGTH = 4
    CAPTCHA_WIDTH = 120
    CAPTCHA_HEIGHT = 40
