# 🚀 Deployment Guide for CCTV Chat

## Overview
This application consists of two parts:
1. **Frontend**: Streamlit app (deployed on Hugging Face Spaces)
2. **Backend**: Flask API server (needs to be deployed separately)

## 🎯 Quick Fix for "Please log in to access this page"

The error you're seeing is because the frontend is trying to connect to a backend server that doesn't exist on Hugging Face. Here are your options:

### Option 1: Deploy Backend Separately (Recommended)

#### Step 1: Deploy Backend to Railway (Free)
1. Go to [Railway.app](https://railway.app)
2. Sign up with GitHub
3. Create new project → Deploy from GitHub repo
4. Select your repository
5. Set environment variables:
   ```
   SECRET_KEY=your-secure-secret-key-here
   DATABASE_URL=sqlite:///cctv_chat.db
   OPENAI_API_KEY=your-openai-api-key
   DASHSCOPE_API_KEY=your-dashscope-api-key
   ```

#### Step 2: Update Hugging Face Environment Variables
1. Go to your Hugging Face Space settings
2. Add environment variable:
   ```
   BACKEND_API_URL=https://your-railway-app.railway.app/api
   ```

### Option 2: Use Local Development Only
For now, you can run the app locally:
```bash
# Terminal 1: Start backend
python backend.py

# Terminal 2: Start frontend
streamlit run appnavigation.py
```

## 📋 Complete Deployment Steps

### Backend Deployment Options

#### A. Railway (Recommended - Free)
```bash
# 1. Install Railway CLI
npm install -g @railway/cli

# 2. Login to Railway
railway login

# 3. Deploy
railway up
```

#### B. Render (Free Tier)
1. Go to [Render.com](https://render.com)
2. Create new Web Service
3. Connect your GitHub repo
4. Set build command: `pip install -r requirements.txt`
5. Set start command: `python backend.py`

#### C. Heroku (Paid)
```bash
# 1. Install Heroku CLI
# 2. Create Procfile with: web: python backend.py
# 3. Deploy
heroku create your-app-name
git push heroku main
```

### Frontend Deployment (Hugging Face)

1. **Update Environment Variables** in your Hugging Face Space:
   ```
   BACKEND_API_URL=https://your-deployed-backend.com/api
   ```

2. **Push your updated code** to GitHub

3. **Hugging Face will automatically redeploy**

## 🔧 Configuration Files

### config.py
This file handles environment detection and configuration:
- Automatically detects if running on Hugging Face
- Uses environment variables for production settings
- Falls back to local development settings

### Environment Variables Needed

#### For Backend (Railway/Render/Heroku):
```
SECRET_KEY=your-secure-secret-key
DATABASE_URL=sqlite:///cctv_chat.db
OPENAI_API_KEY=your-openai-api-key
DASHSCOPE_API_KEY=your-dashscope-api-key
```

#### For Frontend (Hugging Face):
```
BACKEND_API_URL=https://your-backend-url.com/api
```

## 🐛 Troubleshooting

### Common Issues:

1. **"Please log in to access this page"**
   - Backend not deployed or URL incorrect
   - Check `BACKEND_API_URL` environment variable

2. **"Connection refused"**
   - Backend server not running
   - Check if backend deployment is active

3. **"Database error"**
   - Database not properly configured
   - Check `DATABASE_URL` environment variable

### Testing Your Deployment:

1. **Test Backend**: Visit `https://your-backend-url.com/api/profile`
   - Should return 401 (not authenticated) not 404 (not found)

2. **Test Frontend**: Visit your Hugging Face Space
   - Should show login page, not error message

## 📞 Support

If you need help:
1. Check the logs in your deployment platform
2. Verify all environment variables are set
3. Test the backend URL directly in browser

## 🎉 Success!

Once deployed correctly:
- Users can register/login
- Upload and manage videos
- Chat with AI about video content
- All data stored securely in database
