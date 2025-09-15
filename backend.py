from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
import os
from flask import request, jsonify
from flask_bcrypt import Bcrypt
from flask_login import LoginManager, login_user, logout_user, login_required, current_user, UserMixin
from werkzeug.utils import secure_filename
from flask import send_from_directory
from datetime import timedelta, datetime
from openai import OpenAI
from dotenv import load_dotenv
import secrets
import qrcode
import io
import base64

load_dotenv()  # Load environment variables from .env if present

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
    whatsapp_number = db.Column(db.String(64), nullable=True, unique=True)
    whatsapp_linked_at = db.Column(db.DateTime, nullable=True)

    def get_id(self):
        return str(self.id)

@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

# Root endpoint for health checks
@app.route('/')
def root():
    return jsonify({'message': 'CCTV Chat Backend is running!', 'status': 'healthy'}), 200

# Debug endpoint to check environment variables
@app.route('/debug/env')
def debug_env():
    """Debug endpoint to check environment variables"""
    env_vars = {}
    all_env_vars = {}
    
    # Get all environment variables for debugging
    for key, value in os.environ.items():
        all_env_vars[key] = 'SET' if value else 'NOT SET'
        if any(prefix in key.upper() for prefix in ['TWILIO', 'DASHSCOPE', 'SECRET', 'DATABASE']):
            env_vars[key] = 'SET' if value else 'NOT SET'
    
    return jsonify({
        'message': 'Environment variables debug - Redeploy Test',
        'target_variables': env_vars,
        'all_variables': all_env_vars
    }), 200

# Simple test endpoint
@app.route('/test')
def test():
    """Simple test endpoint"""
    return jsonify({'message': 'Test endpoint working', 'timestamp': str(datetime.utcnow())}), 200

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

class WhatsAppLinkToken(db.Model):
    token = db.Column(db.String(16), primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    expires_at = db.Column(db.DateTime, nullable=False)
    used = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, server_default=db.func.now())

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
        'is_active': user.is_active,
        'whatsapp_number': user.whatsapp_number,
        'whatsapp_linked_at': user.whatsapp_linked_at.isoformat() if user.whatsapp_linked_at else None
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

    try:
        # Build an accessible video URL
        if video.video_type == 'upload' and video.file_path_or_url:
            filename = os.path.basename(video.file_path_or_url)
            # Use APP_BASE_URL if available, otherwise construct from request
            base_url = os.environ.get('APP_BASE_URL', request.host_url.rstrip('/'))
            video_url = f"{base_url}/api/video_file/{filename}"
        else:
            video_url = video.file_path_or_url

        print(f"Video URL constructed: {video_url}")  # Debug logging

        # Initialize DashScope OpenAI-compatible client
        dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
        if not dashscope_key:
            print("DASHSCOPE_API_KEY not found in environment variables")
            return jsonify({'error': 'DASHSCOPE_API_KEY not configured on backend'}), 500

        print(f"Using DashScope API key: {dashscope_key[:10]}...")  # Debug logging

        client = OpenAI(
            api_key=dashscope_key,
            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
        )

        # Compose request to Qwen-VL (OpenAI-compatible schema)
        messages = [
            {
                "role": "system",
                "content": [
                    {"type": "text", "text": "You are Qwen-VL, an expert video analysis assistant. Answer concisely and factually based on the provided video."}
                ],
            },
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": question},
                    {"type": "video_url", "video_url": {"url": video_url}},
                ],
            },
        ]

        print(f"Sending request to Qwen-VL with video URL: {video_url}")  # Debug logging

        completion = client.chat.completions.create(
            model="qwen-vl-max",
            messages=messages,
            temperature=0.2,
        )

        answer = completion.choices[0].message.content if completion and completion.choices else "No answer generated."
        print(f"Received answer from Qwen-VL: {answer[:100]}...")  # Debug logging
        return jsonify({'answer': answer}), 200

    except Exception as e:
        print(f"Error in analyze_video: {str(e)}")  # Debug logging
        import traceback
        traceback.print_exc()  # Print full stack trace
        return jsonify({'error': f'AI analysis failed: {str(e)}'}), 500

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

