from app import create_app, db
from app.models import Admin, Poll, Option, VoteRecord

app = create_app()

@app.shell_context_processor
def make_shell_context():
    return {'db': db, 'Admin': Admin, 'Poll': Poll, 'Option': Option, 'VoteRecord': VoteRecord}

@app.cli.command()
def init_db():
    db.create_all()
    print('Database initialized!')

@app.cli.command()
def create_admin():
    from app import create_app
    from config import Config
    from werkzeug.security import generate_password_hash
    
    app = create_app()
    with app.app_context():
        admin = Admin.query.first()
        if not admin:
            admin = Admin(
                username=Config.ADMIN_USERNAME,
                password_hash=generate_password_hash(Config.ADMIN_PASSWORD)
            )
            db.session.add(admin)
            db.session.commit()
            print(f'Admin user created: {Config.ADMIN_USERNAME}')
        else:
            print('Admin user already exists.')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        from config import Config
        from werkzeug.security import generate_password_hash
        
        admin = Admin.query.first()
        if not admin:
            admin = Admin(
                username=Config.ADMIN_USERNAME,
                password_hash=generate_password_hash(Config.ADMIN_PASSWORD)
            )
            db.session.add(admin)
            db.session.commit()
            print(f'Admin user created: {Config.ADMIN_USERNAME}')
    
    app.run(debug=True, host='0.0.0.0', port=5000)
