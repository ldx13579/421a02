import os
import sys

os.environ['PYTHONIOENCODING'] = 'utf-8'

import traceback
import socket
from datetime import datetime

def print_header(title):
    print("\n" + "=" * 60)
    print("  " + title)
    print("=" * 60)

def print_error(message, exception=None):
    print("\n[错误] " + message)
    if exception:
        print("\n详细错误信息:")
        print("-" * 60)
        traceback.print_exc()
        print("-" * 60)

def check_port(host, port):
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except Exception as e:
        print_error("检查端口时出错", e)
        return False

def find_available_port(start_port=5000, max_attempts=10):
    for port in range(start_port, start_port + max_attempts):
        if not check_port('127.0.0.1', port):
            return port
    return None

def check_dependencies():
    print_header("检查依赖项")
    
    required_modules = {
        'flask': 'Flask',
        'flask_sqlalchemy': 'Flask-SQLAlchemy',
        'flask_login': 'Flask-Login',
        'PIL': 'Pillow',
        'dotenv': 'python-dotenv',
        'werkzeug': 'Werkzeug'
    }
    
    all_ok = True
    for module_name, package_name in required_modules.items():
        try:
            __import__(module_name)
            print("  [OK] " + package_name + " 已安装")
        except ImportError:
            print("  [缺失] " + package_name + " 未安装")
            all_ok = False
    
    if not all_ok:
        print("\n请运行以下命令安装缺失的依赖:")
        print("  pip install -r requirements.txt")
        return False
    
    return True

def init_database(app, db):
    print_header("初始化数据库")
    
    try:
        with app.app_context():
            db.create_all()
            print("  [OK] 数据库表创建成功")
            
            from config import Config
            from werkzeug.security import generate_password_hash
            from app.models import Admin
            
            admin = Admin.query.first()
            if not admin:
                admin = Admin(
                    username=Config.ADMIN_USERNAME,
                    password_hash=generate_password_hash(Config.ADMIN_PASSWORD)
                )
                db.session.add(admin)
                db.session.commit()
                print("  [OK] 管理员账户创建成功")
                print("       用户名: " + Config.ADMIN_USERNAME)
                print("       密码: " + Config.ADMIN_PASSWORD)
            else:
                print("  [信息] 管理员账户已存在")
        
        return True
        
    except Exception as e:
        print_error("数据库初始化失败", e)
        return False

def create_flask_app():
    from app import create_app, db
    from app.models import Admin, Poll, Option, VoteRecord, VoteSession, RateLimit
    
    app = create_app()
    
    @app.shell_context_processor
    def make_shell_context():
        return {
            'db': db, 
            'Admin': Admin, 
            'Poll': Poll, 
            'Option': Option, 
            'VoteRecord': VoteRecord,
            'VoteSession': VoteSession,
            'RateLimit': RateLimit
        }
    
    return app, db

def main():
    start_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    print("\n" + "*" * 60)
    print("*           在线投票管理系统 - 启动程序                     *")
    print("*           启动时间: " + start_time + "           *")
    print("*" * 60)
    
    if not check_dependencies():
        sys.exit(1)
    
    print_header("导入应用模块")
    try:
        app, db = create_flask_app()
        print("  [OK] 应用模块导入成功")
    except Exception as e:
        print_error("应用模块导入失败", e)
        sys.exit(1)
    
    print_header("创建Flask应用")
    try:
        print("  [OK] Flask应用创建成功")
        db_path = app.config.get('SQLALCHEMY_DATABASE_URI', 'unknown')
        print("  [信息] 数据库路径: " + str(db_path))
    except Exception as e:
        print_error("Flask应用创建失败", e)
        sys.exit(1)
    
    if not init_database(app, db):
        sys.exit(1)
    
    print_header("检查端口")
    host = '0.0.0.0'
    port = 5000
    
    if check_port('127.0.0.1', port):
        print("  [警告] 端口 " + str(port) + " 已被占用，正在寻找可用端口...")
        available_port = find_available_port(port + 1)
        if available_port:
            port = available_port
            print("  [OK] 找到可用端口: " + str(port))
        else:
            print_error("无法找到可用端口")
            sys.exit(1)
    else:
        print("  [OK] 端口 " + str(port) + " 可用")
    
    print_header("启动服务器")
    print("  [信息] 正在启动服务器...")
    print("  [信息] 本地访问地址: http://127.0.0.1:" + str(port))
    print("  [信息] 管理后台地址: http://127.0.0.1:" + str(port) + "/admin/login")
    print("  [信息] 调试模式: 开启")
    print("  [信息] 监听地址: " + host + ":" + str(port))
    print("\n" + "=" * 60)
    print("  服务器已启动，按 Ctrl+C 停止")
    print("=" * 60 + "\n")
    
    try:
        app.run(debug=True, host=host, port=port, use_reloader=True)
    except KeyboardInterrupt:
        print("\n\n" + "=" * 60)
        print("  服务器已停止")
        print("=" * 60 + "\n")
    except Exception as e:
        print_error("服务器运行时出错", e)
        sys.exit(1)

if __name__ == '__main__':
    main()
