# In database.py

from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt

db = SQLAlchemy()
bcrypt = Bcrypt()

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='Member')  # Roles: Member, Co-Leader, Leader
    profile_pic_path = db.Column(db.String(200), nullable=True, default='profiles/default.png')

    @property
    def is_active(self): return True

    @property
    def is_authenticated(self): return True

    @property
    def is_anonymous(self): return False

    def get_id(self): return str(self.id)

    def __repr__(self): return f'<User {self.username}>'


class Post(db.Model):
    __tablename__ = 'posts'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=False)
    budget = db.Column(db.Integer, nullable=False, default=0)
    location = db.Column(db.String(100), nullable=False)
    on_ground_members = db.Column(db.Text, nullable=True)
    created_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    author = db.relationship('User', backref=db.backref('posts', lazy=True))
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    media = db.relationship('Media', backref='post', lazy=True, cascade="all, delete-orphan")

    def __repr__(self): return f'<Post {self.title}>'


class Media(db.Model):
    __tablename__ = 'media'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    path = db.Column(db.String(200), nullable=False)

    def __repr__(self): return f'<Media {self.path} for Post ID {self.post_id}>'


class Comment(db.Model):
    __tablename__ = 'comments'
    id = db.Column(db.Integer, primary_key=True)
    post_id = db.Column(db.Integer, db.ForeignKey('posts.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id', ondelete='CASCADE'), nullable=False)
    comment_text = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    author = db.relationship('User', backref=db.backref('comments', lazy=True))
    post = db.relationship('Post', backref=db.backref('comments', lazy=True, cascade="all, delete-orphan"))

    def __repr__(self): return f'<Comment by User ID {self.user_id} on Post ID {self.post_id}>'


class Suggestion(db.Model):
    __tablename__ = 'suggestions'
    id = db.Column(db.Integer, primary_key=True)
    text = db.Column(db.Text, nullable=False)
    # This will hold either the username or the name provided by an anonymous user
    suggester_name = db.Column(db.String(80), nullable=False)
    # This is nullable because anonymous users won't have an ID
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())

    author = db.relationship('User', backref=db.backref('suggestions', lazy=True))

    def __repr__(self):
        return f'<Suggestion by {self.suggester_name}>'


def init_db(app):
    with app.app_context():
        db.create_all()