# WhatsApp linking endpoints
@app.route('/api/whatsapp/link-token', methods=['POST'])
@login_required
def generate_whatsapp_link_token():
    """Generate a 6-digit token for WhatsApp linking"""
    try:
        # Generate 6-digit token
        token = str(secrets.randbelow(900000) + 100000)
        
        # Set expiration (10 minutes from now)
        from datetime import datetime, timedelta
        expires_at = datetime.utcnow() + timedelta(minutes=10)
        
        # Store token in database
        link_token = WhatsAppLinkToken(
            token=token,
            user_id=current_user.id,
            expires_at=expires_at,
            used=False
        )
        db.session.add(link_token)
        db.session.commit()
        
        # Build WhatsApp deep link
        twilio_whatsapp_number = os.environ.get('TWILIO_WHATSAPP_NUMBER', 'whatsapp:+1234567890')
        # Extract phone number from whatsapp:+1234567890 format
        phone_number = twilio_whatsapp_number.replace('whatsapp:', '').replace('+', '')
        wa_link = f"https://wa.me/{phone_number}?text=LINK%20{token}"
        
        # Generate QR code
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(wa_link)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        img_buffer = io.BytesIO()
        img.save(img_buffer, format='PNG')
        img_buffer.seek(0)
        qr_base64 = base64.b64encode(img_buffer.getvalue()).decode()
        
        return jsonify({
            'token': token,
            'expires_at': expires_at.isoformat(),
            'wa_link': wa_link,
            'qr_base64': f"data:image/png;base64,{qr_base64}"
        }), 200
        
    except Exception as e:
        return jsonify({'error': f'Failed to generate token: {str(e)}'}), 500

@app.route('/api/whatsapp/unlink', methods=['POST'])
@login_required
def unlink_whatsapp():
    """Unlink WhatsApp from user account"""
    try:
        current_user.whatsapp_number = None
        current_user.whatsapp_linked_at = None
        db.session.commit()
        return jsonify({'message': 'WhatsApp unlinked successfully'}), 200
    except Exception as e:
        return jsonify({'error': f'Failed to unlink WhatsApp: {str(e)}'}), 500

# Twilio webhook endpoint
@app.route('/twilio/webhook', methods=['POST'])
def twilio_webhook():
    """Handle incoming WhatsApp messages from Twilio"""
    try:
        from twilio.request_validator import RequestValidator
        
        # Debug: Print all environment variables that start with TWILIO
        print("=== Environment Variables Debug ===")
        for key, value in os.environ.items():
            if key.startswith('TWILIO'):
                print(f"{key}: {'*' * len(value) if value else 'NOT SET'}")
        
        # Get Twilio auth token
        twilio_auth_token = os.environ.get('TWILIO_AUTH_TOKEN', '')
        print(f"TWILIO_AUTH_TOKEN found: {bool(twilio_auth_token)}")
        print(f"TWILIO_AUTH_TOKEN length: {len(twilio_auth_token) if twilio_auth_token else 0}")
        
        if not twilio_auth_token:
            print("TWILIO_AUTH_TOKEN not found in environment variables")
            return 'Twilio auth token not configured', 403
        
        # Validate Twilio signature
        validator = RequestValidator(twilio_auth_token)
        url = request.url
        params = request.form.to_dict()
        signature = request.headers.get('X-Twilio-Signature', '')
        
        print(f"Validating Twilio signature for URL: {url}")
        print(f"Signature present: {bool(signature)}")
        print(f"Params keys: {list(params.keys())}")
        
        # For development/testing, you might want to skip validation
        # In production, always validate
        skip_validation = os.environ.get('SKIP_TWILIO_VALIDATION', 'false').lower() == 'true'
        
        if not skip_validation and not validator.validate(url, params, signature):
            print("Twilio signature validation failed")
            return 'Invalid signature', 403
        
        # Extract message data
        from_number = request.form.get('From', '')
        message_body = request.form.get('Body', '').strip()
        message_sid = request.form.get('MessageSid', '')
        
        # Normalize phone number
        normalized_number = from_number if from_number.startswith('whatsapp:') else f'whatsapp:{from_number}'
        
        # Check if this is a linking token
        if message_body.isdigit() and len(message_body) == 6:
            # Try to link with token
            token = message_body
            
            # Atomic token consumption
            from datetime import datetime
            link_token = WhatsAppLinkToken.query.filter_by(
                token=token, 
                used=False
            ).filter(WhatsAppLinkToken.expires_at > datetime.utcnow()).first()
            
            if link_token:
                # Mark token as used and link user
                link_token.used = True
                user = db.session.get(User, link_token.user_id)
                if user:
                    user.whatsapp_number = normalized_number
                    user.whatsapp_linked_at = datetime.utcnow()
                    db.session.commit()
                    
                    reply = f"✅ Linked successfully! You can now ask questions about your videos. Try: 'list my videos' or 'what happened yesterday on camera 1'"
                else:
                    reply = "❌ User not found. Please try again."
            else:
                reply = "❌ Token invalid or expired. Generate a new token from your dashboard."
        else:
            # Look up user by WhatsApp number
            user = User.query.filter_by(whatsapp_number=normalized_number).first()
            
            if not user:
                reply = "❌ No linked account found. Please generate a token from your dashboard and send it here."
            else:
                # Process natural language query
                reply = process_whatsapp_query(user, message_body)
        
        # Send reply via TwiML
        from flask import Response
        twiml = f'<Response><Message>{reply}</Message></Response>'
        return Response(twiml, mimetype='text/xml')
        
    except Exception as e:
        # Log error and send friendly message
        print(f"Twilio webhook error: {e}")
        import traceback
        traceback.print_exc()  # Print full stack trace
        twiml = '<Response><Message>Sorry, something went wrong. Please try again later.</Message></Response>'
        return Response(twiml, mimetype='text/xml')

