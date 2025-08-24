import requests
import os

def test_backend_connection():
    """Test if backend is accessible"""
    
    # Get backend URL from environment or use local
    backend_url = os.environ.get('BACKEND_API_URL', 'http://localhost:5000/api')
    
    print(f"Testing backend connection to: {backend_url}")
    
    try:
        # Test basic connectivity
        response = requests.get(f"{backend_url}/profile", timeout=10)
        print(f"✅ Backend is accessible! Status: {response.status_code}")
        
        if response.status_code == 401:
            print("✅ Backend is working correctly (401 = not authenticated, which is expected)")
        elif response.status_code == 200:
            print("✅ Backend is working and user is authenticated")
        else:
            print(f"⚠️ Unexpected status code: {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("❌ Connection failed - backend is not accessible")
        print("Make sure your backend is deployed and the URL is correct")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    test_backend_connection()
