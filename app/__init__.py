from flask import Flask, render_template, request
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from config import Config

db = SQLAlchemy()
login_manager = LoginManager()

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found_error(error):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': '页面未找到', 'code': 404}, 404
        return render_template('errors/404.html'), 404

    @app.errorhandler(403)
    def forbidden_error(error):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': '访问被拒绝', 'code': 403}, 403
        return render_template('errors/403.html'), 403

    @app.errorhandler(500)
    def internal_error(error):
        db.session.rollback()
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': '服务器内部错误', 'code': 500}, 500
        return render_template('errors/500.html'), 500

    @app.errorhandler(400)
    def bad_request_error(error):
        if request.accept_mimetypes.accept_json and not request.accept_mimetypes.accept_html:
            return {'error': '请求无效', 'code': 400}, 400
        return render_template('errors/404.html'), 400

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
    
    register_error_handlers(app)
    
    return app

from app.models import Admin

@login_manager.user_loader
def load_user(user_id):
    return Admin.query.get(int(user_id))
