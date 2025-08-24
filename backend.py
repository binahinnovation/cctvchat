from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from flask import request, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
from flask import send_from_directory
from datetime import timedelta

app = Flask(__name__)
CORS(app)

# Configurations
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///cctv_chat.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'dev_secret_key')
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=24)  # Session timeout

db = SQLAlchemy(app)

bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

# Update User model to inherit from UserMixin
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    username = db.Column(db.String(64), unique=True, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())
    last_login = db.Column(db.DateTime)
    is_active = db.Column(db.Boolean, default=True)
    videos = db.relationship('Video', backref='user', lazy=True)
    chats = db.relationship('ChatHistory', backref='user', lazy=True)

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# User registration endpoint
@app.route('/api/register', methods=['POST'])
def register():
    data = request.json
    email = data.get('email')
    username = data.get('username')
    password = data.get('password')
    if not email or not username or not password:
        return jsonify({'error': 'Missing required fields'}), 400
    if User.query.filter((User.email == email) | (User.username == username)).first():
        return jsonify({'error': 'User already exists'}), 409
    password_hash = bcrypt.generate_password_hash(password).decode('utf-8')
    user = User(email=email, username=username, password_hash=password_hash)
    db.session.add(user)
    db.session.commit()
    return jsonify({'message': 'User registered successfully'}), 201

# User login endpoint
@app.route('/api/login', methods=['POST'])
def login():
    data = request.json
    email = data.get('email')
    password = data.get('password')
    user = User.query.filter_by(email=email).first()
    if user and bcrypt.check_password_hash(user.password_hash, password):
        login_user(user)
        response = jsonify({'message': 'Login successful', 'user_id': user.id, 'username': user.username})
        return response, 200
    return jsonify({'error': 'Invalid credentials'}), 401

# Logout endpoint
@app.route('/api/logout', methods=['POST'])
@login_required
def logout():
    logout_user()
    return jsonify({'message': 'Logged out successfully'}), 200

