import os
import click
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify, session
from database import db, bcrypt, init_db, User, Post, Comment, Media, Suggestion
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from werkzeug.utils import secure_filename
from functools import wraps

# --- App Configuration ---
# Use instance_relative_config=True to tell Flask the instance folder is a special location
app = Flask(__name__, instance_relative_config=True)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass

app.config.from_mapping(
    SECRET_KEY='a_very_secret_key_that_is_long_and_random',
    # Point the database to the instance folder
    SQLALCHEMY_DATABASE_URI=f"sqlite:///{os.path.join(app.instance_path, 'database.db')}",
    SQLALCHEMY_TRACK_MODIFICATIONS=False,
    UPLOAD_FOLDER=os.path.join(app.root_path, 'static', 'uploads')
)

# --- Initialize Extensions ---
db.init_app(app)
bcrypt.init_app(app)

# --- Flask-Login Configuration ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


# --- Custom Decorators for Role-Based Access ---
def role_required(roles):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                return jsonify({'error': 'Authentication required'}), 401
            if current_user.role not in roles:
                return jsonify({'error': 'Forbidden: Insufficient permissions'}), 403
            return f(*args, **kwargs)

        return decorated_function

    return decorator


# --- CLI Command to Initialize DB ---
@app.cli.command('init-db')
def init_db_command():
    """Clear existing data and create new tables."""
    init_db(app)
    click.echo('Initialized the database.')


# --- Page Rendering Routes ---
@app.route('/')
def index():
    latest_posts = Post.query.order_by(Post.timestamp.desc()).limit(3).all()
    # Pass the post and its first media item (if any) to the template
    posts_with_media = []
    for post in latest_posts:
        first_media_path = post.media[0].path if post.media else None
        posts_with_media.append({'post': post, 'media_path': first_media_path})
    return render_template('index.html', posts_with_media=posts_with_media)


@app.route('/about')
def about():
    return render_template('about.html')


@app.route('/activities')
def activities():
    return render_template('activities.html')


@app.route('/donate')
def donate():
    return render_template('donate.html')


@app.route('/suggest', methods=['GET', 'POST'])
def suggest():
    if request.method == 'POST':
        text = request.form.get('suggestion_text')
        if not text:
            flash('Suggestion cannot be empty.', 'danger')
            return redirect(url_for('suggest'))

        suggester_name = "Anonymous"
        user_id = None

        if current_user.is_authenticated:
            suggester_name = current_user.username
            user_id = current_user.id
        else:
            # Ask for a name if user is not logged in
            suggester_name = request.form.get('name') or "Anonymous"

        new_suggestion = Suggestion(
            text=text,
            suggester_name=suggester_name,
            user_id=user_id
        )
        db.session.add(new_suggestion)
        db.session.commit()

        flash('Thank you for your suggestion!', 'success')
        return redirect(url_for('index'))

    return render_template('suggest.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        if User.query.filter_by(username=username).first() or User.query.filter_by(email=email).first():
            flash('Username or email already exists.', 'danger')
            return redirect(url_for('register'))

        hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')

        profile_pic_path = 'uploads/profiles/default.png'  # Default value
        if 'profile_pic' in request.files:
            file = request.files['profile_pic']
            if file.filename != '':
                filename = secure_filename(f"{username}_{file.filename}")
                # Ensure profile upload directory exists
                profile_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'profiles')
                os.makedirs(profile_upload_dir, exist_ok=True)

                file_path = os.path.join(profile_upload_dir, filename)
                file.save(file_path)
                profile_pic_path = os.path.join('uploads', 'profiles', filename)  # Relative path for HTML

        new_user = User(username=username, email=email, password_hash=hashed_password,
                        profile_pic_path=profile_pic_path)
        db.session.add(new_user)
        db.session.commit()
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('login'))
    return render_template('register.html')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.query.filter_by(username=username).first()
        if user and bcrypt.check_password_hash(user.password_hash, password):
            login_user(user, remember=True)
            return redirect(url_for('dashboard'))
        else:
            flash('Login failed. Check username and password.', 'danger')
    return render_template('login.html')


@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    # If the user is a Leader, show the leader dashboard.
    if current_user.role == 'Leader':
        return render_template('leader_dashboard.html')

    # If the user is a Co-Leader, show the co-leader dashboard.
    elif current_user.role == 'Co-Leader':
        return render_template('coleader_dashboard.html')

    # For EVERYONE ELSE (i.e., role is 'Member')...
    else:
        # ...redirect them to the activities page.
        return redirect(url_for('activities'))

    # --- API Routes ---

# GET POSTS
@app.route('/api/posts', methods=['GET'])
def get_posts():
    posts = Post.query.order_by(Post.timestamp.desc()).all()
    total_budget = db.session.query(db.func.sum(Post.budget)).scalar() or 0

    posts_data = [{
        'id': post.id,
        'title': post.title,
        'description': post.description,
        'budget': post.budget,
        'location': post.location,
        'media': [media.path for media in post.media],  # Return list of all media paths
        'on_ground_members': post.on_ground_members,
        'author': post.author.username,
        'timestamp': post.timestamp.strftime('%B %d, %Y')
    } for post in posts]

    return jsonify({'posts': posts_data, 'total_budget': total_budget})