def process_whatsapp_query(user, query):
    """Process natural language query and return summary"""
    try:
        query_lower = query.lower()
        
        # Simple command parsing
        if 'list' in query_lower and ('video' in query_lower or 'camera' in query_lower):
            # List user's videos
            videos = Video.query.filter_by(user_id=user.id).limit(5).all()
            if videos:
                video_list = "\n".join([f"• {v.video_name} ({v.video_type})" for v in videos])
                return f"📹 Your recent videos:\n{video_list}\n\nAsk about any video by name!"
            else:
                return "📹 No videos found. Upload some videos first!"
        
        elif 'what happened' in query_lower or 'analyze' in query_lower:
            # Try to find video by name in query
            videos = Video.query.filter_by(user_id=user.id).all()
            matching_video = None
            
            for video in videos:
                if video.video_name.lower() in query_lower:
                    matching_video = video
                    break
            
            if matching_video:
                # Use existing Qwen analysis
                try:
                    # Build video URL for analysis
                    if matching_video.video_type == 'upload' and matching_video.file_path_or_url:
                        filename = os.path.basename(matching_video.file_path_or_url)
                        video_url = f"{os.environ.get('APP_BASE_URL', 'http://localhost:5000')}/api/video_file/{filename}"
                    else:
                        video_url = matching_video.file_path_or_url
                    
                    # Call Qwen
                    dashscope_key = os.environ.get('DASHSCOPE_API_KEY')
                    if dashscope_key:
                        client = OpenAI(
                            api_key=dashscope_key,
                            base_url="https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
                        )
                        
                        messages = [
                            {
                                "role": "system",
                                "content": [{"type": "text", "text": "You are Qwen-VL. Provide a concise summary of what happens in this video, focusing on key events, people, and activities. Keep response under 200 words."}]
                            },
                            {
                                "role": "user", 
                                "content": [
                                    {"type": "text", "text": query},
                                    {"type": "video_url", "video_url": {"url": video_url}}
                                ]
                            }
                        ]
                        
                        completion = client.chat.completions.create(
                            model="qwen-vl-max",
                            messages=messages,
                            temperature=0.2,
                        )
                        
                        answer = completion.choices[0].message.content if completion and completion.choices else "No analysis available."
                        
                        # Save to chat history
                        chat = ChatHistory(
                            video_id=matching_video.id,
                            user_id=user.id,
                            question=query,
                            answer=answer,
                            model_used="qwen-vl-max"
                        )
                        db.session.add(chat)
                        db.session.commit()
                        
                        return f"🎥 Analysis of '{matching_video.video_name}':\n\n{answer}"
                    else:
                        return "❌ Analysis service not configured."
                        
                except Exception as e:
                    return f"❌ Analysis failed: {str(e)}"
            else:
                return "❌ Video not found. Try 'list my videos' to see available videos."
        
        else:
            return """🤖 Hi! I can help you with your CCTV videos. Try these commands:
            
📹 "list my videos" - Show your recent videos
🎥 "what happened in [video name]" - Analyze a specific video
🔍 "analyze [video name]" - Get detailed analysis

Example: "what happened in my security footage" """
            
    except Exception as e:
        return f"❌ Error processing query: {str(e)}"

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    
    # Get port from environment variable (for Railway) or use default
    port = int(os.environ.get('PORT', 5000))
    
    # Run the app
    app.run(host='0.0.0.0', port=port, debug=False) 