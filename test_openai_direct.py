#!/usr/bin/env python3
"""
Direct OpenAI API test to diagnose issues
"""
import os
import sys
import json
from dotenv import load_dotenv
import openai

def test_openai_api():
    """Test OpenAI API with our current key"""
    print("🔍 Testing OpenAI API Key...")
    
    # Load environment
    load_dotenv()
    api_key = os.getenv('OPENAI_API_KEY')
    
    if not api_key:
        print("❌ ERROR: OPENAI_API_KEY not found in environment")
        return False
        
    print(f"✅ API Key loaded: {api_key[:15]}...{api_key[-4:]}")
    print(f"✅ Key format: {'sk-proj-' if api_key.startswith('sk-proj-') else 'sk-'}")
    
    try:
        # Initialize client
        client = openai.OpenAI(api_key=api_key)
        print("✅ OpenAI client initialized")
        
        # Test embeddings (what we use for Pinecone)
        print("\n🧪 Testing text-embedding-3-large...")
        response = client.embeddings.create(
            model="text-embedding-3-large",
            input="Test grant search system embedding"
        )
        
        embedding = response.data[0].embedding
        print(f"✅ Embedding successful!")
        print(f"   - Dimension: {len(embedding)}")
        print(f"   - First 5 values: {embedding[:5]}")
        print(f"   - Usage tokens: {response.usage.total_tokens}")
        
        # Test chat completions (what we use for extraction)
        print("\n🧪 Testing gpt-4-turbo...")
        chat_response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": "Say 'OpenAI API is working' if you can respond."}
            ],
            temperature=0.9,
            max_tokens=50
        )
        
        print(f"✅ Chat completion successful!")
        print(f"   - Response: {chat_response.choices[0].message.content}")
        print(f"   - Usage tokens: {chat_response.usage.total_tokens}")
        
        return True
        
    except openai.AuthenticationError as e:
        print(f"❌ AUTHENTICATION ERROR: {e}")
        print("   Check if your API key is valid and has proper permissions")
        return False
    except openai.RateLimitError as e:
        print(f"❌ RATE LIMIT ERROR: {e}")
        print("   Your API key may have hit rate limits")
        return False
    except openai.APIError as e:
        print(f"❌ API ERROR: {e}")
        return False
    except Exception as e:
        print(f"❌ UNEXPECTED ERROR: {e}")
        return False

if __name__ == "__main__":
    success = test_openai_api()
    sys.exit(0 if success else 1)