# CREATE POST
@app.route('/api/create_post', methods=['POST'])
@login_required
@role_required(['Leader', 'Co-Leader'])
def create_post():
    data = request.form
    new_post = Post(
        title=data['title'],
        description=data['description'],
        budget=int(data['budget']),
        location=data['location'],
        on_ground_members=data['on_ground_members'],
        created_by=current_user.id
    )
    # Add and flush to get the post ID for filenames
    db.session.add(new_post)
    db.session.flush()

    # Use getlist to handle multiple files
    files = request.files.getlist('media')
    if files:
        post_upload_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'posts')
        os.makedirs(post_upload_dir, exist_ok=True)

        for file in files:
            if file and file.filename != '':
                # Add post_id to filename to ensure uniqueness
                filename = secure_filename(f"{new_post.id}_{file.filename}")
                upload_path = os.path.join(post_upload_dir, filename)
                file.save(upload_path)
                media_path = os.path.join('uploads', 'posts', filename)

                # Create a new Media object and link it to the post
                new_media = Media(post_id=new_post.id, path=media_path)
                db.session.add(new_media)

    db.session.commit()  # Commit post and all media objects together
    return jsonify({'message': 'Post created successfully'}), 201


# DELETE POST
@app.route('/api/delete_post/<int:post_id>', methods=['DELETE'])
@login_required
@role_required(['Leader'])
def delete_post(post_id):
    post = Post.query.get_or_404(post_id)
    # Loop through all associated media and delete the files
    for media_item in post.media:
        try:
            os.remove(os.path.join(app.root_path, 'static', media_item.path))
        except OSError as e:
            # Log the error but continue, so the post still gets deleted
            print(f"Error deleting file {media_item.path}: {e}")
            pass

    # Deleting the post will also delete associated media DB records due to cascade
    db.session.delete(post)
    db.session.commit()
    return jsonify({'message': 'Post deleted successfully'}), 200


# GET/POST COMMENTS
@app.route('/api/posts/<int:post_id>/comments', methods=['GET', 'POST'])
@login_required
def handle_comments(post_id):
    if request.method == 'POST':
        comment_text = request.json.get('comment_text')
        if not comment_text:
            return jsonify({'error': 'Comment text cannot be empty'}), 400

        new_comment = Comment(post_id=post_id, user_id=current_user.id, comment_text=comment_text)
        db.session.add(new_comment)
        db.session.commit()

        comment_data = {
            'id': new_comment.id,
            'comment_text': new_comment.comment_text,
            'author': new_comment.author.username,
            'profile_pic': url_for('static',
                                   filename=new_comment.author.profile_pic_path or 'uploads/profiles/default.png'),
            'timestamp': new_comment.timestamp.strftime('%b %d, %H:%M')
        }
        return jsonify(comment_data), 201
    else:  # GET
        comments = Comment.query.filter_by(post_id=post_id).order_by(Comment.timestamp.asc()).all()
        comments_data = [{
            'id': comment.id,
            'comment_text': comment.comment_text,
            'author': comment.author.username,
            'profile_pic': url_for('static',
                                   filename=comment.author.profile_pic_path or 'uploads/profiles/default.png'),
            'timestamp': comment.timestamp.strftime('%b %d, %H:%M')
        } for comment in comments]
        return jsonify(comments_data)

# --- Suggestions API Route ---
@app.route('/api/suggestions', methods=['GET'])
@login_required
@role_required(['Leader', 'Co-Leader'])
def get_suggestions():
    suggestions = Suggestion.query.order_by(Suggestion.timestamp.desc()).all()
    suggestions_data = [{
        'id': s.id,
        'text': s.text,
        'suggester_name': s.suggester_name,
        'timestamp': s.timestamp.strftime('%B %d, %Y %H:%M')
    } for s in suggestions]
    return jsonify(suggestions_data)


# --- Leader-Only API Routes ---
@app.route('/api/users', methods=['GET'])
@login_required
@role_required(['Leader'])
def get_users():
    users = User.query.all()
    users_data = [{
        'id': user.id,
        'username': user.username,
        'email': user.email,
        'role': user.role,
        'profile_pic_path': url_for('static', filename=user.profile_pic_path or 'uploads/profiles/default.png')
    } for user in users]
    return jsonify(users_data)


@app.route('/api/promote_user/<int:user_id>', methods=['POST'])
@login_required
@role_required(['Leader'])
def promote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'Member':
        user.role = 'Co-Leader'
        db.session.commit()
        return jsonify({'message': f'User {user.username} promoted to Co-Leader'}), 200
    return jsonify({'error': 'User is not a Member'}), 400


@app.route('/api/demote_user/<int:user_id>', methods=['POST'])
@login_required
@role_required(['Leader'])
def demote_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.role == 'Co-Leader':
        user.role = 'Member'
        db.session.commit()
        return jsonify({'message': f'User {user.username} demoted to Member'}), 200
    return jsonify({'error': 'User is not a Co-Leader'}), 400


@app.route('/api/delete_user/<int:user_id>', methods=['DELETE'])
@login_required
@role_required(['Leader'])
def delete_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        return jsonify({'error': 'You cannot delete yourself.'}), 403
    if user.role == 'Leader':
        return jsonify({'error': 'Cannot delete a Leader account'}), 403
    db.session.delete(user)
    db.session.commit()
    return jsonify({'message': 'User deleted successfully'}), 200