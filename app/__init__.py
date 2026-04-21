from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)
    
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'admin.login'
    login_manager.login_message = '请先登录管理员账户'
    
    from app.routes.main import main
    from app.routes.admin import admin
    from app.routes.api import api
    
    app.register_blueprint(main)
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(api, url_prefix='/api')
    
    return app

from app.models import Admin

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))