# Video model
class Video(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    video_name = db.Column(db.String(256))
    video_type = db.Column(db.String(32)) # upload/camera/url
    file_path_or_url = db.Column(db.String(512))
    upload_date = db.Column(db.DateTime, server_default=db.func.now())
    file_size = db.Column(db.Integer)
    duration = db.Column(db.Integer)
    thumbnail_path = db.Column(db.String(512))
    is_processed = db.Column(db.Boolean, default=False)
    is_favorite = db.Column(db.Boolean, default=False)
    chats = db.relationship('ChatHistory', backref='video', lazy=True)

# Chat history model
class ChatHistory(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    video_id = db.Column(db.Integer, db.ForeignKey('video.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    question = db.Column(db.Text, nullable=False)
    answer = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, server_default=db.func.now())
    model_used = db.Column(db.String(64))

UPLOAD_FOLDER = os.path.join(os.getcwd(), 'upload')
ALLOWED_EXTENSIONS = {'mp4', 'avi', 'mov', 'mkv', 'flv', 'wmv'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# Video upload endpoint (file)
@app.route('/api/upload_video', methods=['POST'])
@login_required
def upload_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)
        video = Video(
            user_id=current_user.id,
            video_name=filename,
            video_type='upload',
            file_path_or_url=filepath,
            file_size=os.path.getsize(filepath),
            is_processed=False
        )
        db.session.add(video)
        db.session.commit()
        return jsonify({'message': 'Video uploaded successfully', 'video_id': video.id}), 201
    return jsonify({'error': 'Invalid file type'}), 400

# Video upload endpoint (URL or camera)
@app.route('/api/add_video', methods=['POST'])
@login_required
def add_video():
    data = request.json
    video_name = data.get('video_name')
    video_type = data.get('video_type')  # 'url' or 'camera'
    file_path_or_url = data.get('file_path_or_url')
    if not video_name or not video_type or not file_path_or_url:
        return jsonify({'error': 'Missing required fields'}), 400
    video = Video(
        user_id=current_user.id,
        video_name=video_name,
        video_type=video_type,
        file_path_or_url=file_path_or_url,
        is_processed=False
    )
    db.session.add(video)
    db.session.commit()
    return jsonify({'message': 'Video added successfully', 'video_id': video.id}), 201

# Get all videos for current user with search and filter
@app.route('/api/videos', methods=['GET'])
@login_required
def get_videos():
    videos = Video.query.filter_by(user_id=current_user.id)
    
    # Search by video name
    search = request.args.get('search', '').strip()
    if search:
        videos = videos.filter(Video.video_name.ilike(f'%{search}%'))
    
    # Filter by video type
    video_type = request.args.get('type', '').strip()
    if video_type:
        videos = videos.filter_by(video_type=video_type)
    
    # Filter by favorite status
    favorite = request.args.get('favorite', '').strip()
    if favorite.lower() == 'true':
        videos = videos.filter_by(is_favorite=True)
    elif favorite.lower() == 'false':
        videos = videos.filter_by(is_favorite=False)
    
    # Sort by favorite status and upload date
    videos = videos.order_by(Video.is_favorite.desc(), Video.upload_date.desc())
    
    # Pagination
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)
    per_page = min(per_page, 50)  # Limit max items per page
    
    pagination = videos.paginate(page=page, per_page=per_page, error_out=False)
    
    video_list = []
    for video in pagination.items:
        video_data = {
            'id': video.id,
            'video_name': video.video_name,
            'video_type': video.video_type,
            'file_path_or_url': video.file_path_or_url,
            'upload_date': video.upload_date.strftime('%Y-%m-%d %H:%M:%S'),
            'file_size': video.file_size,
            'duration': video.duration,
            'thumbnail_path': video.thumbnail_path,
            'is_processed': video.is_processed,
            'is_favorite': video.is_favorite
        }
        video_list.append(video_data)
    
    return jsonify({
        'videos': video_list,
        'pagination': {
            'page': page,
            'per_page': per_page,
            'total': pagination.total,
            'pages': pagination.pages,
            'has_next': pagination.has_next,
            'has_prev': pagination.has_prev
        }
    })

# Serve uploaded video files
@app.route('/api/video_file/<filename>')
def get_video_file(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

# Save a chat/question for a video
@app.route('/api/chat', methods=['POST'])
@login_required
def save_chat():
    data = request.json
    video_id = data.get('video_id')
    question = data.get('question')
    answer = data.get('answer')
    model_used = data.get('model_used')
    if not video_id or not question or not answer:
        return jsonify({'error': 'Missing required fields'}), 400
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    chat = ChatHistory(
        video_id=video_id,
        user_id=current_user.id,
        question=question,
        answer=answer,
        model_used=model_used
    )
    db.session.add(chat)
    db.session.commit()
    return jsonify({'message': 'Chat saved successfully', 'chat_id': chat.id}), 201

# Get chat history for a video
@app.route('/api/chat_history/<int:video_id>', methods=['GET'])
@login_required
def get_chat_history(video_id):
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    chats = ChatHistory.query.filter_by(video_id=video_id, user_id=current_user.id).order_by(ChatHistory.timestamp.asc()).all()
    chat_list = [
        {
            'id': c.id,
            'question': c.question,
            'answer': c.answer,
            'timestamp': c.timestamp,
            'model_used': c.model_used
        } for c in chats
    ]
    return jsonify({'chats': chat_list}), 200

# Delete a specific chat Q&A pair
@app.route('/api/chat/<int:chat_id>', methods=['DELETE'])
@login_required
def delete_chat(chat_id):
    chat = ChatHistory.query.filter_by(id=chat_id, user_id=current_user.id).first()
    if not chat:
        return jsonify({'error': 'Chat not found or not owned by user'}), 404
    db.session.delete(chat)
    db.session.commit()
    return jsonify({'message': 'Chat deleted successfully'}), 200

# Delete a video
@app.route('/api/video/<int:video_id>', methods=['DELETE'])
@login_required
def delete_video(video_id):
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    db.session.delete(video)
    db.session.commit()
    return jsonify({'message': 'Video deleted successfully'}), 200

# Rename a video
@app.route('/api/video/<int:video_id>/rename', methods=['POST'])
@login_required
def rename_video(video_id):
    data = request.json
    new_name = data.get('new_name')  # Changed from 'video_name' to 'new_name'
    if not new_name:
        return jsonify({'error': 'New video name is required'}), 400
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    video.video_name = new_name
    db.session.commit()
    return jsonify({'message': 'Video name updated successfully'}), 200

# Toggle favorite status for a video
@app.route('/api/video/<int:video_id>/favorite', methods=['POST'])
@login_required
def toggle_favorite(video_id):
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    video.is_favorite = not video.is_favorite
    db.session.commit()
    return jsonify({'message': 'Favorite status updated', 'is_favorite': video.is_favorite}), 200

# Get current user profile
@app.route('/api/profile', methods=['GET'])
@login_required
def get_profile():
    user = current_user
    return jsonify({
        'id': user.id,
        'email': user.email,
        'username': user.username,
        'created_at': user.created_at,
        'last_login': user.last_login,
        'is_active': user.is_active
    }), 200

# Update current user profile (username only for now)
@app.route('/api/profile', methods=['POST'])
@login_required
def update_profile():
    data = request.get_json()
    username = data.get('username')
    
    if not username:
        return jsonify({'error': 'Username is required'}), 400
    
    # Check if username is already taken by another user
    existing_user = User.query.filter_by(username=username).first()
    if existing_user and existing_user.id != current_user.id:
        return jsonify({'error': 'Username already taken'}), 400
    
    current_user.username = username
    db.session.commit()
    return jsonify({'message': 'Profile updated successfully'}), 200

# Change password endpoint
@app.route('/api/profile/password', methods=['POST'])
@login_required
def change_password():
    data = request.get_json()
    current_password = data.get('current_password')
    new_password = data.get('new_password')
    
    if not current_password or not new_password:
        return jsonify({'error': 'Current and new password are required'}), 400
    
    # Verify current password
    if not bcrypt.check_password_hash(current_user.password_hash, current_password):
        return jsonify({'error': 'Current password is incorrect'}), 400
    
    # Hash new password
    new_password_hash = bcrypt.generate_password_hash(new_password).decode('utf-8')
    current_user.password_hash = new_password_hash
    db.session.commit()
    
    return jsonify({'message': 'Password changed successfully'}), 200

# Analyze video endpoint
@app.route('/api/analyze_video', methods=['POST'])
@login_required
def analyze_video():
    data = request.json
    video_id = data.get('video_id')
    question = data.get('question')
    
    if not video_id or not question:
        return jsonify({'error': 'Video ID and question are required'}), 400
    
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    
    # For now, return a placeholder response
    # In a real implementation, this would call the AI model
    answer = f"Analysis of video {video.video_name}: {question} - This is a placeholder response. The actual AI analysis would be implemented here."
    
    return jsonify({'answer': answer}), 200

# Add chat endpoint
@app.route('/api/add_chat', methods=['POST'])
@login_required
def add_chat():
    data = request.json
    video_id = data.get('video_id')
    question = data.get('question')
    answer = data.get('answer')
    
    if not video_id or not question or not answer:
        return jsonify({'error': 'Video ID, question, and answer are required'}), 400
    
    video = Video.query.filter_by(id=video_id, user_id=current_user.id).first()
    if not video:
        return jsonify({'error': 'Video not found or not owned by user'}), 404
    
    chat = ChatHistory(
        video_id=video_id,
        user_id=current_user.id,
        question=question,
        answer=answer
    )
    db.session.add(chat)
    db.session.commit()
    
    return jsonify({'message': 'Chat saved successfully', 'chat_id': chat.id}), 200

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True) 