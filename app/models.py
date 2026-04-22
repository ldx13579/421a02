from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app import db

class Admin(UserMixin, db.Model):
    __tablename__ = 'admins'
    
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    last_login = db.Column(db.DateTime)
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    def __repr__(self):
        return f'<Admin {self.username}>'

class Poll(db.Model):
    __tablename__ = 'polls'
    
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    description = db.Column(db.Text)
    is_active = db.Column(db.Boolean, default=False)
    is_results_public = db.Column(db.Boolean, default=True)
    vote_type = db.Column(db.String(20), default='single')
    max_choices = db.Column(db.Integer, default=1)
    start_time = db.Column(db.DateTime, default=datetime.utcnow)
    end_time = db.Column(db.DateTime)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    options = db.relationship('Option', backref='poll', lazy='dynamic', cascade='all, delete-orphan')
    vote_records = db.relationship('VoteRecord', backref='poll', lazy='dynamic', cascade='all, delete-orphan')
    
    def is_voting_open(self):
        now = datetime.utcnow()
        if not self.is_active:
            return False
        if self.end_time and now > self.end_time:
            return False
        if self.start_time and now < self.start_time:
            return False
        return True
    
    def get_total_votes(self):
        return VoteRecord.query.filter_by(poll_id=self.id).count()
    
    def __repr__(self):
        return f'<Poll {self.title}>'

class Option(db.Model):
    __tablename__ = 'options'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id'), nullable=False, index=True)
    text = db.Column(db.String(200), nullable=False)
    order = db.Column(db.Integer, default=0)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def get_vote_count(self):
        return VoteRecord.query.filter_by(option_id=self.id).count()
    
    def get_vote_percentage(self):
        total = self.poll.get_total_votes()
        if total == 0:
            return 0.0
        return round((self.get_vote_count() / total) * 100, 1)
    
    def __repr__(self):
        return f'<Option {self.text}>'

class VoteRecord(db.Model):
    __tablename__ = 'vote_records'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id'), nullable=False, index=True)
    option_id = db.Column(db.Integer, db.ForeignKey('options.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False, index=True)
    user_agent = db.Column(db.String(500))
    session_id = db.Column(db.String(100), index=True)
    voted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.Index('idx_poll_ip', 'poll_id', 'ip_address'),
    )
    
    def __repr__(self):
        return f'<VoteRecord poll={self.poll_id} option={self.option_id}>'

class VoteSession(db.Model):
    __tablename__ = 'vote_sessions'
    
    id = db.Column(db.Integer, primary_key=True)
    poll_id = db.Column(db.Integer, db.ForeignKey('polls.id'), nullable=False, index=True)
    ip_address = db.Column(db.String(45), nullable=False)
    session_id = db.Column(db.String(100), nullable=False)
    voted_at = db.Column(db.DateTime, default=datetime.utcnow, index=True)
    
    __table_args__ = (
        db.UniqueConstraint('poll_id', 'ip_address', 'session_id', name='uq_vote_session'),
        db.Index('idx_vote_session_poll_ip', 'poll_id', 'ip_address'),
    )
    
    def __repr__(self):
        return f'<VoteSession poll={self.poll_id}>'

class RateLimit(db.Model):
    __tablename__ = 'rate_limits'
    
    id = db.Column(db.Integer, primary_key=True)
    key = db.Column(db.String(100), nullable=False, unique=True, index=True)
    count = db.Column(db.Integer, default=0)
    reset_at = db.Column(db.DateTime, nullable=False, index=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<RateLimit key={self.key} count={self.count}>'
