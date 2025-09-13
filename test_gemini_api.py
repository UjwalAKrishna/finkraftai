#!/usr/bin/env python3
"""Simple test script for Gemini API integration"""

import requests
import json

def test_gemini_api():
    """Test the Gemini-powered chat API"""
    
    base_url = "http://localhost:8000"
    
    print("🧪 Testing Gemini LLM Chat API")
    print("Start the server with: python3 run_app.py")
    print("Then run this test in another terminal\n")
    
    # Sample conversation
    messages = [
        "Filter invoices for last month, vendor='IndiSky', status=failed",
        "Create ticket: Failed invoices need GSTIN information",
        "Show my tickets",
        "Export the filtered data as CSV"
    ]
    
    for i, message in enumerate(messages, 1):
        print(f"{i}. Testing: '{message}'")
        
        response = requests.post(f"{base_url}/chat", json={
            "user_id": "john_doe",
            "message": message
        })
        
        if response.status_code == 200:
            data = response.json()
            print(f"   ✅ Success: {data['success']}")
            print(f"   🤖 Response: {data['agent_response']}")
            print(f"   🔧 Tool: {data.get('tool_used', 'none')}")
            
            if data.get('llm_response') and isinstance(data['llm_response'], dict):
                explanation = data['llm_response'].get('explanation', '')
                if explanation:
                    print(f"   💭 LLM: {explanation}")
        else:
            print(f"   ❌ Error: {response.status_code}")
        
        print()

if __name__ == "__main__":
    test_gemini_api()