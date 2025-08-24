import os

# Configuration for different environments
class Config:
    # Detect environment
    @staticmethod
    def is_huggingface():
        return os.environ.get('SPACE_ID') is not None
    
    @staticmethod
    def is_local():
        return not Config.is_huggingface()
    
    # API URL configuration
    @staticmethod
    def get_api_url():
        if Config.is_huggingface():
            # For Hugging Face deployment, you need to set this to your deployed backend URL
            # Example: "https://your-backend.railway.app/api"
            return os.environ.get('BACKEND_API_URL', None)
        else:
            # Local development
            return "http://localhost:5000/api"
    
    # Database configuration
    @staticmethod
    def get_database_url():
        if Config.is_huggingface():
            # For production, use environment variable
            return os.environ.get('DATABASE_URL', 'sqlite:///cctv_chat.db')
        else:
            # Local development
            return 'sqlite:///instance/cctv_chat.db'
    
    # Secret key configuration
    @staticmethod
    def get_secret_key():
        return os.environ.get('SECRET_KEY', 'your-secret-key-change-this-in-production')
    
    # AI API configuration
    @staticmethod
    def get_openai_api_key():
        return os.environ.get('OPENAI_API_KEY', '')
    
    @staticmethod
    def get_dashscope_api_key():
        return os.environ.get('DASHSCOPE_API_KEY', '')

# Environment variables needed for Hugging Face deployment:
# BACKEND_API_URL=https://your-backend-url.com/api
# DATABASE_URL=sqlite:///cctv_chat.db (or your production database URL)
# SECRET_KEY=your-secure-secret-key
# OPENAI_API_KEY=your-openai-api-key
# DASHSCOPE_API_KEY=your-dashscope-api-key
