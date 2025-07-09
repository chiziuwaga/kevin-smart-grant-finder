"""
Simple test to verify Perplexity API key is working
"""

import httpx
import json
import os

async def test_api_key():
    api_key = "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"
    
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }
    
    payload = {
        "model": "sonar-reasoning-pro",
        "messages": [
            {"role": "user", "content": "What is 2+2?"}
        ]
    }
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                "https://api.perplexity.ai/chat/completions",
                headers=headers,
                json=payload,
                timeout=30.0
            )
            
            print(f"Status: {response.status_code}")
            print(f"Response: {response.text[:200]}...")
            
            if response.status_code == 200:
                data = response.json()
                print("✅ API key is working!")
                return True
            else:
                print("❌ API key failed")
                return False
                
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    import asyncio
    asyncio.run(test_api_key())
