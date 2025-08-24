---
title: CCTV Chat - AI Surveillance Analysis
emoji: 📹
colorFrom: blue
colorTo: indigo
sdk: streamlit
sdk_version: 1.45.1
app_file: home.py
pinned: false
---

# CCTV Chat - AI-Powered Surveillance Analysis

This application uses AI to analyze CCTV footage and provide intelligent summaries and answers to questions about the video content.

## Features

- Upload and analyze CCTV footage
- Ask questions about the video content
- Get AI-powered analysis and insights
- Real-time progress tracking
- User-friendly interface

## Technical Details

- Built with Streamlit
- Uses Qwen-VL model via Alibaba Cloud API
- Supports MP4, MOV, and AVI video formats
- Optimized for surveillance footage analysis

## Environment Variables

The following environment variables need to be set in Hugging Face:

- `DASHSCOPE_API_KEY`: Your Alibaba Cloud API key

## Local Development

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```
3. Run the application:
```bash
streamlit run appnavigation.py
```

## Deployment

This application is deployed on Hugging Face Spaces. You can access it at: [Your Hugging Face Space URL]

## License

[Your License Here] 