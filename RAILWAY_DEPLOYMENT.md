# 🚀 Railway Deployment Guide for CCTV Chat

## Prerequisites
- ✅ GitHub repository: https://github.com/binahinnovation/cctvchat
- ✅ Code pushed to GitHub
- ✅ Railway account (free)

## Step-by-Step Deployment

### Step 1: Create Railway Account
1. Go to [Railway.app](https://railway.app)
2. Click "Start a New Project"
3. Sign up with GitHub (use same account as your repository)

### Step 2: Deploy from GitHub
1. Click "Deploy from GitHub repo"
2. Select repository: `binahinnovation/cctvchat`
3. Railway will auto-detect Python app
4. Click "Deploy"

### Step 3: Configure Environment Variables
Once deployed, go to your project settings → Variables tab and add:

```
SECRET_KEY=your-super-secret-key-change-this-12345
DATABASE_URL=sqlite:///cctv_chat.db
OPENAI_API_KEY=your-openai-api-key-here
DASHSCOPE_API_KEY=your-dashscope-api-key-here
```

### Step 4: Get Your Backend URL
After deployment, Railway will show your app URL like:
`https://your-app-name.railway.app`

### Step 5: Test Your Backend
Visit: `https://your-app-name.railway.app/api/profile`
- Should return 401 (not authenticated) - this means it's working!

### Step 6: Update Hugging Face
1. Go to your Hugging Face Space settings
2. Add environment variable:
   ```
   BACKEND_API_URL=https://your-app-name.railway.app/api
   ```
3. Wait for automatic redeploy

## 🎯 Expected Results

### After Railway Deployment:
- ✅ Backend accessible at `https://your-app-name.railway.app`
- ✅ API endpoints working
- ✅ Database created automatically

### After Hugging Face Update:
- ✅ Login page appears instead of error
- ✅ Users can register/login
- ✅ Full app functionality works

## 🔧 Troubleshooting

### Common Issues:

1. **"Build failed"**
   - Check Railway logs
   - Ensure all dependencies in requirements.txt

2. **"App not starting"**
   - Check environment variables are set
   - Verify SECRET_KEY is set

3. **"Database errors"**
   - DATABASE_URL should be: `sqlite:///cctv_chat.db`
   - Database will be created automatically

4. **"Connection refused"**
   - Wait for Railway to finish deployment
   - Check if app is running in Railway dashboard

## 📊 Railway Dashboard

Once deployed, you can:
- View logs in real-time
- Monitor resource usage
- Update environment variables
- Restart the app if needed

## 💰 Cost Estimation

- **Free tier**: $5 credit/month
- **Your app**: ~$1-2/month
- **Remaining**: $3+ for other projects

## 🎉 Success!

Once everything is set up:
- Frontend: Your Hugging Face Space
- Backend: Your Railway app
- Users can register, upload videos, and chat with AI!

## 📞 Support

If you encounter issues:
1. Check Railway logs
2. Verify environment variables
3. Test backend URL directly in browser
4. Check Hugging Face Space logs
